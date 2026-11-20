#!/usr/bin/env python3
"""Per-stage cycles of one Lotus frame (1 player, driving).  usage: lstages.py SNAP NAME [--frames N] [--clock 8] [--seq HEX,HEX,...] [--settle VBL]
Chain of one-shot breakpoints at the return addresses of the calls in the frame body ($76378..$765fa), each logs `e VBL`/`e FrameCycles`
and arms the next (as tools/msrstages.py).  Output work/lotus/prof/stages_NAME.txt"""
import argparse, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lotus import Lotus
HERE = Path(__file__).resolve().parent
CYC = 160256
SEQ = [0x76378, 0x76576, 0x7657a, 0x7657e, 0x7658a, 0x7658e, 0x7659a, 0x7659e, 0x765a2, 0x765a6, 0x765da, 0x765fa]

def run(snap, name, frames=20, clock=8, seq=SEQ, settle=60, up=True, poke=()):
    h = Lotus(snapshot=snap, extra=['--joy1', 'keys'])
    try:
        time.sleep(3)
        if clock != 8: h.set_cpuclock(clock)
        if up: h.debug('w $70569 $01', 0.3)
        for a, v in poke: h.debug(f'w ${a:x} ${v:x}', 0.3)
        v0 = h.vbl()
        while h.vbl() < v0 + settle: time.sleep(0.3)
        for i, r in enumerate(seq):
            nxt = seq[(i + 1) % len(seq)]
            (h.R / f"st_{r:x}.txt").write_text(f"e VBL\ne FrameCycles\nb pc = ${nxt:x} :trace :once :file {h.R}/st_{nxt:x}.txt\n")
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${seq[0]:x} :trace :once :file {h.R}/st_{seq[0]:x}.txt")
        time.sleep(frames * 2.3 / 50.0 * 1.6 * (8 / clock) + 6)
        h.debug("b all", 0.5)
        log = h._logtext()[n0:]
    finally:
        h.close()
    (HERE / f"prof/stages_{name}.rawlog").write_text(log)
    raw = []; cur = None
    for ln in log.splitlines():
        m = re.match(r"\tpc = \$([0-9a-f]+) :once :trace", ln)
        if m: cur = int(m.group(1), 16); vbl = None; continue
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur is not None:
            v = int(m.group(1))
            if vbl is None: vbl = v
            else: raw.append((cur, vbl, v)); cur = None
    best = None
    for c0 in sorted({fc for _, _, fc in raw}) + [CYC]:
        t = [(v + (1 if fc < c0 else 0)) * CYC + fc for _, v, fc in raw]
        bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
        if best is None or bad < best[0]: best = (bad, c0)
    c0 = best[1]
    ev = [(pc, (v + (1 if fc < c0 else 0)) * CYC + fc) for pc, v, fc in raw]
    print("wrap c0 =", c0, "monotonic violations =", best[0], "events", len(ev))
    rows = {}; tot = []
    for i in range(1, len(ev)):
        pc, t = ev[i]; rows.setdefault(pc, []).append(t - ev[i-1][1])
    out = ["# stage = cycles from the previous stage point to this pc (return of the call at pc-4/-6)"]
    for pc in seq:
        v = rows.get(pc, [])
        if v: out.append(f"{pc:05x} n={len(v):3d} mean={sum(v)/len(v):9.0f} min={min(v):8d} max={max(v):8d}")
    # frame period: successive visits of seq[0]
    t0 = [t for pc, t in ev if pc == seq[0]]
    if len(t0) > 1:
        d = [b - a for a, b in zip(t0, t0[1:])]
        out.append(f"period n={len(d)} mean={sum(d)/len(d):.0f} ({sum(d)/len(d)/CYC:.2f} VBL) min={min(d)} max={max(d)}")
    (HERE / f"prof/stages_{name}.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("name")
    ap.add_argument("--frames", type=int, default=20); ap.add_argument("--clock", type=int, default=8)
    ap.add_argument("--settle", type=int, default=60)
    a = ap.parse_args()
    run(a.snap, a.name, a.frames, a.clock, settle=a.settle)
