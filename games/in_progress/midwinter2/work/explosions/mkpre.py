import sys, time; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
out='/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/explosions/'
h = Hatari(snapshot=str(SNAP/'raid_jeep_dhafra.sav'))
try:
    time.sleep(1)
    h.key('space', hold=0.3)
    time.sleep(0.3)
    h.savemem(out+'jeep_fired.sav')
    base=0x3532+3*0x42
    b = memb(h, base, 0x42)
    print('slot3 type', sw(b[0x2e:0x30]), 'state', sw(b[0x3a:0x3c]), 'life', sw(b[0x36:0x38]), 'vbl', h.vbl())
finally:
    h.close()
