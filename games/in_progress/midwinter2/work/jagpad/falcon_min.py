"""Falcon (TOS 4.04, 4 MB) cold boot of the HD jag build to the HQ hall, then J mode + pad keys: FLAG must be 2 (68020+: no pad access)."""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
from stharness import MACHINE_TOS
h = Hatari(snapshot=None, memsize_kb=4096, game_dir=G / (sys.argv[1] if len(sys.argv) > 1 else 'build/jag_a'), machine='falcon', tos=MACHINE_TOS['falcon'], extra=PADX)
try:
    time.sleep(25)
    ref = G / 'work' / 'ref' / 'mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): print('M/J/K screen', flush=True); break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): print('M accepted', flush=True); break
    time.sleep(20)
    print('marker', memb(h, 0xb2ff8, 4), 'sites', [memb(h, a, 6).hex() for a in (0x262c2, 0x26b66, 0x26bea)], '$700a', w(h, 0x700a), flush=True)
    jmode(h); time.sleep(2)
    for k in ['Left', 'Up', 'x', 'z', 'o', '1']:
        hold(h, k, 1.2); rel(h, k, 0.5)
        d = memb(h, 0xb9ee0, 16)
        print(f'hold {k}: FLAG={d[0]} PADJ={d[1]:02x} GB={d[8:12].hex()} keys={keydown_list(h)}', flush=True)
    v0 = h.vbl(); time.sleep(2); print('VBL advancing', h.vbl() - v0)
    print('bus-error log lines', bus_errors(h)[:4])
    h.shot(str(G / f'work/jagpad/np_falcon_{(sys.argv[1] if len(sys.argv) > 1 else 'jag').split(chr(47))[-1]}_end.png'))
finally:
    h.close()
