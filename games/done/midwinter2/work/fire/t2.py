import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/jagpad')
from jt import *
for snap in sys.argv[1:]:
    h = Hatari(snapshot=str(SNAP/snap), extra=['--joy1','none'])
    try:
        time.sleep(3)
        print(snap, 'type', w(h,0x6220), 'sel', w(h,0x18112), 'ammo', memb(h,0xef8a,32).hex(), 'cool 4072/4074/7582', w(h,0x4072), w(h,0x4074), sw(h,0x7582), '677c', w(h,0x677c))
    finally: h.close()
