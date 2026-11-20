"""python3 dumpat.py SNAP OUT.bin [PC=7a88] [MHZ=8] : restore stock snapshot, run to the first hit of PC, dump 1 MB RAM + regs.
Private to MSRExtrap. Uses its own workdir (mkdtemp) and kills only its own Hatari."""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/timing')
from tlib import *
snap, out = sys.argv[1], sys.argv[2]
pc = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x7a88
h = open_snap(snap, 8)
try:
    f = h.R / "dump.txt"
    f.write_text(f"savebin {Path(out).resolve()} 0 $100000\nr\ne VBL\n")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${pc:x} :trace :once :file {f}")
    t0 = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[n0:]:
        if time.time() - t0 > 120: raise SystemExit("timeout")
        time.sleep(0.3)
    time.sleep(2.5)
    log = h._logtext()[n0:]
    open(str(out) + ".regs.txt", "w").write(log)
    print(log[-1500:])
finally:
    h.close()
