import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
from jt import S as jt_S
snap = sys.argv[1] if len(sys.argv) > 1 else '1mb_ingame_foot.sav'
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=1024, extra=PADX)
def S(tag): jt_S(h, tag)
try:
    time.sleep(2)
    apply_live(h, pre)
    print('sites', [memb(h, a, 6).hex() for a in (0x262f6, 0x26b66, 0x26bea, 0xb433a)])
    mmode(h); time.sleep(1); S('M idle')
    hold(h, 'Left', 1.0); S('M hold Left'); rel(h, 'Left')
    jmode(h); time.sleep(1.2); S('J idle')
    for k in ['Left', 'Right', 'Up', 'Down', 'z', 'x', 'v', 'o', 'p', 'q', 'w', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
        hold(h, k, 1.2); S('hold ' + k); rel(h, k)
    S('released')
    print('bus errors', sum('Bus Error' in x for x in h._logtext().splitlines()))
finally:
    h.close()
