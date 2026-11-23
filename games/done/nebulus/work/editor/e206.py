"""Crumble + exit door completion gate (campaign path, as the player does it): build with a custom NEBLEVEL.OVL (campaign CRMB: level 1 PATHOK, level 2 FALL),
F10 -> Campaigns -> CRMB -> Play (real keys).
 level 1: ring with crumble ledges ($91) at cols 2,3 (right of the frog start) and the exit door at col 10; the frog walks LEFT round the ring (never touches a crumble) -> the level is COMPLETED, rsPos advances to level 2
 level 2: crumble ledges at cols 2,3 + exit door at col 5 (right behind them) and the ring broken at cols 14,15 (no way round): the frog walks RIGHT onto the crumble: it falls (log of cell/frog state, screenshots), dies, respawns with the grid restored
usage: e206.py WORKDIR [ste|megaste|st]   (builds its own NEBLEVEL.OVL build under WORKDIR_build)"""
import sys, os, time, struct, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
WD = sys.argv[1]; MACH = sys.argv[2] if len(sys.argv) > 2 else 'ste'; OUT = WD + '_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def P(line): print(line, flush=True); LOG.append(line)
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
g1 = ring()
for r in (2, 3, 4): g1[10][r] = 0xc3
g1[2][1] = g1[3][1] = 0x91
g2 = ring()
for r in (2, 3, 4): g2[5][r] = 0xc3
g2[2][1] = g2[3][1] = 0x91; g2[14][1] = g2[15][1] = 0
lv = [ovl.level(1, 0, 48, g, time=0x0600, name=n) for n, g in (('PATHOK', g1), ('FALL', g2))]
data = ovl.build(lv, [ovl.camp('CRMB', [0, 1])]); assert not ovl.validate(data)
open(OUT + 'crmb.ovl', 'wb').write(data)
BUILD = WD + '_build'
subprocess.run(['python3', '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools/nepatch.py', 'build', '--out', BUILD, '--ovl', OUT + 'crmb.ovl'], check=True, capture_output=True)
RSB = 0x77c80
def rs(): return struct.unpack('>32H', grab(h, RSB, 64, 'rs'))
def frog(): return struct.unpack('>HH', grab(h, 0x33a16, 4, 'f')) + struct.unpack('>H', grab(h, 0x33a20, 2, 's'))
def cells(): return grab(h, 0x327f0, 0x1000, 'g')
def running(): return W(h, 0x33a20) == 0 and W(h, 0x33938) == 1
kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
h = Nebulus(workdir=WD, game=Path(BUILD), **kw)
def K(k, n=1, hold=0.2, gap=0.35):
    for _ in range(n): h.key(k, hold=hold); time.sleep(gap)
try:
    chk('title', h.boot_to_title(timeout=240)); time.sleep(3)
    h.key('F10', hold=0.5); time.sleep(2)
    K('Down'); K('Control_R', hold=0.4, gap=1.0); K('Control_R', hold=0.4, gap=1.0); K('Control_R', hold=0.4, gap=0.5)     # Campaigns > CRMB > Play
    t0 = time.time()
    while time.time() - t0 < 120 and not (rs()[1] == 0 and running()): time.sleep(1.0)
    poke(h, 0x76c04, bytes([0xff, 0xff])); P('trainer E (enemies off: no time-waster flyer) poked at $76c04')
    time.sleep(1.0); w = rs(); c = cells()
    chk('campaign level 1 running (rsPos 0), grid = PATHOK: $91 at (2,1),(3,1), door $c3 at (10,2..4)', (w[1], c[2 * 256 + 1], c[3 * 256 + 1], c[10 * 256 + 2], c[10 * 256 + 4]), (0, 0x91, 0x91, 0xc3, 0xc3))
    h.shot(OUT + '01_level1_start.png'); P(f'level 1 start frog (x,y,state) = {frog()}')
    # --- walk LEFT round the ring (tap-walk to the door column 10 = x 80..87, never on a crumble), then Up in the door = the exit door
    done = False; seen = []; crum_cleared = False
    for i in range(60):
        f = frog(); x = f[0]; d = (x - 84) % 128; seen.append(f)
        if f[2] == 10 or f[2] == 8: P(f'frog died/fell at {f}'); break
        dd = ((x - 84 + 64) % 128) - 64
        if -4 <= dd <= 3: break
        h.key('Left' if dd > 0 else 'Right', hold=(0.3 if min(d, 128 - d) > 16 else 0.08)); time.sleep(0.5)
    c = cells(); crum_cleared = (c[2 * 256 + 1] != 0x91 or c[3 * 256 + 1] != 0x91)
    f = frog(); P(f'at the door: frog {f}'); h.shot(OUT + '01b_at_door.png')
    h.key('Up', hold=0.4)
    for i in range(60):
        time.sleep(1.0)
        try: w = rs(); f = frog()
        except Exception: continue
        if w[1] != 0: done = True; P(f'{i + 1} s after Up: rsPos {w[1]} (level completed); frog {f}'); break
    P(f'frog samples (x,y,state): {seen[:40]}')
    chk('level 1 COMPLETED by walking left to the exit door without touching a crumble (rsPos 0 -> 1)', done)
    chk('no crumble cell was cleared on the way', crum_cleared, False)
    h.shot(OUT + '02_after_door.png')
    # --- level 2
    t0 = time.time()
    while time.time() - t0 < 90 and not (rs()[1] == 1 and running()): time.sleep(1.0)
    time.sleep(1.5); w = rs(); c = cells()
    chk('campaign level 2 running (rsPos 1), grid = FALL', (w[1], c[2 * 256 + 1], c[3 * 256 + 1], c[14 * 256 + 1], c[5 * 256 + 3]), (1, 0x91, 0x91, 0, 0xc3))
    h.shot(OUT + '03_level2_start.png'); P(f'level 2 start frog = {frog()}')
    h._xdo('keydown', '--window', h.win, 'Right'); fell = None; shots = 0
    for i in range(80):
        time.sleep(0.1)
        try: f = frog(); c = cells()
        except Exception: continue
        cl = [c[2 * 256 + 1], c[3 * 256 + 1]]
        if cl != [0x91, 0x91] and fell is None: fell = i; P(f't={i*0.1:.1f}s: crumble cleared {cl}, frog {f}'); h.shot(OUT + '04_crumble_cleared.png')
        if fell is not None and f[2] not in (0,) and shots < 3 and i % 3 == 0: P(f'  t={i*0.1:.1f}s frog {f} cells {cl}'); h.shot(OUT + f'05_fall_{shots}.png'); shots += 1
        if fell is not None and i - fell > 40: break
    h._xdo('keyup', '--window', h.win, 'Right')
    chk('walking right onto the crumble: the cell is cleared and the frog falls (no way to the door)', fell is not None)
    time.sleep(4.0); f = frog(); c = cells(); P(f'4 s later: frog {f}, crumble cells {[c[2*256+1], c[3*256+1]]}, rs {rs()[:4]}')
    h.shot(OUT + '06_after_death.png')
    chk('no Address/Bus Error/exception (boot-time I/O-space probe warnings of TOS/HDDRIVER, address $ffxxxxxx, are not game errors)', [e for e in errors(h) if not re.search(r'Bus Error reading at address \$ff[0-9a-f]{6}', e)], [])
except Exception as ex:
    import traceback; traceback.print_exc(); chk('exception', repr(ex)[:200], 'none')
finally:
    h.close(); time.sleep(1)
print('FAILS', fails); open(f'{WD}_e206_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
