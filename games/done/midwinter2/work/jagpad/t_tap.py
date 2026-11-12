"""Tap sensitivity: N taps of each pad button for several durations, counting (a) pad make events (breakpoint at the blob's `.make`)
and (b) for Option the game's own Esc consumption ($1b446 = `clr.b 1(a0)` after `tst.b $7687`). argv: snapshot [esc0]  (esc0 = poke ESCMIN to 0)."""
import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
snap = sys.argv[1] if len(sys.argv) > 1 else 'raid_speedboat_iquitos.sav'
esc0 = len(sys.argv) > 2 and sys.argv[2] == 'esc0'
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
img = (Path(pre + '.img')).read_bytes()
blob = img[0x6500:0x6500 + 0x380]
needle = bytes.fromhex('31c07684' '13bc00ff0000')
make_addr = 0xb9500 + blob.index(needle)
esc_needle = bytes.fromhex('13fc0010000b9ee3')
esc_addr = 0xb9500 + blob.index(esc_needle)
print(f'make at ${make_addr:x}, ESCMIN init at ${esc_addr:x}')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=1024, extra=PADX)
def hits(tag):
    return len(re.findall(r'matched', h._logtext().split(tag)[-1])) if False else None
try:
    time.sleep(2)
    apply_live(h, pre)
    if esc0:
        h.debug(f'w ${esc_addr + 3:x} $00', 0.5)
    jmode(h); time.sleep(1.5)
    h.debug('b all', 0.3)
    h.cmd(f'hatari-debug b pc = ${make_addr:x} :trace'); time.sleep(0.4)
    h.debug('w $50d4 $4e $75', 0.5)       # the game's Esc handler becomes rts: it never reads or clears $7687
    h.cmd('hatari-debug b pc = $31568 && ($7687).b ! 0 :trace'); time.sleep(0.4)
    res = {}
    for key, name in [('o', 'Option')]:
        for ms in (30, 60, 100, 150, 250):
            n0 = h._logtext()
            for i in range(10):
                h._xdo('keydown', '--window', h.win, key); time.sleep(ms / 1000.0)
                h._xdo('keyup', '--window', h.win, key); time.sleep(0.9)
            new = h._logtext()[len(n0):]
            mk = len(re.findall(r'^1\. CPU breakpoint', new, re.M))
            eh = len(re.findall(r'^2\. CPU breakpoint', new, re.M))
            res[(name, ms)] = (mk, eh)
            print(f'{name:10s} tap {ms:3d} ms x10: make hits={mk}  polls seeing Esc down={eh}', flush=True)
    print(h._logtext()[-800:])
finally:
    h.close()
