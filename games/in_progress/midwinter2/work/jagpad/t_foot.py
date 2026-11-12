import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
snap = sys.argv[1] if len(sys.argv) > 1 else '1mb_ingame_foot.sav'
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=1024, extra=PADX)
def S(tag):
    acc = memb(h, 0x6fb6, 8)
    ax = int.from_bytes(acc[0:4], 'big', signed=True) / 65536; ay = int.from_bytes(acc[4:8], 'big', signed=True) / 65536
    d = memb(h, 0xb9ee0, 8)
    print(f'{tag:14s} FLAG={d[0]} PADJ={d[1]:02x} BTN={d[2]:02x} OLD={d[4:8].hex()} $75a9={memb(h,0x75a9,1).hex()} accX={ax:8.2f} accY={ay:8.2f} '
          f'$6872={w(h,0x6872):04x} $6fbe={w(h,0x6fbe):04x} $7684={w(h,0x7684):04x} keys={keydown_list(h)} yaw$6766={sw(h,0x6766)} $6768={sw(h,0x6768)}', flush=True)
try:
    time.sleep(2)
    apply_live(h, pre)
    print('sites', [memb(h, a, 6).hex() for a in (0x262c2, 0x26b66, 0x26bea)])
    mmode(h); time.sleep(1); S('M idle')
    hold(h, 'Left', 1.0); S('M hold Left'); rel(h, 'Left')
    jmode(h); time.sleep(1.2); S('J idle')
    for k in ['Left', 'Right', 'Up', 'Down', 'z', 'x', 'v', 'o', 'p', 'q', 'w', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
        hold(h, k, 1.2); S('hold ' + k); rel(h, k)
    S('released')
    print('bus errors', sum('Bus Error' in x for x in h._logtext().splitlines()))
finally:
    h.close()
