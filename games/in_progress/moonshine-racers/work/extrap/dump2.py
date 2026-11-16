"""python3 dump2.py SNAP OUTPREFIX PC1 PC2 : dumps 1 MB at the first hit of PC1 then the next hit of PC2 (stock snapshot, 8 MHz)."""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/timing')
from tlib import *
snap, pre = sys.argv[1], sys.argv[2]
pcs = [int(x, 16) for x in sys.argv[3:]]
h = open_snap(snap, 8)
try:
    h.debug("b all", 0.3)
    for i, pc in enumerate(pcs):
        nxt = pcs[i+1] if i+1 < len(pcs) else None
        lines = [f"savebin {Path(pre).resolve()}_{pc:x}.bin 0 $100000", "r", "e VBL"]
        if nxt is not None: lines.append(f"b pc = ${nxt:x} :trace :once :file {h.R}/d_{nxt:x}.txt")
        (h.R / f"d_{pc:x}.txt").write_text("\n".join(lines) + "\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${pcs[0]:x} :trace :once :file {h.R}/d_{pcs[0]:x}.txt")
    t0 = time.time()
    while h._logtext()[n0:].count("Wrote 0x100000") < len(pcs):
        if time.time() - t0 > 120: raise SystemExit("timeout")
        time.sleep(0.3)
    time.sleep(1.5)
    print(h._logtext()[n0:][-600:])
finally:
    h.close()
