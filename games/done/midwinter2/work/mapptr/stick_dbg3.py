import sys, time, math
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari
h = Hatari(snapshot=str(ROOT/'work/snapshots/corridor_agent.sav'), memsize_kb=2048, extra=['--joy1','keys'])
def pos(): return h.peekw(0x6fae), h.peekw(0x6fb2)
def tap(key, secs):
    h._xdo('keydown', '--window', h.win, key); time.sleep(secs); h._xdo('keyup', '--window', h.win, key); time.sleep(0.25)
def move_to(tx, ty, tol=4, tries=40):
    for _ in range(tries):
        x, y = pos(); dx, dy = tx - x, ty - y
        if abs(dx) <= tol and abs(dy) <= tol: return True
        for d, pk, nk in ((dx, 'Right', 'Left'), (dy, 'Down', 'Up')):
            if abs(d) > tol: tap(pk if d > 0 else nk, max(0.05, min(0.6, 0.55 * math.sqrt(abs(d) / 450.0))))
try:
    time.sleep(3)
    h.debug('w $eb76 $ff $ff $00 $00 $00 $00')
    for tgt in ((102,86),(98,92),(95,100)):
        print('target', tgt, move_to(*tgt, tol=2), pos())
        h.key('comma', 0.4)
        for j in range(6):
            time.sleep(0.5); print('  ', hex(h.peekw(0x700a)), hex(h.peekw(0x6fbe)), hex(h.peekw(0x6872)), hex(h.peekw(0x62e6)))
        h.shot('/home/ryan/Code/AtariST/midwinter2/work/mapptr/dbg3_%d.png' % tgt[0])
finally: h.close()
