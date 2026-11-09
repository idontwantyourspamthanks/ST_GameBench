#!/usr/bin/env python3
"""Bucket a Hunter CPU profile (work/prof/<name>.txt: lines `addr cycles count`, hex addr) by function.

    python3 games/hunter/tools/hprof.py work/dumps/ram_foot_stand.bin work/prof/foot_stand.txt [--top 15]

A function = from a jsr/bsr/jmp-abs target to the next target (same bucketing as tools/m68dis.py, range widened to
$800-$A0000 because Hunter's engine is loaded up to $79714). Frames = executions of the flip instruction $5fee.
Exclusive cycles only (callees are separate buckets)."""
from __future__ import annotations
import argparse, bisect, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import m68dis

FLIP_PC = 0x5FEE
CYC_PER_VBL = 160256            # 8 MHz STE, 50 Hz


def targets(ram: bytes) -> list[int]:
    m68dis.CODE_LO, m68dis.CODE_HI = 0x800, 0xA0000
    t = set(m68dis.call_targets(ram))
    for a in range(0x800, 0xA0000 - 6, 2):              # jmp abs.l too
        if struct.unpack_from(">H", ram, a)[0] == 0x4EF9:
            x = struct.unpack_from(">I", ram, a + 2)[0]
            if 0x800 <= x < 0xA0000 and x % 2 == 0:
                t.add(x)
    return sorted(t)


def load(path: str) -> dict[int, tuple[int, int]]:
    d = {}
    for ln in open(path):
        p = ln.split()
        if len(p) >= 3:
            d[int(p[0], 16)] = (int(p[1]), int(p[2]))
    return d


def buckets(ram: bytes, prof: dict[int, tuple[int, int]]):
    tg = targets(ram)
    frames = prof.get(FLIP_PC, (0, 0))[1] or 1
    tot = sum(c for c, _ in prof.values())
    out: dict[int, list[int]] = {}
    for a, (c, n) in prof.items():
        i = bisect.bisect_right(tg, a) - 1
        f = tg[i] if i >= 0 else a
        b = out.setdefault(f, [0, 0, 0])
        b[0] += c
        b[1] = max(b[1], prof.get(f, (0, 0))[1])        # entry executions = calls
    return frames, tot, sorted(out.items(), key=lambda kv: -kv[1][0])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dump"); ap.add_argument("prof"); ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args(argv)
    ram = open(a.dump, "rb").read()
    frames, tot, bs = buckets(ram, load(a.prof))
    print(f"frames={frames} total_cycles={tot} ({tot / CYC_PER_VBL:.0f} VBL)  cycles/frame={tot // frames}")
    print("func     excl_cyc   share  calls/frame  cyc/call")
    for f, (c, calls, _) in bs[:a.top]:
        cpf = calls / frames
        print(f"${f:05x} {c:10d} {100 * c / tot:6.2f}% {cpf:10.2f} {(c / calls if calls else 0):10.0f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
