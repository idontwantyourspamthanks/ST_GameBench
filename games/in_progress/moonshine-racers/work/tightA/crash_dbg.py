import sys, re, time, os
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
from msr import Moonshine
names = sys.argv[1].split(',')
live = ab.live_build(names)
h = Moonshine(snapshot=ab.snap_path('race_drive'))
try:
    time.sleep(1.5); ab.apply_live(h, live, 0x7A88); time.sleep(0.4)
    (h.R / "hold.txt").write_text("w $6105 $01\n"); h.cmd(f"hatari-debug b pc = $7a88 :trace :file {h.R}/hold.txt")
    h.debug("ex address,bus", 0.5)
    n0 = len(h._logtext())
    t0 = time.time()
    while time.time() - t0 < 400:
        lg = h._logtext()[n0:]
        if 'Address Error' in lg or 'Bus Error' in lg or 'exception' in lg.lower(): break
        time.sleep(1)
    time.sleep(1)
    print(h._logtext()[n0:][-1500:].encode('latin1','replace').decode('latin1'))
    o = h.debug("history 40", 1.5); print(o[-3000:])
    o = h.debug("r", 1.0); print(o[-1500:])
finally:
    h.close()
