#!/usr/bin/env python3
"""Timing gates for the WW1 fixed-tick patches (tick_head tick_pass tick_wx tick_men tick_click*).  Port of master's tools/pmtick.py.

    python3 tools/wwtick.py snap NAME [--wait S] [--mhz 8]     cold boot of disks/ea.st (original) to the map view, savemem -> $SNAPDIR/NAME.sav
    python3 tools/wwtick.py rate NAME --mhz 8 --hz 50 [--unpatched] [--vbls 600]   world ticks per EMULATED second from a snapshot
    python3 tools/wwtick.py ab NAME --mhz 8 [--vbls 700] [--control]               per-tick state equality: unpatched vs live-patched
    python3 tools/wwtick.py cold --disk build/tick/floppy.st ...                    rate on a cold boot of a built floppy

Snapshot runs use ONE work dir name ($W, wiped between runs) so the paths inside the memstate stay valid; only one Hatari runs at a time.
The live patch = what the built floppy's hook would write: the blob span $72800..$72AFF of the build's expect.bin (loadbin) + every site's new bytes
(`w`), applied at a call of the flip routine (`$e0e`, code is only patched at a frame boundary).  The unpatched run executes `e VBL` at the same stop.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402

SNAPDIR = Path("/tmp/pmww1s2/snaps")
W = Path("/tmp/pmww1s2/tickrun")
LOOPTOP = 0x13D58          # first instruction of a loop pass (view limits; master $12fd8)
FLIP = 0xE0E               # the flip routine (master $187a)
ITER = 0x2ED90             # long: world clock (original: +1 per pass; patched: +1 per tick pass)
PASSC = 0x50FD8            # long: second counter bumped with it
D = 0x72A80                # tick_head's data block
DUMP_LEN = 0x72000         # RAM $0-$71fff = the whole game (payload excluded)

# ranges that legitimately differ between two runs of the SAME game (interrupt-driven / scratch); filled from the unpatched-vs-unpatched control
MASKS: list[tuple[int, int, str]] = [
    (0x1D500, 0x2D1C0, "screens"),
    (0x2D6C0, 0x2D780, "stack scratch above the screens"),
    (0x1BC80, 0x1BCA0, "timer-C sound player pointer"),
    (0x1D2A0, 0x1D2C0, "IKBD packet state / shadow pointer"),
    (0x2ED94, 0x2EDA8, "click stamp (patched: the pass counter), screen pointers (flip parity differs with R passes)"),
    (0x2EDAC, 0x2EDAE, "flip-wait flag"),
    (0x2EDBE, 0x2EDC0, "right-button latch written by the IKBD handler in the VBL"),
    (0x2D7B2, 0x2D7C0, "sound sequencer state (timer-C interrupt, real-time driven: snd_core $1c4de)"),
    (0x82C6, 0x82C8, "composer's self-modified screen address (flip parity)"),
    (0xE7C2, 0xE7C6, "draw pointer scratch = back buffer + $20 (flip parity)"),
    (0x13CCC, 0x13CCE, "render-this-pass flag (0 on S / skipped passes)"),
    (0x71B7C, 0x71B84, "VBL counter (differs between two runs of the same snapshot: timing jitter)"),
]


def snap_path(name):
    return SNAPDIR / f"{name}.sav"


def new_run(disk, snapshot=None, **kw):
    shutil.rmtree(W, ignore_errors=True)
    return pmww.PMW(disk=Path(disk), workdir=str(W), snapshot=str(snapshot) if snapshot else None, machine="ste", tos=pmww.TOS["1.62"], memsize_kb=1024, **kw)


def cmd_snap(a):
    SNAPDIR.mkdir(parents=True, exist_ok=True)
    h = new_run(pmww.DISK)
    try:
        h.boot_to_map()
        time.sleep(a.wait)
        out = snap_path(a.name)
        h.savemem(str(out))
        print(f"SNAP {out} {out.stat().st_size} B; world clock ${h.peekl(ITER):x}", flush=True)
    finally:
        h.close()


# ---- live patch ---------------------------------------------------------------------------------------------------------
def live_cmds(build: Path):
    man = json.loads((build / "manifest.json").read_text())
    img = (build / "expect.bin").read_bytes()
    lo, hi = 0x72800, 0x72B00
    f = W.parent / "live_blob.bin"
    f.write_bytes(img[lo - pmww_IMG:hi - pmww_IMG])
    c = [f"loadbin {f} ${lo:x}"]
    for s in man["sites"]:
        if s["name"].startswith("tick_"):
            c.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
    return c


pmww_IMG = 0x72000


def wait_gone(h, start, timeout=900):
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never fired")
        time.sleep(0.3)
    time.sleep(0.4)


def at_flip(h, cmds):
    f = h.R / "atflip.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :once :file {f}")
    wait_gone(h, start, 120)


def sample_at(h, target, exprs, timeout=600):
    """Debugger `e` values at ONE stop: the first VBL > target."""
    f = h.R / f"smp{target}.txt"
    f.write_text("".join(f"e {e}\n" for e in exprs))
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {target} :trace :once :file {f}")
    wait_gone(h, start, timeout)
    out = {}
    for m in re.finditer(r"> e (.+)\n(?:  .*\n)*= (.*)", h._logtext()[start:]):
        out[m.group(1)] = int(re.search(r"\$([0-9a-fA-F]+) \(hex\)", m.group(2)).group(1), 16)
    return out


def rd(h, a, n):
    out = h.debug(f"m ${a:x} {n}", 0.5)
    bs = bytearray()
    for ln in out.splitlines():
        m = re.match(r"[0-9A-Fa-f]{8}:\s(.*)", ln)
        if m:
            bs += bytes(int(x, 16) for x in m.group(1).split("  ")[0].split())
    return bytes(bs[:n])


def rate_numbers(h, hz, vbls, patched, tag):
    if hz is None:                                     # the machine's real refresh: shifter sync mode bit 1 ($ff820a), 1 = 50 Hz, 0 = 60 Hz
        hz = 50 if rd(h, 0xFF820A, 1)[0] & 2 else 60
    ex = ["VBL", "CycleCounter", f"(${ITER:x}).l"] + ([f"(${D + o:x}).l" for o in (8, 12, 16)] if patched else [])
    s0 = sample_at(h, h.vbl() + 40, ex)
    s1 = sample_at(h, s0["VBL"] + vbls, ex)
    dv = s1["VBL"] - s0["VBL"]
    secs = dv / hz
    t = s1[ex[2]] - s0[ex[2]]
    line = (f"RATE {tag} {hz} Hz: {dv} VBL = {secs:.2f} s emulated, {((s1['CycleCounter'] - s0['CycleCounter']) & 0xFFFFFFFF) / dv:.0f} cycles/VBL, "
            f"world clock +{t} = {t / secs:.3f}/s")
    if patched:
        r = [s1[e] - s0[e] for e in ex[3:]]
        line += f"; tick passes {r[0]}, R passes {r[1]}, S passes {r[2]}"
    return line, t / secs


def cmd_rate(a):
    h = new_run(pmww.DISK, snap_path(a.name))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        cmds = (live_cmds(ROOT / a.build) if not a.unpatched else ["e VBL"]) + (["w $ff820a $00"] if a.hz == 60 else [])
        at_flip(h, cmds)
        time.sleep(1.0)
        sync = rd(h, 0xFF820A, 1)[0]
        line, _ = rate_numbers(h, a.hz, a.vbls, not a.unpatched, f"{a.name} {a.mhz} MHz {a.hz} Hz sync ${sync:02x} {'orig' if a.unpatched else 'patched'}")
        print(line, flush=True)
    finally:
        h.close()


# ---- per-tick state equality --------------------------------------------------------------------------------------------
def log_passes(h, live, mhz, vbls, poke=()):
    """Restore state, apply `live` (None = nothing) at a flip, then dump RAM $0-$71fff at every loop top for `vbls` VBL: [(world clock, pass counter, bytes)]."""
    if mhz != 8:
        h.set_cpuclock(mhz)
    at_flip(h, list(poke) + (live if live else ["e VBL"]))
    cur = h.R / "cur.bin"
    f = h.R / "dumpcmd.txt"
    f.write_text(f"savebin {cur} $0 ${DUMP_LEN:x}\n")
    got, stop = [], threading.Event()

    def poll():
        last = None
        while not stop.is_set():
            try:
                st = cur.stat()
            except FileNotFoundError:
                time.sleep(0.003)
                continue
            if st.st_size == DUMP_LEN and st.st_mtime_ns != last:
                time.sleep(0.03)
                st2 = cur.stat()
                if st2.st_mtime_ns == st.st_mtime_ns and st2.st_size == DUMP_LEN:
                    last = st.st_mtime_ns
                    got.append(cur.read_bytes())
            time.sleep(0.004)
    th = threading.Thread(target=poll, daemon=True)
    th.start()
    h.debug("b all", 0.3)
    s2 = len(h._logtext())
    v0 = h.vbl()
    h.cmd(f"hatari-debug b pc = ${LOOPTOP:x} :trace :file {f}")
    time.sleep(0.2)
    h.cmd(f"hatari-debug b VBL > {v0 + vbls} :trace :once")
    wait_gone(h, s2)
    h.debug("b all", 0.3)
    time.sleep(0.5)
    stop.set()
    th.join()
    L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
    return [(L(b, ITER), L(b, PASSC), b) for b in got]


def site_masks(build: Path):
    man = json.loads((build / "manifest.json").read_text())
    return [(s["addr"], s["addr"] + len(bytes.fromhex(s["new"]))) for s in man["sites"] if s["name"].startswith("tick_")]


def diff_words(a, b, smask):
    import numpy as np
    x = np.frombuffer(a, dtype=">u2")
    y = np.frombuffer(b, dtype=">u2")
    idx = np.nonzero(x != y)[0] * 2
    return [int(i) for i in idx if not any(lo <= i < hi for lo, hi, _ in MASKS) and not any(lo <= i < hi for lo, hi in smask)]


def group(addrs, gap=16):
    out = []
    for a in addrs:
        if out and a - out[-1][1] <= gap:
            out[-1][1] = a + 2
        else:
            out.append([a, a + 2])
    return out


def cmd_ab(a):
    build = ROOT / a.build
    live = live_cmds(build)
    smask = site_masks(build)
    res = {}
    for name, lv in (("U", None), ("P", None if a.control else live)):
        h = new_run(pmww.DISK, snap_path(a.name))
        try:
            time.sleep(1.5)
            res[name] = log_passes(h, lv, a.mhz, a.vbls if lv else int(a.vbls * 1.6), a.poke)
        finally:
            h.close()
    U, P = res["U"], res["P"]
    ub = {}
    for it, k, b in U:
        ub.setdefault(it, b)
    tag = f"{a.name} {a.mhz} MHz" + (" CONTROL (unpatched vs unpatched)" if a.control else "")
    print(f"AB {tag}: unpatched {len(U)} loop tops (world clock {U[0][0]}..{U[-1][0]}), second run {len(P)} loop tops (clock {P[0][0]}..{P[-1][0]})")
    for nm, L in (("patched" if not a.control else "second", P), ("unpatched", U)):
        its = [k for k, _, _ in L]
        print(f"AB   {nm}: distinct world clocks {len(set(its))}, passes with a repeated clock (R passes) {len(its) - len(set(its))}")
    bad, n, ticks, vals = {}, 0, set(), {}
    for it, k, b in P:
        u = ub.get(it)
        if u is None:
            continue
        n += 1
        ticks.add(it)
        d = diff_words(u, b, smask)
        for g in group(d):
            bad.setdefault((g[0], g[1]), []).append(it)
            if len(vals.setdefault((g[0], g[1]), [])) < 6:
                vals[(g[0], g[1])].append((it, u[g[0]:g[1]].hex(), b[g[0]:g[1]].hex()))
    print(f"AB compared {n} loop tops over {len(ticks)} distinct world ticks")
    neg = sum(1 for it, k, b in P if ub.get(it + 1) is not None and diff_words(ub[it + 1], b, smask))
    nn = sum(1 for it, k, b in P if ub.get(it + 1) is not None)
    print(f"AB negative control: second tick k vs unpatched tick k+1 differs in {neg} of {nn} loop tops")
    if not bad:
        print(f"AB RESULT {tag}: IDENTICAL (everything in $0-${DUMP_LEN - 1:x} except the masks)")
    else:
        print(f"AB RESULT {tag}: DIFFERENT")
        for (lo, hi), its in sorted(bad.items())[:60]:
            print(f"AB DIFF ${lo:x}-${hi - 1:x} in {len(its)} loop tops, first clocks {its[:4]}")
            for v in vals[(lo, hi)][:4]:
                print("AB     clock %d unpatched %s patched %s" % v)
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("snap")
    p.add_argument("name")
    p.add_argument("--wait", type=float, default=5)
    p = sub.add_parser("rate")
    p.add_argument("name")
    p.add_argument("--mhz", type=int, default=8)
    p.add_argument("--hz", type=int, default=50)
    p.add_argument("--vbls", type=int, default=600)
    p.add_argument("--unpatched", action="store_true")
    p.add_argument("--build", default="build/tick")
    p = sub.add_parser("ab")
    p.add_argument("name")
    p.add_argument("--mhz", type=int, default=8)
    p.add_argument("--vbls", type=int, default=700)
    p.add_argument("--control", action="store_true", help="both runs unpatched: finds the noise ranges to mask")
    p.add_argument("--build", default="build/tick")
    p.add_argument("--poke", nargs="*", default=[], help="debugger commands run at the flip stop in both runs")
    a = ap.parse_args()
    return {"snap": cmd_snap, "rate": cmd_rate, "ab": cmd_ab}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
