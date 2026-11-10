import sys, subprocess
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
snap, mhz = sys.argv[1], int(sys.argv[2])
names=open('/tmp/cand_names.txt').read().split()
names=[n for n in names if not n.startswith('pp_')]
live=build_live(names,'skipcnt')
h=Hatari(snapshot=str(SNAP/snap),memsize_kb=2048)
try:
    if mhz!=8: h.set_cpuclock(mhz)
    v=h.vbl(); at_flip(h,apply_cmds(live),v+100); time.sleep(2)
    d0=memb(h,0xb6000,64); f=h.fps(600); d1=memb(h,0xb6000,64)
    g=lambda d,o: uw(d[o:o+4])
    c={k:g(d1,o)-g(d0,o) for k,o in (('NSKIP',0x14),('NREND',0x18),('NINV',0x1c),('NUNS',0x24),('NSC',0x28),('NOBJ',0x2c),('NWAV',0x30))}
    print('CNT',snap,mhz,'type',h.peekw(0x6220),'fps',f['fps'],c)
finally: h.close()
