#!/usr/bin/env python3
"""Compare the per-effect features of fx passes (out/<cell>_fx.json from cell.py --fx) against a reference cell.

    python3 work/audiocheck/fxcmp.py REF CELL [CELL ...]

Per effect id: rms, spectral centroid (20 Hz-3.2 kHz, the DMA stream's band) and energy share above 1.5 kHz; the ratio/difference against the
reference.  A cell with intact data and the same mixer agrees within a few % (the request lands on another VBL phase, so waveforms do not correlate);
a damaged sample region shows as a centroid and high-band jump on exactly the effects that use it (Midwinter 2: banktail.md section 4).
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def load(n):
    return {r["e"]: r for r in json.load(open(OUT / f"{n}_fx.json"))}


def main():
    ref, cells = sys.argv[1], sys.argv[2:]
    R = load(ref)
    print(f"reference {ref}")
    for c in cells:
        C = load(c)
        print(f"\n{c} vs {ref}:  e | rms ratio | centroid Hz (ref -> cell) | hi>1.5k % (ref -> cell) | len ms (ref -> cell) | DMA rate reg / ctl")
        worst = 0.0
        for e in sorted(R):
            if e not in C:
                continue
            a, b = R[e], C[e]
            rr = b["rms"] / max(a["rms"], 1e-9)
            dc = b["centroid"] - a["centroid"]
            dh = 100 * (b["hi"] - a["hi"])
            worst = max(worst, abs(rr - 1), abs(dc) / max(a["centroid"], 1), abs(dh) / 10)
            flag = " <<<" if abs(rr - 1) > 0.25 or abs(dc) > 0.25 * max(a["centroid"], 1) + 60 or abs(dh) > 8 else ""
            print(f"  {e:2d} | {rr:5.2f} | {a['centroid']:6.0f} -> {b['centroid']:6.0f} | {100 * a['hi']:5.1f} -> {100 * b['hi']:5.1f} | {a.get('len_ms')} -> {b.get('len_ms')} | {b['dma_rate']}/{b['dma_ctl']}{flag}")
        print(f"  worst normalised deviation {worst:.2f}")


if __name__ == "__main__":
    main()
