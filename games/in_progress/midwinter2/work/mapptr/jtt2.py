#!/usr/bin/env python3
"""J (joystick) mode on the Raids island map, Hatari TT / TOS 3.06 / 4 MB, --joy1 keys. Cold boot -> J -> corridor -> RAIDS -> NOVICE -> map;
80 s time series on the map (stick moves + stillness), then island select (SPACE) + text page + '?' boss page, shots + pointer detection.
usage: jtt.py NAME BUILD [MACHINE MEM]"""
import sys, time, math
from pathlib import Path
from PIL import Image
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
name, bd = sys.argv[1:3]
machine = sys.argv[3] if len(sys.argv) > 3 else 'tt'
mem = int(sys.argv[4]) if len(sys.argv) > 4 else 4096
out = ROOT/'work/mapptr'/name; out.mkdir(exist_ok=True)
tt = machine == 'tt'
h = Hatari(snapshot=None, machine=machine, tos=MACHINE_TOS[machine], memsize_kb=mem, game_dir=ROOT/bd,
           extra=(['--mmu','true'] if tt else []) + ['--joy1', 'keys'])
T0 = time.time()
def P(*a): print(f'{time.time()-T0:6.1f}s', *a, flush=True)
def arrow(im, px, py):
    ox, oy = (0, 0) if tt else (96, 58)
    cx, cy = ox+2*px, oy+2*py; c = 0; p = im.load()
    for yy in range(cy-2, cy+28):
        for xx in range(cx-2, cx+22):
            if 0 <= xx < im.width and 0 <= yy < im.height:
                r, g, b = p[xx, yy]
                if r > 200 and 50 < g < 140 and b < 80: c += 1
    return c
def pos(): return h.peekw(0x6fae), h.peekw(0x6fb2)
def tap(key, secs):
    h._xdo('keydown', '--window', h.win, key); time.sleep(secs); h._xdo('keyup', '--window', h.win, key); time.sleep(0.25)
def move_to(tx, ty, tol=4, tries=40):
    for _ in range(tries):
        x, y = pos()
        dx, dy = tx - x, ty - y
        if abs(dx) <= tol and abs(dy) <= tol: return True
        for d, pk, nk in ((dx, 'Right', 'Left'), (dy, 'Down', 'Up')):
            if abs(d) > tol:
                tap(pk if d > 0 else nk, max(0.05, min(0.6, 0.55 * math.sqrt(abs(d) / 450.0))))
    return False
def click(): h.key('comma', 0.3)
def shot(tag):
    s = h.shot(str(out / f'{tag}.png')); px, py = pos()
    c = arrow(Image.open(s).convert('RGB'), px, py)
    P(f'{tag} mode={h.peekw(0x700a)} eb76={h.peekw(0xeb76):x} px={px} py={py} arrow_px={c}')
    return c
try:
    time.sleep(70 if tt else 25)
    ref = ROOT / 'work/ref/mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 36'); time.sleep(6)   # J
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45 if tt else 4)
    P('J mode word $eb76 =', hex(h.peekw(0xeb76)))
    for i in range(3): shot(f'corridor{i}'); time.sleep(2)
    for _ in range(5):
        P('door ok', move_to(98, 92, tol=2)); click()
        t0 = time.time(); ok = False
        while time.time() - t0 < 60:
            time.sleep(4)
            if h.peekw(0xEB9C) == 0xFFFF and mw2raids._screen_has_levels(h): ok = True; break
        if ok: break
    P('level screen', ok); shot('level')
    P('novice ok', move_to(40, 168, tol=3)); click()
    t0 = time.time(); k = 0
    stops = [(60, 60), (200, 120), (120, 150), (250, 50)]
    while time.time() - t0 < 80:
        if k % 5 == 3: move_to(*stops[(k // 5) % 4], tol=6, tries=6)
        f = h.fps(50)
        shot(f'm{k:03d}'); P('   flips/50vbl', f['flips']); k += 1
    # island select by SPACE on Dhafra
    P('hover dhafra', move_to(175, 60, tol=4)); shot('hover')
    h.key('space'); t0 = time.time(); k = 0
    while time.time() - t0 < 50:
        shot(f's{k:03d}'); k += 1
    P('book', move_to(62, 172, tol=4)); click(); t0 = time.time(); k = 0
    while time.time() - t0 < 25:
        shot(f'b{k:03d}'); k += 1
    P('question mark', move_to(22, 178, tol=4)); click(); t0 = time.time(); k = 0
    while time.time() - t0 < 25:
        shot(f'q{k:03d}'); k += 1
    h.savemem(str(out / 'end.sav'))
finally:
    h.close()
