"""NebDoors study 2 (two-way trip, the wall, the wrap): how a tunnel door finds its exit.  Custom levels (ring of ledges on row 1, frog starts col 0 row 2) with a door at (0,2..4)
and different partner configurations at col 8 (and others); the frog presses Up in the door, RAM (x,y,state,anim) sampled during and after.
usage: e203_study.py BUILD WORKDIR [ste|megaste|st] SNAP"""
import sys, os, time, struct, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/tmp/nld/games/in_progress/nebulus/work/editor')
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
g = ring(); door(g, 0); door(g, 8); L.append(('RET', g, 'doors (0,2-4)+(8,2-4): Up, then Up again at the other door'))
g = ring(); door(g, 0); door(g, 8, v=0x80); L.append(('STUCK', g, 'door (0,2-4), pillars (8,2-4): arrive inside the wall, then Right / Left / Up'))
g = ring(); door(g, 12); door(g, 13); door(g, 4); door(g, 5); L.append(('WRAP', g, 'doors cols 12,13 + 4,5: walk Left from col 0 into col 13/12 (x 100..111), Up'))
L = [l for l in L if l[0] in os.environ.get('ONLY', 'RET,STUCK,WRAP').split(',')]
data = ovl.build([ovl.level(1, 0, 48, gr, time=0x0450, name=n) for n, gr, _ in L], [])
assert not ovl.validate(data); open(OUT + 'special.ovl', 'wb').write(data)
def frog(h):
    d = grab(h, 0x33a16, 14, 'f'); x, y, _, c, an, st, spr = struct.unpack('>7H', d)
    return dict(x=x, y=y, dirn=c, st=st, anim=an)
def play(h, idx):
    pick(h, 'Levels'); pick(h, idx); pick(h, 'Play', 1.0)
    ok = wait_running(h, 90); time.sleep(1.0); return ok
def enemies_off(h):
    if W(h, 0x76c04) == 0: h.key('e', hold=0.2); time.sleep(0.5)
    return W(h, 0x76c04)
def key(h, k, down): h._xdo('keydown' if down else 'keyup', '--window', h.win, k)
def tap(h, k, t):
    key(h, k, True); time.sleep(t); key(h, k, False)
def wait_state(h, st, tmo=6):
    t0 = time.time()
    while time.time() - t0 < tmo:
        f = frog(h)
        if f['st'] == st: return f
    return frog(h)
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2); h.debug(f'loadbin {OUT}special.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        open_manager(h)
        for i, (n, gr, desc) in enumerate(L):
            if i: h.key('q', hold=0.3); time.sleep(3.0); open_manager(h)
            ok = play(h, i); P(f'   E trainer (enemies off) word {enemies_off(h):#x}'); f0 = frog(h)
            P(f'== {n}: {desc}  running={ok}  start: {f0}')
            if n == 'WRAP':
                for _ in range(60):
                    f = frog(h)
                    if 98 <= f['x'] <= 109: break
                    tap(h, 'Left', 0.25 if f['x'] > 120 or f['x'] < 20 else 0.1 if f['x'] > 112 else 0.25)
                time.sleep(0.5); fw = frog(h); P(f'   walked Left in taps: x={fw["x"]} (col {fw["x"] >> 3}) state {fw["st"]}')
            else:
                fw = f0
            x_in = fw['x']
            key(h, 'Up', True); time.sleep(0.15); key(h, 'Up', False)
            f1 = wait_state(h, 4, 2); P(f'   Up: state {f1["st"]} (4 = tunnel) x={f1["x"]}')
            for _ in range(6):
                time.sleep(0.5); f2 = frog(h)
                if f2['st'] == 0: break
            P(f'   arrived: x={f2["x"]} (col {f2["x"] >> 3}, entered at x={x_in} col {x_in >> 3}; difference {(f2["x"] - x_in) % 128}) y={f2["y"]} state {f2["st"]}'); h.shot(OUT + f'{n}_arrived.png')
            if n == 'RET':
                key(h, 'Up', True); time.sleep(0.15); key(h, 'Up', False)
                wait_state(h, 4, 2)
                for _ in range(6):
                    time.sleep(0.5); f3 = frog(h)
                    if f3['st'] == 0: break
                P(f'   Up again at the opposite door: x={f3["x"]} (col {f3["x"] >> 3}) y={f3["y"]} state {f3["st"]}')
            if n == 'STUCK':
                time.sleep(3.0); f4 = frog(h); P(f'   3 s later, no input: {f4}')
                for k in ('Right', 'Left'):
                    xb = frog(h); tap(h, k, 0.8); xa = frog(h); P(f'   {k} 0.8 s inside the wall: x {xb["x"]} -> {xa["x"]}, y {xa["y"]}, state {xa["st"]}')
                xb = frog(h); tap(h, 'Up', 0.3); time.sleep(0.4); xa = frog(h); P(f'   Up: {xb} -> {xa}')
        P('errors: ' + repr(errors(h)))
    finally:
        h.close(); time.sleep(1)
run()
open(f'{WD}_e203_study2_{MACH}.log', 'w').write('\n'.join(LOG) + '\n')
