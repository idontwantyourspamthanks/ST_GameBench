#!/usr/bin/env python3
"""Profile Powermonger with a patch set applied live on a snapshot (hotpaths2.md).

    python3 tools/pmprof2.py run SNAP MHZ [--only p ...] [--vbls 300] [--out work/prof2] [--tag T]
    python3 tools/pmprof2.py rep work/prof2/get_men_8_T            # report from saved files

`run` writes <out>/<snap>_<mhz>_<tag>.txt (Hatari profile), .stages.json (CycleCounter at every main-loop jsr site, kind of pass)
and .bin (RAM at the end).  The default patch set (pmpatch.py live without --only) is applied at the next loop top, followed by
`r pc=$d0010` (snd_live: the DMA sound setup), like tools/pmsnd.py.  --only none applies nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from pm import PM, SNAP, LOOP_SITES, LOOP_NAMES  # noqa: E402

LOOPTOP = 0x12FD8
TMP = Path("/tmp/pm2")
D = 0xB8A00
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
SITES = (0x13020, 0x13040, 0x13046, 0x1304C, 0x13052, 0x13074, 0x13090, 0x13096, 0x130A4, 0x130AA, 0x130B0, 0x130B6, 0x130BC,
         0x130C2, 0x130C8, 0x130CE, 0x130F6, 0x130FC, 0x1386C, 0x13872)


def build_live(names: list[str] | None, tag: str) -> str:
    out = TMP / tag / "live"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(HERE / "pmpatch.py"), "live", "--out", str(out)]
    if names is not None:
        cmd += ["--only", *names]
    subprocess.run(cmd, check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    spec = json.loads(Path(str(out) + ".json").read_text())
    sites = []
    for s in spec["sites"]:
        raw = bytes.fromhex(s["new"])
        for o in range(0, len(raw), 40):
            sites.append({**s, "addr": s["addr"] + o, "new": raw[o:o + 40].hex()})
    spec["sites"] = sites
    Path(str(out) + ".json").write_text(json.dumps(spec))
    return str(out)


def apply_cmds(live: str) -> list[str]:
    spec = json.loads(Path(live + ".json").read_text())
    c = [f"loadbin {live}.img ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])) for s in spec["sites"]]
    return c


def at_loop(h: PM, cmds: list[str], timeout: float = 120) -> None:
    f = h.R / "atloop.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${LOOPTOP:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("loop top")
        time.sleep(0.3)
    time.sleep(0.5)


def run(snap: str, mhz: int, names, vbls: int, out: Path, tag: str, stages: bool = True):
    out.mkdir(parents=True, exist_ok=True)
    base = out / f"{snap}_{mhz}_{tag}"
    h = PM(snapshot=str(SNAP / (snap + ".sav")), memsize_kb=1024)
    try:
        time.sleep(1.0)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = []
        if names != []:
            live = build_live(names, tag)
            cmds = apply_cmds(live)
            cmds.append("r pc=$d0010")
        else:
            cmds.append("e VBL")
        at_loop(h, cmds)
        time.sleep(0.5)
        h.debug("b all", 0.3)
        # warm up: 60 VBL
        v = h.vbl()
        s0 = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {v + 60} :trace :once")
        h._wait_removed(s0)
        h.debug("b all", 0.3)
        ctx = h.R / "cyc.txt"
        ctx.write_text(f"e pc\ne CycleCounter\ne VBL\ne (${D + 6:x}).w\n")
        endf = h.R / "prof_end.txt"
        endf.write_text(f"profile save {base}.txt\nsavebin {base}.bin $0 $100000\nb all\n")
        s0 = len(h._logtext())
        v = h.vbl()
        if stages:
            for pc in SITES:
                h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {ctx}")
                time.sleep(0.1)
        h.cmd(f"hatari-debug b VBL > {v + vbls + 25} :trace :once :file {endf}")
        time.sleep(0.3)
        h.cmd("hatari-debug profile on")
        h._wait_removed(s0, timeout=1800)
        time.sleep(2.0)
        text = h._logtext()[s0:]
    finally:
        h.close()
    recs = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(x) for x in NUM.findall(blk)]
        if len(m) >= 4 and m[0] in SITES:
            recs.append((m[0], m[1], m[2], m[3]))
    Path(f"{base}.stages.json").write_text(json.dumps(recs))
    txt = Path(f"{base}.txt").read_text()
    m = re.search(r"^\$00001282\s.*?\((\d+),", txt, re.M)
    print(base, "VBL handler runs", m.group(1) if m else None, "stage records", len(recs))
    return base


def stage_report(base: str):
    recs = json.loads(Path(f"{base}.stages.json").read_text())
    acc = defaultdict(int)
    kinds = defaultdict(lambda: [0, 0])
    # segment [site_i, site_i+1) attributed to site_i; the pass kind comes from the first site of each pass ($13020 or $13040)
    tot = 0
    for (p0, c0, v0, k0), (p1, c1, v1, k1) in zip(recs, recs[1:]):
        d = (c1 - c0) & 0xFFFFFFFF
        if d > 5_000_000:
            continue
        acc[p0] += d
        tot += d
    passes = sum(1 for r in recs if r[0] == 0x13020)
    rend = sum(1 for r in recs if r[0] == 0x13096)
    flips = sum(1 for r in recs if r[0] == 0x1386C)
    return acc, tot, passes, rend, flips


NAMES = {0x13020: "tick head", 0x13040: "$127e6 sound queue", 0x13046: "$6522", 0x1304C: "$d322 group scan", 0x13052: "$3e06 captain upkeep",
         0x13074: "tick_pass", 0x13090: "$1870 VBL wait", 0x13096: "$12ce0 window copy", 0x130A4: "$178ae (tooltip hook)",
         0x130AA: "$f898 landscape+objects", 0x130B0: "$1abaa season/weather", 0x130B6: "$17878 HUD", 0x130BC: "$165b2 HUD/army",
         0x130C2: "$14b62 men sim", 0x130C8: "$6a3a UI", 0x130CE: "$7a56 UI", 0x130F6: "$d23a", 0x130FC: "$7202", 0x1386C: "$187a flip",
         0x13872: "$1a276"}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="c", required=True)
    r = sub.add_parser("run")
    r.add_argument("snap"); r.add_argument("mhz", type=int)
    r.add_argument("--only", nargs="*", default=None)
    r.add_argument("--add", nargs="*", default=[], help="patches added to the default set")
    r.add_argument("--vbls", type=int, default=300)
    r.add_argument("--out", default=str(GAME / "work/prof2"))
    r.add_argument("--tag", default="def")
    r.add_argument("--no-stages", action="store_true")
    q = sub.add_parser("rep")
    q.add_argument("base")
    a = ap.parse_args()
    if a.c == "run":
        names = None if a.only is None else ([] if a.only == ["none"] else a.only)
        if a.add:
            import pmpatch
            names = [p.name for p in pmpatch.selected(pmpatch.load_all(), None)] + a.add if names is None else names + a.add
        base = run(a.snap, a.mhz, names, a.vbls, Path(a.out), a.tag, not a.no_stages)
    else:
        base = a.base
    if Path(f"{base}.stages.json").exists():
        acc, tot, passes, rend, flips = stage_report(base)
        print(f"loop passes {passes}, rendered {rend}, flips {flips}, total {tot} cycles; per pass:")
        for k, v in sorted(acc.items(), key=lambda kv: -kv[1]):
            print(f"  {NAMES.get(k, hex(k)):28s} {v / max(1, passes):10.0f}  {100 * v / tot:5.1f} %")


if __name__ == "__main__":
    main()
