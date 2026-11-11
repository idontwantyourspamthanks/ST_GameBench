import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
snap, mhz, vbls = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
live = build_live(None, 'v12_default')
h = Hatari(snapshot=str(SNAP/snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl()
    print('type', hex(h.peekw(0x6220)), 'view', h.peekw(0x700a), 'pos', memb(h,0x66e6,8).hex())
    at_flip(h, apply_cmds(live), v + 100)
    time.sleep(2)
    d0 = memb(h, 0xb6000, 64)
    f = h.fps(vbls)
    d1 = memb(h, 0xb6000, 64)
    print(snap, mhz, 'MHz', f)
    for nm, o in (('NSKIP',0x14),('NREND',0x18),('NINV',0x1c),('NUNS',0x24),('NSC',0x28),('NOBJ',0x2c),('NWAV',0x30)):
        print(' ', nm, uw(d0[o:o+4]), '->', uw(d1[o:o+4]))
    print(' type', hex(h.peekw(0x6220)), 'pos', memb(h,0x66e6,8).hex(), 'marker', memb(h,0xb2ff8,4))
finally:
    h.close()
