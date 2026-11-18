#!/usr/bin/env python3
"""Bucket a Moonshine Racers CPU profile (Hatari `profile save`) by function.

    python3 tools/msrprof.py work/dumps/ram_race_up.bin work/prof/race_up.txt [--top 25]

Profile file lines: `$addr  insn  pct% (count, cycles, imiss, dhit)`.  A function = from a jsr/bsr/jmp-abs target to the next
target (same bucketing as tools/m68dis.py; range $800-$20000).  Frames = executions of the page-flip routine $d1ca
(FLIP_PC).  Exclusive cycles only.  CYC_PER_VBL = 160256 (8 MHz, 50 Hz)."""
from __future__ import annotations
import argparse, bisect, re, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import m68dis

FLIP_PC = 0xD1CA
CYC_PER_VBL = 160256
LO, HI = 0x800, 0x20000
LINE = re.compile(r"^\$([0-9a-f]+)\s.*% \((\d+), (\d+), \d+, \d+\)\s*$", re.I)


def load(path):
    d = {}
    for ln in open(path):
        m = LINE.match(ln)
        if m:
            d[int(m.group(1), 16)] = (int(m.group(3)), int(m.group(2)))   # cycles, count
    return d


def targets(ram):
    m68dis.CODE_LO, m68dis.CODE_HI = LO, HI
    t = set(m68dis.call_targets(ram))
    for a in range(LO, HI - 6, 2):
        if struct.unpack_from(">H", ram, a)[0] == 0x4EF9:
            x = struct.unpack_from(">I", ram, a + 2)[0]
            if LO <= x < HI and x % 2 == 0:
                t.add(x)
    return sorted(t)


def buckets(ram, prof):
    tg = targets(ram)
    frames = prof.get(FLIP_PC, (0, 0))[1] or 1
    tot = sum(c for c, _ in prof.values())
    out = {}
    for a, (c, n) in prof.items():
        i = bisect.bisect_right(tg, a) - 1
        f = tg[i] if i >= 0 else a
        b = out.setdefault(f, [0, 0])
        b[0] += c
        b[1] = max(b[1], prof.get(f, (0, 0))[1])
    return frames, tot, sorted(out.items(), key=lambda kv: -kv[1][0])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dump"); ap.add_argument("prof"); ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args(argv)
    ram = open(a.dump, "rb").read()
    frames, tot, bs = buckets(ram, load(a.prof))
    cpf = tot / frames
    print(f"frames={frames} total_cycles={tot}  cycles/frame={cpf:.0f} = {cpf / CYC_PER_VBL:.2f} VBL")
    print("func     excl_cyc   share  cyc/frame  %ofVBL  calls/frame  cyc/call")
    for f, (c, calls) in bs[:a.top]:
        print(f"${f:05x} {c:10d} {100 * c / tot:6.2f}% {c / frames:10.0f} {100 * c / frames / CYC_PER_VBL:6.1f}% {calls / frames:8.2f} {(c / calls if calls else 0):10.0f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
