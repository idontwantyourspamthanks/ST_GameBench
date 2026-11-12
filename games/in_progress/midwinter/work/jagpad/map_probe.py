import sys, time
from jlib import *
which = sys.argv[1]   # real | pad
h = MW1(snapshot=str(SNAP / '1mb_ski_stand_J.sav'), extra=PAD)
S = Sampler(h, [(0xb6bf0, 8), (0x12d5e, 4), (0x1efde, 2), (0x2c324, 4), (0x24fa2, 8), (0x24fba, 2), (0x62b8, 2)])
def show(tag):
    r = S(); P = r[0xb6bf0]
    print(f"{tag:14s} vbl={r['vbl']} PADST={P[0]:02x} step={r[0x12d5e].hex()} menu={r[0x1efde].hex()} ctx={r[0x62b8].hex()} key24={r[0x2c324].hex()} ptr=({int.from_bytes(r[0x24fa2][:4],'big')>>16},{int.from_bytes(r[0x24fa2][4:],'big')>>16}) btn={r[0x24fba].hex()} flips50={h.fps(50)['flips']}", flush=True)
try:
    time.sleep(2)
    if which == 'pad':
        apply_live(h, str(HERE / 'jaglive'))
    time.sleep(1.5)
    show('ski')
    if which == 'pad':
        kd(h, 'n1'); time.sleep(1.5); ku(h, 'n1')
    else:
        h._xdo('key', '--window', h.win, 'm')
    time.sleep(3); show('map open')
    h.shot('/tmp/jag_map_open.png')
    h.click_at((612, 450), 3.0); show('after click')
    h.shot('/tmp/jag_map_closed.png')
    if which == 'pad':
        kd(h, 'down'); time.sleep(0.3); ku(h, 'down'); time.sleep(0.5); show('pad down tap')
        kd(h, 'up'); time.sleep(0.15); ku(h, 'up'); time.sleep(0.5); show('pad up tap')
        kd(h, 'B'); time.sleep(0.4); ku(h, 'B'); time.sleep(3); show('after pad B'); h.shot('/tmp/jag_map_closed2.png')
    else:
        h.click(); time.sleep(3); show('after 2nd click')
finally:
    h.close()
