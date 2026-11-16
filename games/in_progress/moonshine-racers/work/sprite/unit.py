#!/usr/bin/env python3
"""Run an assembled test blob inside a snapshot and log cycle-counter timestamps at its markers.

    python3 work/sprite/unit.py TEST.s [--snap race_start] [--machine ste] [--mem 1024] [--clock 8] [--dump ADDR:LEN ...] [--live name ...]
The blob is assembled with vasm (-Fbin, org $C0000), loaded at $C0000 at the first $7a88 hit; $7b74 (jsr $d1e4) is redirected to it
(the blob must restore the 6 bytes `4e b9 00 00 d1 e4` and end with `jmp $d1e4.l`).  Every label `m_*` is a marker: a breakpoint
prints `e CycleCounter` each time it executes.  The blob writes 'DONE' to $C0FF0 when finished.  Output: marker timeline + dumps."""
import argparse, re, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine  # noqa
import msrabtest as ab  # noqa


def assemble(src: Path, defs=()):
    out = src.with_suffix(".bin"); lst = src.with_suffix(".lst")
    cmd = ["vasmm68k_mot", "-Fbin", "-m68000", "-no-opt", "-o", str(out), "-L", str(lst), "-nosym"] + [f"-D{d}" for d in defs] + [str(src)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    syms = {}
    for ln in lst.read_text().splitlines():
        m = re.match(r"^\s*(\S+)\s+[AEC]:([0-9A-Fa-f]+)", ln)
    # vasm listing: "Symbols by name:" then "name  A:00000000"
    txt = lst.read_text()
    i = txt.find("Symbols by name")
    for ln in txt[i:].splitlines()[1:]:
        m = re.match(r"^(\S+)\s+\S*:([0-9A-Fa-f]+)\s*$", ln.strip()) or re.match(r"^(\S+)\s+\S*[ A-Z]:?\s*([0-9A-Fa-f]{6,8})\s*$", ln.strip())
        if m: syms[m.group(1)] = int(m.group(2), 16)
    return out, syms


def run(src, snap="race_start", machine="ste", mem=1024, clock=None, dumps=(), live=None, timeout=240, defs=(), bins=(), extra=(), trig=0x7a88):
    out, syms = assemble(Path(src), defs)
    marks = {a: n for n, a in syms.items() if n.startswith("m_")}
    h = Moonshine(snapshot=ab.snap_path(snap), machine=machine, memsize_kb=mem) if (machine != "ste" or mem != 1024) else Moonshine(snapshot=ab.snap_path(snap))
    try:
        time.sleep(1.5 if machine == 'ste' else 5)
        if clock: h.set_cpuclock(clock)
        for pc, n in marks.items():
            (h.R / f"mk_{pc:x}.txt").write_text("e CycleCounter\n")
        cmds = [f"loadbin {out.resolve()} $c0000"] + [f"loadbin {Path(b.split(':')[1]).resolve()} ${b.split(':')[0]}" for b in bins] + ["w $7b74 $4e $b9 $00 $0c $00 $00"]
        if live:
            spec_cmds = ab.apply_live  # not used: live applied separately
        for pc, scr in extra:
            (h.R / f"xb_{pc:x}.txt").write_text(scr)
        (h.R / "apply.txt").write_text("\n".join(cmds + [f"b pc = ${pc:x} :trace :file {h.R}/mk_{pc:x}.txt" for pc in marks] + [f"b pc = ${pc:x} :trace :file {h.R}/xb_{pc:x}.txt" for pc, _ in extra]) + "\n")
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        if live:
            lv = ab.live_build(live)
            ab.apply_live(h, lv, 0x7A88)
            n0 = len(h._logtext())
        if machine != "ste":
            v = h.vbl()
            h.cmd(f"hatari-debug b VBL > {v + 3} && pc = $7b86 :trace :once :file {h.R}/apply.txt")
        else:
            h.cmd(f"hatari-debug b pc = ${trig:x} :trace :once :file {h.R}/apply.txt")
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(1.5)
            o = h.debug("m $c0ff0 4", 0.5)
            if "44 4f 4e 45" in o: break
        else:
            print("TIMEOUT")
        log = h._logtext()[n0:]
        res = {}
        if dumps and "r" in dumps:
            res["r"] = h.debug("r", 1.0)
        for d in [x for x in dumps if x != "r"]:
            a, l = d.split(":")
            res[d] = h.debug(f"m ${a} {int(l,16) if False else l}", 1.0)
        res["__log__"] = log
    finally:
        h.close()
    # timeline
    tl = []
    parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", log)
    for i in range(1, len(parts) - 1, 2):
        pc = int(parts[i].split("$")[1], 16)
        m = re.search(r"#(\d+)(?:/-?\d+)? \(dec\)", parts[i + 1])
        if m: tl.append((marks.get(pc, hex(pc)), int(m.group(1))))
    return tl, res, syms


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("--snap", default="race_start")
    ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--clock", type=int)
    ap.add_argument("--dump", nargs="*", default=[]); ap.add_argument("--live", nargs="*"); ap.add_argument("-D", nargs="*", default=[]); ap.add_argument("--bin", nargs="*", default=[])
    a = ap.parse_args()
    tl, res, syms = run(a.src, a.snap, a.machine, a.mem, a.clock, a.dump, a.live, defs=a.D, bins=a.bin)
    prev = None
    for n, c in tl:
        d = "" if prev is None else (c - prev) & 0xffffffff
        print(f"{n:20s} {c:12d}  +{d}")
        prev = c
    for k, v in res.items(): print(v)

if __name__ == "__main__":
    main()
