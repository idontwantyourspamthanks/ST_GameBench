"""e205 probe (gate2): fine-grained crumble walk over a lower ledge.  Original header: NebLooksUI crumble / conveyor gate: custom levels with $91 / $a1 / $b1 cells played from the manager (Levels > n > Play) on the title snapshot of the build.
 1) a ring level of plain $81 and the same ring with $91 at cols 3,4: the start screenshots (sky, tower, ledge ring, frog; HUD excluded) are pixel-equal = a crumble ledge looks like a ledge in play
 2) the frog walks right onto the $91 cell: cell value before/after in RAM, frog x/y/state before/after (falls into the sea and dies, or onto the lower $81 at row 0)
 3) conveyors: frog standing on $b1 / $a1 cells without input: x drifts +1 / -1 per step (documents the direction)
usage: e205.py BUILD WORKDIR [ste|megaste|st]"""
import sys, os, time, struct, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
from PIL import Image, ImageChops
BUILD, WD = sys.argv[1], sys.argv[2]; MACH = sys.argv[3] if len(sys.argv) > 3 else 'ste'
SNAP = f'/tmp/nlg/x/title_{MACH}_new.sav'; OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def P(line): print(line, flush=True); LOG.append(line)
if not os.path.exists(SNAP): print('snapshot boot', mk_snap(BUILD, SNAP, MACH, WD + '_snap'), flush=True)
assert b'Crumble ledge' in gzip.open(SNAP).read(), 'stale snapshot'
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
L = []
g = ring(); g[2][1] = g[3][1] = 0x91; g[2][0] = g[3][0] = 0x81; L.append(('CRUMBL', g))                       # crumble over a lower ledge, ring continues both sides
g = ring(); g[6][1] = g[7][1] = 0x91; g[6][0] = g[7][0] = 0x81; g[8][0] = g[9][0] = 0x81; L.append(('LOWWALK', g))  # lower ledge wider than the crumble pair
g = ring(); g[2][1] = g[3][1] = 0x91; L.append(('CRUMB', g))
data = ovl.build([ovl.level(1, 0, 48, gr, time=0x0450, name=n) for n, gr in L], [])
assert not ovl.validate(data); open(OUT + 'probe.ovl', 'wb').write(data)
def cells(h): return grab(h, 0x327f0, 0x1000, 'g')
def frog(h): return struct.unpack('>HH', grab(h, 0x33a16, 4, 'f')) + struct.unpack('>H', grab(h, 0x33a20, 2, 's'))
def play(h, idx):
    pick(h, 'Levels'); pick(h, idx); pick(h, 'Play', 1.0)
    ok = wait_running(h, 90); time.sleep(1.0); return ok
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2); h.debug(f'loadbin {OUT}probe.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('open manager', open_manager(h))
        for idx, nm in enumerate(('CRUMBL', 'LOWWALK', 'CRUMB')):
            chk(f'play {nm}', play(h, idx)); c = cells(h); P(f'{nm}: start frog {frog(h)}; row1 cols2..9 {[c[k*256+1] for k in range(2,10)]} row0 {[c[k*256] for k in range(2,10)]}')
            h._xdo('keydown', '--window', h.win, 'Right'); t0 = time.time(); last = None; n = 0
            while time.time() - t0 < 3.0:
                try: f = frog(h); c = cells(h)
                except Exception: continue
                snap = (f, tuple(c[k*256+1] for k in range(2,10)), tuple(c[k*256] for k in range(2,10)))
                if snap != last: P(f'  t={time.time()-t0:4.2f}s frog(x,y,st)={f} row1[2..9]={list(snap[1])} row0[2..9]={list(snap[2])}'); last = snap; n += 1
                if n > 60: break
            h._xdo('keyup', '--window', h.win, 'Right'); h.shot(OUT + f'p_{nm}.png'); time.sleep(2.0); f = frog(h); P(f'  2 s after releasing: frog {f}')
            h.key('q', hold=0.3); time.sleep(3.0); chk('open manager', open_manager(h))
        chk('no Address/Bus Error/exception', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e205_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
