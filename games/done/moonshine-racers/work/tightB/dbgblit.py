import sys, re, time, os
from pathlib import Path
GAME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GAME / 'tools'))
os.environ.setdefault('MSRPATCH_TOOL', str(GAME / 'work/tightB/msrpatch_priv.py')); os.environ.setdefault('MSR_LIVETAG', '_tb')
import msrabtest as ab
from msr import Moonshine
snap, extra, secs = sys.argv[1], sys.argv[2].split(','), int(sys.argv[3])
BASE = ['mr_edge', 'rd_geom', 'rd_draw', 'rd_init', 'hd_stage', 'hd_init', 'hd_clouds', 'hd_nomap', 'hd_nomap2']
live = ab.live_build(BASE + extra)
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5); h.debug('b all', 0.3)
    ab.apply_live(h, live, 0x7A88); time.sleep(0.4); h.debug('b all', 0.3)
    (h.R / 'dbg.txt').write_text("r\nm $b5800 4\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $b4604 :trace :file {h.R}/dbg.txt")
    time.sleep(secs)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
open(sys.argv[4], 'w').write(log)
print(len(log), log.count('Reading debugger commands'), 'bus errors:', log.count('Bus Error'), 'addr errors:', log.count('Address Error'))
