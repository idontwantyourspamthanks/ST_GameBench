import sys; sys.path.insert(0,'.')
from analyze import *
import statistics
COPY = {"pm": 0x13096, "ww1": 0x13e0a}
LAND = {"pm": 0x130aa, "ww1": 0x13e1e}
CLK = {8: 8021247, 16: 16042494}
for mhz in (8, 16):
  for g, snaps in (("ww1", ["map_idle","get_men"]), ("pm", ["map_idle","get_men","battle_320"])):
    for s in snaps:
        d, rows = load(g, s, mhz)
        r, dl = passes(d, COPY[g])
        dl = [x for x in dl if x < 20_000_000]
        mean = sum(dl)/len(dl)
        vb = [(b[2]-a[2]) for a, b in zip(r, r[1:])]
        print(f"{g:3s} {s:10s} {mhz:2d}MHz passes {len(dl):3d} cycles/rendered-pass mean {mean:10.0f} median {statistics.median(dl):10.0f} min {min(dl)} max {max(dl)}  -> {CLK[mhz]/mean:5.2f} fps (emulated cycles/clock) | flips {d['fps']['flips']}/400 VBL = {d['fps']['fps']:.3f} fps | VBL/pass {sum(vb)/len(vb):.1f}")
