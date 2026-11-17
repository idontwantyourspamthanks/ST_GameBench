"""python3 prof_run.py SNAP SET OUTNAME [vbls]  : apply live SET at $7a88, settle, dump RAM, Hatari profile -> work/tightC/res/prof_<OUT>.txt + ram_<OUT>.bin"""
import sys, os, time
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, G+'/tools')
os.environ['MSRPATCH_TOOL']=G+'/work/tightC/msrpatch_priv.py'
os.environ.setdefault('MSR_LIVETAG','_tc')
import msrabtest as ab
from msr import Moonshine, prof
snap, var, name = sys.argv[1], sys.argv[2], sys.argv[3]
vbls = int(sys.argv[4]) if len(sys.argv)>4 else 300
SETS = {'stock': None,
 'new': ['mr_edge','rd_geom','rd_draw','rd_init','hd_stage','hd_init','hd_clouds','hd_nomap','hd_nomap2']}
sets = (SETS['new'] if var.startswith('new') else []) + var.split('+')[1:] if var != 'stock' else None
live = ab.live_build(sets) if sets else None
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    v0 = h.vbl()
    while h.vbl() < v0 + 80: time.sleep(0.3)
    h.dump(f'{G}/work/tightC/res/ram_{name}.bin', 0, 0x100000)
    o = prof(h, vbls, f'{G}/work/tightC/res/prof_{name}.txt')
    print(o[o.find('Normal RAM'):][:300])
finally:
    h.close()
