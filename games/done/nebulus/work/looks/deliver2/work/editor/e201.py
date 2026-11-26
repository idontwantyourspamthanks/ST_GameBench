"""NebLooksUI crumble / conveyor gate: custom levels with $91 / $a1 / $b1 cells played from the manager (Levels > n > Play) on the title snapshot of the build.
 1) a ring level of plain $81 and the same ring with $91 at cols 3,4: the start screenshots (sky, tower, ledge ring, frog; HUD excluded) are pixel-equal = a crumble ledge looks like a ledge in play
 2) the frog walks right onto the $91 cell: cell value before/after in RAM, frog x/y/state before/after (falls into the sea and dies, or onto the lower $81 at row 0)
 3) conveyors: frog standing on $b1 / $a1 cells without input: x drifts +1 / -1 per step (documents the direction)
usage: e201.py BUILD WORKDIR [ste|megaste|st]"""
import sys, os, time, struct, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
from PIL import Image, ImageChops
BUILD, WD = sys.argv[1], sys.argv[2]; MACH = sys.argv[3] if len(sys.argv) > 3 else 'ste'
SNAP = f'/tmp/neblooksui/title_{MACH}_new.sav'; OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
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
L = []
L.append(('NORMAL', ring()))
g = ring(); g[3][1] = 0x91; g[4][1] = 0x91; L.append(('CRUMB', g))
g = ring(); g[2][1] = 0x91; g[3][1] = 0x91; g[2][0] = 0x81; g[3][0] = 0x81; L.append(('CRUMBL', g))
g = ring(); g[0][1] = g[1][1] = g[2][1] = 0xb1; L.append(('CONVR', g))
g = ring()
for a in (14, 15, 0, 1, 2): g[a][1] = 0xa1
L.append(('CONVL', g))
data = ovl.build([ovl.level(1, 0, 48, gr, time=0x0450, name=n) for n, gr in L], [])
assert not ovl.validate(data)
open(OUT + 'special.ovl', 'wb').write(data)
GRID = 0x327f0
def cells(h):
    d = grab(h, GRID, 0x1000, 'g'); return d
def frog(h):
    return struct.unpack('>HH', grab(h, 0x33a16, 4, 'f')) + struct.unpack('>H', grab(h, 0x33a20, 2, 's'))
BOX = (96, 110, 736, 290)
def play(h, idx):
    pick(h, 'Levels'); pick(h, idx); pick(h, 'Play', 1.0)
    ok = wait_running(h, 90); time.sleep(1.0); return ok
def back_to_title(h):
    h.key('q', hold=0.3); time.sleep(3.0)
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2); h.debug(f'loadbin {OUT}special.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        # --- 1 look
        chk('open manager', open_manager(h))
        chk('play NORMAL', play(h, 0)); h.shot(OUT + '01_normal.png'); c0 = cells(h)
        back_to_title(h); chk('open manager again', open_manager(h))
        chk('play CRUMB', play(h, 1)); h.shot(OUT + '02_crumb_start.png'); c1 = cells(h)
        chk('CRUMB grid has $91 at (3,1),(4,1)', [c1[3 * 256 + 1], c1[4 * 256 + 1]], [0x91, 0x91])
        d = ImageChops.difference(Image.open(OUT + '01_normal.png').convert('RGB').crop(BOX), Image.open(OUT + '02_crumb_start.png').convert('RGB').crop(BOX)).getbbox()
        chk('start screenshot crop (sky, skyline, tower, ledge ring, frog) of CRUMB == NORMAL (a crumble ledge is drawn exactly like a ledge)', d, None)
        # --- 2 walk onto it
        P(f'before: frog (x,y,state)={frog(h)} row1 cols2..5={[c1[k * 256 + 1] for k in (2, 3, 4, 5)]}')
        h._xdo('keydown', '--window', h.win, 'Right')
        seen = []; fell = False
        for i in range(30):
            time.sleep(0.2); c = cells(h); f = frog(h)
            row = [c[k * 256 + 1] for k in (2, 3, 4, 5)]
            seen.append((f, row))
            if row[1] == 0 and not fell:
                fell = True; P(f't{i}: cell (3,1) cleared: frog {f} row1 cols2..5={row}'); h.shot(OUT + '03_after_crumble.png')
            if fell and i > 0 and f[2] not in (8, 0): P(f't{i}: frog {f} row1 {row}')
            if fell and f[2] == 10: break
        h._xdo('keyup', '--window', h.win, 'Right')
        chk('the $91 cell was cleared when the frog walked onto it', fell)
        P('frog after: ' + repr(seen[-1]))
        # lower platform: level CRUMBL ($91 at cols 2,3 row 1 with a plain $81 at row 0 below them)
        h._xdo('keyup', '--window', h.win, 'Right')
        back_to_title(h); chk('open manager', open_manager(h)); chk('play CRUMBL', play(h, 2)); c2 = cells(h)
        chk('CRUMBL grid: $91 at (2,1),(3,1), $81 at (2,0),(3,0)', [c2[2 * 256 + 1], c2[3 * 256 + 1], c2[2 * 256], c2[3 * 256]], [0x91, 0x91, 0x81, 0x81])
        P(f'CRUMBL before: frog (x,y,state)={frog(h)}'); h._xdo('keydown', '--window', h.win, 'Right')
        lower = None
        for i in range(40):
            time.sleep(0.15); c = cells(h); f = frog(h)
            if c[2 * 256 + 1] == 0 or c[3 * 256 + 1] == 0:
                P(f'  t{i}: crumble cell cleared: frog {f} cells (2,1),(3,1),(2,0),(3,0) = {[c[2*256+1], c[3*256+1], c[2*256], c[3*256]]}'); time.sleep(0.8)
                lower = (frog(h), [cells(h)[2 * 256], cells(h)[3 * 256]]); break
        h._xdo('keyup', '--window', h.win, 'Right')
        P(f'CRUMBL 0.8 s later: frog (x,y,state) {lower}'); h.shot(OUT + '04_lower.png')
        chk('the frog fell one row and stands on the row 0 ledge (state 0, y = 0 = on the lower floor)', lower is not None and lower[0][2] == 0, True)
        back_to_title(h); chk('open manager', open_manager(h))
        # --- 3 conveyors
        for idx, nm in ((3, 'CONVR'), (4, 'CONVL')):
            chk(f'play {nm}', play(h, idx)); xs = []
            for i in range(6): xs.append(frog(h)[0]); time.sleep(0.35)
            P(f'{nm}: frog x without input over 2 s: {xs}'); h.shot(OUT + f'05_{nm}.png')
            back_to_title(h); chk('open manager', open_manager(h))
        chk('no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e201_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
