#!/usr/bin/env python3
"""Per-stage cycle cost of the main loop ($7960..$7bac) from a snapshot.

    python3 tools/msrstages.py work/snapshots/ste1m_race_start.sav race_start [--frames 20] [--clock 8]
A chain of `b pc = <return address of each jsr in the loop and in $ef7a> :once :file` breakpoints; every stage file logs
`e VBL` and `e FrameCycles`, and the last stage re-arms the first, so each frame is timed.  Absolute cycle = VBL*160256 +
FrameCycles (8 MHz ST: 160256 cycles per 50 Hz frame; the numbers scale with --clock).  Output: work/notes/stages_<name>.txt"""
import argparse, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME

BENCH = GAME.parent.parent.parent
DUMP = GAME / "work/dumps/ram_race_up.bin"
CYC = 160256


def seq_from(dump):
    def dis(a, b):
        return subprocess.run([sys.executable, str(BENCH / "tools/m68dis.py"), str(dump), a, "--end", b], capture_output=True, text=True).stdout
    rets = []
    for ln in (dis("7960", "7b7c") + dis("ef7a", "efc6")).splitlines():
        m = re.match(r"([0-9a-f]{6}):\s+([0-9a-f]+)\s+(jsr|bsr)", ln)
        if m:
            rets.append((int(m.group(1), 16), int(m.group(1), 16) + len(m.group(2)) // 2))
    main = [r for a, r in rets if 0x7a88 <= a < 0x7b6c]
    ef = [r for a, r in rets if 0xef7a <= a < 0xefc6]
    i = main.index(0x7b52) if 0x7b52 in main else None
    # loop top $796a (jsr $838a), its return $7970, render start $7a88, the jsr calls, flip-wait $7b74 (jsr $d1e4) and its return $7b7a
    return [0x796a, 0x7970, 0x7a88] + [r for r in main if r <= 0x7b4c] + ef + [r for r in main if r > 0x7b4c] + [0x7b74, 0x7b7a]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("name")
    ap.add_argument("--frames", type=int, default=20); ap.add_argument("--clock", type=int, default=8)
    a = ap.parse_args()
    seq = seq_from(DUMP)
    h = Moonshine(snapshot=a.snap)
    try:
        time.sleep(3)
        if a.clock != 8: h.set_cpuclock(a.clock)
        for i, r in enumerate(seq):
            lines = ["e VBL", "e FrameCycles"]
            nxt = seq[(i + 1) % len(seq)]
            lines.append(f"b pc = ${nxt:x} :trace :once :file {h.R}/st_{nxt:x}.txt")
            (h.R / f"st_{r:x}.txt").write_text("\n".join(lines) + "\n")
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${seq[0]:x} :trace :once :file {h.R}/st_{seq[0]:x}.txt")
        time.sleep(a.frames * 6 / 50.0 * 1.2 + 3)
        h.debug("b all", 0.5)
        log = h._logtext()[n0:]
    finally:
        h.close()
    open(GAME / f"work/notes/stages_{a.name}.rawlog", "w").write(log)
    # parse: every stage prints `pc = $X :once :trace`, then `e VBL`, `e FrameCycles`
    raw = []
    cur = None
    for ln in log.splitlines():
        m = re.match(r"\tpc = \$([0-9a-f]+) :once :trace", ln)
        if m: cur = int(m.group(1), 16); vbl = None; continue
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur is not None:
            v = int(m.group(1))
            if vbl is None: vbl = v
            else: raw.append((cur, vbl, v)); cur = None
    # Hatari's VBL counter and FrameCycles wrap at different cycles of the frame: find the offset c0 (events with
    # FrameCycles < c0 belong to frame VBL+1) that makes the event times monotonic.
    best = None
    for c0 in sorted({fc for _, _, fc in raw}) + [CYC]:
        t = [(v + (1 if fc < c0 else 0)) * CYC + fc for _, v, fc in raw]
        bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
        if best is None or bad < best[0]: best = (bad, c0)
    c0 = best[1]
    ev = [(pc, (v + (1 if fc < c0 else 0)) * CYC + fc) for pc, v, fc in raw]
    print("frame-wrap offset c0 =", c0, "monotonic violations =", best[0])
    out = Path(GAME / f"work/notes/stages_{a.name}.txt")
    rows = {}
    for i in range(1, len(ev)):
        pc, t = ev[i]; pt = ev[i - 1][1]
        rows.setdefault(pc, []).append(t - pt)
    with open(out, "w") as f:
        f.write(f"# {a.snap} clock {a.clock}; events {len(ev)}; stage = cycles from previous stage point to the return of the call at this pc\n")
        for pc in seq:
            v = rows.get(pc, [])
            if v:
                f.write(f"{pc:05x} n={len(v):3d} mean={sum(v) / len(v):9.0f} min={min(v):8d} max={max(v):8d}\n")
    print(open(out).read())

if __name__ == "__main__":
    main()
