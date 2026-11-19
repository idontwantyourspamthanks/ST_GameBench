"""NebDoors study: how a tunnel door finds its exit.  Custom levels (ring of ledges on row 1, frog starts col 0 row 2) with a door at (0,2..4)
and different partner configurations at col 8 (and others); the frog presses Up in the door, RAM (x,y,state,anim) sampled during and after.
usage: e203_study.py BUILD WORKDIR [ste|megaste|st] SNAP"""
import sys, os, time, struct, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
BUILD, WD, MACH, SNAP = sys.argv[1:5]; OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
LOG = []
def P(line): print(line, flush=True); LOG.append(line)
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
def door(g, c, r0=2, v=0x83):
    for r in range(r0, r0 + 3): g[c][r] = v
L = []
g = ring(); door(g, 0); door(g, 8); L.append(('PAIR', g, 'door (0,2-4) + door (8,2-4)'))
g = ring(); door(g, 0); L.append(('NOPART', g, 'door (0,2-4), col 8 empty (ring ledge under it)'))
g = ring(); door(g, 0); door(g, 8, v=0x80); L.append(('WALL', g, 'door (0,2-4), pillars $80 at (8,2-4)'))
g = ring(); door(g, 0)
for c in (7, 8, 9): g[c][1] = 0
L.append(('HOLE', g, 'door (0,2-4), col 8 empty and the ring ledge removed at cols 7-9'))
g = ring(); door(g, 0); door(g, 9); door(g, 7); L.append(('OFF1', g, 'door (0,2-4), doors at cols 7 and 9 (not 8)'))
g = ring(); door(g, 0); door(g, 8, r0=10); g[8][9] = 0x81; L.append(('OTHERROW', g, 'door (0,2-4), door (8,10-12) with ledge (8,9)'))
g = ring(); door(g, 0); g[8][2] = 0x80; L.append(('WALL1', g, 'door (0,2-4), single pillar at (8,2)'))
g = ring(); door(g, 0); door(g, 8, v=0x87); L.append(('PAIR87', g, 'door (0,2-4) + $87 doors (8,2-4)'))
g = ring(); door(g, 0); door(g, 8); door(g, 8, r0=6); g[8][5] = 0x81; L.append(('PAIRUP', g, 'door (0,2-4)+(8,2-4) and a second door (8,6-8)'))
data = ovl.build([ovl.level(1, 0, 48, gr, time=0x0450, name=n) for n, gr, _ in L], [])
assert not ovl.validate(data); open(OUT + 'special.ovl', 'wb').write(data)
def frog(h):
    d = grab(h, 0x33a16, 14, 'f'); x, y, _, c, _, st, an = struct.unpack('>7H', d)
    return dict(x=x, y=y, dirn=c, st=st, anim=an)
def play(h, idx):
    pick(h, 'Levels'); pick(h, idx); pick(h, 'Play', 1.0)
    ok = wait_running(h, 90); time.sleep(1.0); return ok
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2); h.debug(f'loadbin {OUT}special.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        open_manager(h)
        for i, (n, gr, desc) in enumerate(L):
            if i: h.key('q', hold=0.3); time.sleep(3.0); open_manager(h)
            ok = play(h, i); f0 = frog(h)
            g0 = grab(h, 0x327f0, 0x1000, 'g')
            P(f'== {n}: {desc}  running={ok}  before: {f0}  cells col0 rows2-4 {[g0[r] for r in (2,3,4)]} col8 rows2-4 {[g0[8*256+r] for r in (2,3,4)]}')
            h.shot(OUT + f'{n}_0before.png')
            h._xdo('keydown', '--window', h.win, 'Up'); t0 = time.time(); seen = []
            for k in range(14):
                f = frog(h); seen.append((round(time.time() - t0, 1), f['x'], f['y'], f['st'], f['anim']))
                if k == 4 and f['st'] == 4: h.shot(OUT + f'{n}_1tunnel.png')
                if f['st'] == 4 and f['anim'] >= 0x1d: h._xdo('keyup', '--window', h.win, 'Up')
            h._xdo('keyup', '--window', h.win, 'Up')
            time.sleep(3.0); f1 = frog(h)
            P(f'   samples (t,x,y,state,anim): {seen}')
            P(f'   after 3 s: {f1}  => column {f1["x"] >> 3} (x {f1["x"]}), y {f1["y"]} (row {f1["y"] >> 2})')
            h.shot(OUT + f'{n}_2after.png')
            time.sleep(4.0); f2 = frog(h); P(f'   after 7 s: {f2}')
        P('errors: ' + repr(errors(h)))
    finally:
        h.close(); time.sleep(1)
run()
open(f'{WD}_e203_study_{MACH}.log', 'w').write('\n'.join(LOG) + '\n')
