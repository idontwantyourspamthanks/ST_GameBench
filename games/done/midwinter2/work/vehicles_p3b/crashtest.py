import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
names=sys.argv[2].split(','); snap=sys.argv[1]
live=build_live(names,'crash_'+str(abs(hash(sys.argv[2]))%10**6))
h=Hatari(snapshot=str(SNAP/snap),memsize_kb=2048)
try:
    v=h.vbl(); at_flip(h, apply_cmds(live), v+100)
    time.sleep(6)
    t=h._logtext()
    print('BUSERR' if 'Bus Error' in t else 'ok', [l for l in t.splitlines() if 'Bus Error' in l][:1])
finally: h.close()
