"""J mode menu navigation with the pad only (stick moves the pointer, A clicks): corridor -> CONTROL door -> map screen."""
import sys, time, math
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / 'corridor_agent.sav'), extra=PADX)
def pos(): return w(h, 0x6fae), w(h, 0x6fb2)
def goto(tx, ty, tol=7):
    for it in range(10):
        x, y = pos()
        dx, dy = tx - x, ty - y
        print(f'  at ({x},{y}) target ({tx},{ty})', flush=True)
        if abs(dx) <= tol and abs(dy) <= tol: return True
        for d, pk, nk in ((dx, 'Right', 'Left'), (dy, 'Down', 'Up')):
            if abs(d) > tol:
                n = max(1, round(-3.5 + math.sqrt(12.25 + 8 * max(abs(d) - 4, 1))))      # VBLs: 0.125 n^2 + 0.875 n = |d|
                k = pk if d > 0 else nk
                hold(h, k, n * 0.02 + 0.03); rel(h, k, 0.25)
    return False
try:
    time.sleep(3)
    apply_live(h, pre)
    jmode(h); time.sleep(1.5)
    print("arrived", goto(159, 63, tol=3))
    h.shot(str(G / 'work/jagpad/menu_before_click.png'))
    v0 = w(h, 0x700a)
    hold(h, 'z', 0.4); print('during A: $6fbe', hex(w(h, 0x6fbe)), '$62e6', hex(w(h, 0x62e6)), '$62e8', hex(w(h, 0x62e8)), 'click pos', w(h, 0x6faa), w(h, 0x6fac)); rel(h, 'z', 3)
    print('after A click: $6fbe was pulsed; $700a', v0, '->', w(h, 0x700a))
    time.sleep(12)
    h.shot(str(G / 'work/jagpad/menu_after_click.png'))
finally:
    h.close()
