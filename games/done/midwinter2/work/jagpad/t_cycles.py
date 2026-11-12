"""Cycles per VBL spent in the jag blobs: Hatari CPU profile over ~250 VBLs of a snapshot.
usage: t_cycles.py [snapshot]   (STE 1 MB TOS 1.62, 8 MHz; 1 VBL at 50 Hz = 160256 cycles)"""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
snap = sys.argv[1] if len(sys.argv) > 1 else '1mb_ingame_foot.sav'
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
_blob = (Path(build_live(only, 'jag_all') + '.img')).read_bytes()[0x6500:0x6a00]
POLL_ENTRY = 0xb9500 + _blob.index(bytes.fromhex('4a790000eb76'))
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=1024, extra=PADX)
def region(rows, lo, hi): return sum(c for a, c in rows if lo <= a < hi)
def run(tag, keys=()):
    for k in keys: h._xdo('keydown', '--window', h.win, k)
    time.sleep(1.0)
    rows = h.profile(250)
    for k in keys: h._xdo('keyup', '--window', h.win, k)
    entry = sum(c for a, c in rows if a == POLL_ENTRY)       # tst.w $eb76.l = 16 cycles per VBL
    n = entry // 16
    poll = region(rows, 0xb9500, 0xb9800) + region(rows, 0x262f6, 0x262fc) - 152 * n   # blob + the site jmp, minus the movem/rte that used to sit at the site
    dirb = region(rows, 0xb9e00, 0xb9e50)
    tot = sum(c for a, c in rows)
    p5 = sum(c for a, c in rows if 0xb4300 <= a < 0xb4400)
    jm = 'M mode' not in tag
    net = poll + (dirb + 14 * n if jm else 0)
    print(f'{tag:28s} TOTAL NET {net / max(n,1):.0f}/VBL = {100 * net / max(n,1) / 160256:.3f} % at 50 Hz, {100 * net / max(n,1) * 60 / 8e6:.3f} % at 60 Hz | polls={n} net jag_poll={poll} ({poll / max(n,1):.0f}/VBL = {100 * poll / max(n,1) / 160256:.3f} %)  jag_dir+btn={dirb} ({dirb / max(n,1):.0f}/VBL)  '
          f'p5_ctl_vbl={p5} ({p5 / max(n,1):.0f}/VBL)  profiled total={tot}', flush=True)
    return rows
try:
    time.sleep(2)
    apply_live(h, pre)
    time.sleep(3)   # first VBL: probe
    mmode(h); time.sleep(1); run('M mode (jag idle path)')
    jmode(h); time.sleep(1.5)
    run('J mode, pad idle')
    run('J mode, hold Up+z+o', ['Up', 'z', 'o'])
    run('J mode, hold 1+5+9+0', ['1', '5', '9', '0'])
finally:
    h.close()
