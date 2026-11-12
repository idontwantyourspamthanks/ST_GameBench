import sys, time, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
dx, dy = int(sys.argv[1]), int(sys.argv[2])
h = Hatari(snapshot='/home/ryan/Code/AtariST/midwinter2/work/snapshots/1mb_ingame_foot.sav', memsize_kb=1024)
try:
    px, py = 25600, 25600
    x, y = px+dx, py+dy
    cmds = [
     "w $3538 " + " ".join("$%02x" % ((x>>s)&255) for s in (24,16,8,0)),   # +6
     "w $353c " + " ".join("$%02x" % ((y>>s)&255) for s in (24,16,8,0)),   # +a
     "w $3560 $00 $01",   # +2e = unit type 1
     "w $356c $00 $00",   # +3a state 0
    ]
    for c in cmds: h.debug(c, 0.3)
    for i in range(4):
        time.sleep(2.5)
        h.shot(f'/tmp/npc_{dx}_{dy}_{i}.png')
        print(h.debug('m $3532 66', 0.5)[-400:].replace('\n',' | '))
finally:
    h.close()
