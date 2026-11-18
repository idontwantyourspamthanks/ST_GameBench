"""Cold boot BUILD; on the game's title tap F10 (xdotool, HOLD s) repeatedly; a tap 'registers' when the manager opens ($70 != $382d8 = editor's own VBL);
leave with another F10; tally by title page word $3d5b6. Then D (held 0.3 s) x3. usage: t30.py BUILD TAG [HOLD] [PER_PAGE]"""
import sys, json
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
build, tag = sys.argv[1], sys.argv[2]
hold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
per = int(sys.argv[4]) if len(sys.argv) > 4 else 30
h = boot(build, tag)
def vec70():
    b = rd(h, 0x70, 4, 0.35); return int.from_bytes(b, 'big') if b else None
def page():
    b = rd(h, 0x3d5b6, 2, 0.35); return int.from_bytes(b, 'big') if b else None
try:
    t0 = time.time()
    while time.time() - t0 < 120:
        time.sleep(2)
        if h._marker_present(): break
    time.sleep(4)
    print('title up after', round(time.time() - t0), 's; $70 =', hex(vec70() or 0), 'NEPO marker', rd(h, 0xb0020, 4))
    import random
    rng = random.Random(5)
    tally = {0: [0, 0], 1: [0, 0], 2: [0, 0]}
    done = 0
    for target in (2, 1, 0):
        while tally[target][1] < per:
            # wait until the title shows the target page, then tap after a random 0..1.2 s (the page lasts ~4.4 s)
            tw = time.time()
            while page() != target and time.time() - tw < 40: pass
            time.sleep(rng.uniform(0.0, 1.2))
            pg = page()
            st = tally.setdefault(pg, [0, 0])
            tap(h, 'F10', hold); time.sleep(0.9)
            opened = vec70() != 0x382d8
            st[1] += 1; st[0] += 1 if opened else 0
            done += 1
            if opened:
                tap(h, 'F10', 0.3); time.sleep(0.9)
                if vec70() != 0x382d8:
                    print('manager did not close; try again'); tap(h, 'F10', 0.4); time.sleep(1.0)
            if done % 15 == 0: print(done, {hex(k or 0): v for k, v in tally.items()}, flush=True)
    print('F10 tap hold', hold, 'registered/tapped by page word:', {hex(k or 0): f'{v[0]}/{v[1]}' for k, v in tally.items()})
    d_ok = 0
    for i in range(3):
        h._xdo('keydown', '--window', h.win, 'd'); time.sleep(0.3); h._xdo('keyup', '--window', h.win, 'd'); time.sleep(1.0)
        if vec70() != 0x382d8:
            d_ok += 1; tap(h, 'F10', 0.3); time.sleep(1.0)
        time.sleep(1.0)
    print('D (held 0.3 s) opened the manager', d_ok, '/ 3')
finally:
    h.close()
