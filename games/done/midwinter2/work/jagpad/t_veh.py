import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
snap = sys.argv[1]
seq = sys.argv[2].split(',') if len(sys.argv) > 2 else ['Up', 'Left', 'Right', 'z', 'v', 'x', 'o']
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
nopad = len(sys.argv) > 4 and sys.argv[4] == 'nopad'
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=1024, extra=PADX)
def S(tag):
    d = memb(h, 0xb9ee0, 8)
    print(f'{tag:12s} type={w(h,0x6220):2d} head={w(h,0x6742):4d} thr$6750={sw(h,0x6750):6d} spd$6772={sw(h,0x6772):6d} bank$6746={sw(h,0x6746):6d} '
          f'pitch$674a={sw(h,0x674a):6d} alt$764c={sw(h,0x764c):6d} $6fbe={w(h,0x6fbe):04x} $6872={w(h,0x6872):04x} yaw={sw(h,0x6766):5d} '
          f'PADJ={d[1]:02x} BTN={d[2]:02x} keys={keydown_list(h)}', flush=True)
try:
    time.sleep(2)
    print('type at start', w(h, 0x6220), 'vbl', h.vbl(), flush=True)
    apply_live(h, pre)
    jmode(h)
    time.sleep(1.5)
    S('idle')
    for k in seq:
        k, _, hs = k.partition(':'); hs = float(hs) if hs else secs
        hold(h, k, hs); S(f'hold {k} {hs}')
        rel(h, k, 1.5); S('  released')
    print('bus errors:', [x for x in h._logtext().splitlines() if 'us error' in x.lower() or 'Bus Error' in x][:5])
finally:
    h.close()
