#!/usr/bin/env python3
"""Print the baseline tables (markdown) from work/bench/*.json made by work/bench.py."""
import json
import sys
from pathlib import Path

B = Path(__file__).resolve().parent / "bench"
SNAPS = ["1mb_ski_stand", "1mb_ski_walk", "1mb_ski_turn", "1mb_ski_busy"]


def load(snap, mhz):
    p = B / f"{snap}_{mhz}mhz.json"
    return json.loads(p.read_text()) if p.exists() else None


def fps_table():
    print("| snapshot | 8 MHz flips/1000 VBL | fps | VBL/frame | 16 MHz flips/1000 VBL | fps | VBL/frame |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for s in SNAPS:
        r8, r16 = load(s, 8), load(s, 16)
        c = []
        for r in (r8, r16):
            f = r and r.get("fps")
            c += [f["flips"], f"{f['fps']:.1f}", f"{f['vbls_per_frame']:.1f}"] if f else ["-"] * 3
        print(f"| `{s}` | " + " | ".join(str(x) for x in c) + " |")


def trace_table(maxframes=40):
    """Compare the 8 and 16 MHz flip traces frame by frame. set_cpuclock() costs about a second, so the 16 MHz
    run starts a few frames further along; the traces are aligned on the first 16 MHz row, found in the
    8 MHz trace by (x, z, speed, heading). If the simulation is per-frame, the aligned rows agree exactly."""
    print("| snapshot | aligned frames | rows identical (x,z,speed,heading) | path | VBL, 8 MHz | VBL, 16 MHz | units/s, 8 MHz | units/s, 16 MHz | ratio | heading/s 8 MHz | heading/s 16 MHz |")
    print("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in ("1mb_ski_walk", "1mb_ski_turn"):
        r8, r16 = load(s, 8), load(s, 16)
        t8, t16 = (r8 or {}).get("trace"), (r16 or {}).get("trace")
        if not t8 or not t16:
            continue
        key = lambda r: tuple(r[1:])
        i8 = next((i for i, r in enumerate(t8) if key(r) == key(t16[0])), None)
        if i8 is None:
            print(f"| `{s}` | no alignment | | | | | | | | | |")
            continue
        n = min(len(t8) - i8, len(t16), maxframes + 1) - 1
        a, b = t8[i8:i8 + n + 1], t16[:n + 1]
        same = all(key(x) == key(y) for x, y in zip(a, b))
        path = sum(abs(q[1] - p_[1]) + abs(q[2] - p_[2]) for p_, q in zip(a, a[1:]))
        v8, v16 = a[-1][0] - a[0][0], b[-1][0] - b[0][0]
        dh = lambda t: (t[-1][4] - t[0][4] + 512) % 1024 - 512
        print(f"| `{s}` | {n} | {'yes' if same else 'NO'} | {path} | {v8} | {v16} | {path * 50 / v8:.0f} | "
              f"{path * 50 / v16:.0f} | {v8 / v16:.2f}x | {dh(a) * 50 / v8:.1f} | {dh(b) * 50 / v16:.1f} |")


def profile_tables(top=20):
    for s in SNAPS:
        r = load(s, 8)
        p = r and r.get("profile")
        if not p:
            continue
        tot = p["total_cycles"]
        print(f"\n### `{s}` at 8 MHz ({p['vbls']} VBL, {tot} cycles, {p['instr_addrs']} distinct instruction addresses)\n")
        print("| rank | bucket (call target) | share | cycles/VBL |")
        print("|---:|---|---:|---:|")
        for i, (k, c) in enumerate(p["buckets"][:top], 1):
            print(f"| {i} | `{k}` | {100 * c / tot:.1f}% | {c / p['vbls']:.0f} |")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "fps"):
        fps_table()
    if which in ("all", "trace"):
        print()
        trace_table()
    if which in ("all", "profile"):
        profile_tables()
