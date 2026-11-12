import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / '1mb_ingame_foot.sav'), extra=[])
try:
    time.sleep(2); apply_live(h, pre); jmode(h); time.sleep(6)
    S(h, 'J idle, no pad cfg')
    print('PADOLD', memb(h, 0xb9ee4, 4).hex(), 'ROT', memb(h, 0xb9eec, 1).hex(), 'ESCCNT', memb(h, 0xb9ee3, 1).hex())
    print('acc', memb(h, 0x6fb6, 8).hex(), 'ramps', memb(h, 0x75b2, 16).hex(), '$75a2', memb(h, 0x75a0, 12).hex())
finally:
    h.close()
