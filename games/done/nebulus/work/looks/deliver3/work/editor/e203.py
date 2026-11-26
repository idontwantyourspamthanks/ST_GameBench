"""NebDoors gate: a Door opening is always placed with its opposite (column + 8 mod 16, same rows) and deleted with it; the Exit door is the goal and is not paired.
 1) old file with unpaired doors: loads as before (grid == record), editing a lone door does not touch the cell 8 columns away unless that is a door
 2) new level: D key / Door opening menu item put 3 cells + 3 opposite cells (incl. the wrap 14 -> 6, 12 -> 4); status "Door + opposite"; clear / overwrite one door cell clears its partner; Exit door X = 3 cells, no partner, status "Exit (finish)"
 3) playtest of a level made in the editor: frog walks into the door at column 0 and comes out at column 8 (x + 64, same row) where the opposite door is; walks to an exit door and finishes -> back in the editor
 4) an ORIGINAL tower (campaign entry original M1 T1): the door at column 2 still works (x + 64 -> column 10)
usage: e203.py BUILD WORKDIR [ste|megaste|st] [--snap FILE]"""
import sys, os, time, struct, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/tmp/nld/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
args = sys.argv[1:]
SNAP = None
if '--snap' in args: i = args.index('--snap'); SNAP = args[i + 1]; del args[i:i + 2]
BUILD, WD = args[0], args[1]; MACH = args[2] if len(args) > 2 else 'ste'
SNAP = SNAP or f'/tmp/nld/x/title_{MACH}_new.sav'; OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def P(line): print(line, flush=True); LOG.append(line)
if not os.path.exists(SNAP): print('snapshot boot', mk_snap(BUILD, SNAP, MACH, WD + '_snap'), flush=True)
snapdata = gzip.open(SNAP).read()
for sig in (b'Door + opposite', b'Exit (finish)', b'Crumble ledge'):      # freshness guard (SNAP_EXPECT): the snapshot must hold THIS build's editor
    assert sig in snapdata, f'stale snapshot {SNAP}: {sig!r} missing'
assert open(f'{BUILD}/NEPATCH.BIN', 'rb').read().find(b'Door + opposite') > 0, 'the build under test has no paired-door editor'
# ---- the old file: a level with a lone door (3,2-4) + a ledge at its opposite (11,3), and a proper pair (6,10-12)+(14,10-12); the original tower 1 as a campaign
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
g = ring()
for r in (2, 3, 4): g[3][r] = 0x83
g[11][3] = 0x81
for r in (10, 11, 12): g[6][r] = 0x83; g[14][r] = 0x83
OLD = g
data = ovl.build([ovl.level(1, 0, 48, OLD, time=0x0450, name='LONE')], [ovl.camp('ORIG', [ovl.orig(1, 0)])])
assert not ovl.validate(data); open(OUT + 'special.ovl', 'wb').write(data)
GRID = 0x327f0
def cell(h, c, r): return grab(h, GRID + c * 256 + r, 1, 'c')[0]
def col(h, c, r0, n): return list(grab(h, GRID + c * 256 + r0, n, 'col'))
def grid(h): return grab(h, GRID, 0x1000, 'g')
def msg(h):
    p = L(h, V + 20)
    return grab(h, p, 24, 'm').split(b'\0')[0].decode('latin1') if p else ''
def K(h, k, n=1, hold=0.12, gap=0.3):
    for _ in range(n): h.key(k, hold=hold); time.sleep(gap)
def at(h, c, r):
    cx, cy = W(h, RS + 20), W(h, RS + 22)
    dx = (c - cx) % 16
    K(h, 'Left', 16 - dx) if dx > 8 else K(h, 'Right', dx)
    K(h, 'Up', r - cy) if r > cy else K(h, 'Down', cy - r)
    assert (W(h, RS + 20), W(h, RS + 22)) == (c, r), ((W(h, RS + 20), W(h, RS + 22)), (c, r))
def enemies_off(h):
    if W(h, 0x76c04) == 0: h.key('e', hold=0.2); time.sleep(0.5)      # E trainer (persists between plays): no enemies, so the time-waster flyer cannot kill a standing frog
    return W(h, 0x76c04)
def frog(h):
    d = grab(h, 0x33a16, 14, 'f'); x, y, _, dirn, an, st, spr = struct.unpack('>7H', d); return dict(x=x, y=y, st=st, anim=an)
def key(h, k, down): h._xdo('keydown' if down else 'keyup', '--window', h.win, k)
def tap(h, k, t): key(h, k, True); time.sleep(t); key(h, k, False)
def wait_st(h, st, tmo=8):
    t0 = time.time(); f = frog(h)
    while time.time() - t0 < tmo:
        f = frog(h)
        if f['st'] == st: return f
    return f
def tunnel(h, name):
    """Up in a door: returns (x before, x centred+..., x after, y before, y after)"""
    f0 = frog(h); tap(h, 'Up', 0.15); f1 = wait_st(h, 4, 3)
    t0 = time.time(); f2 = frog(h)
    while time.time() - t0 < 9:
        time.sleep(0.4); f2 = frog(h)
        if f2['st'] == 0 and time.time() - t0 > 1.0: break
    P(f'   {name}: before {f0}, tunnel state seen {f1["st"]} (x {f1["x"]}), after {f2}  => column {f0["x"] >> 3} -> {f2["x"] >> 3}, x {f0["x"]} -> {f2["x"]} (+{(f2["x"] - f0["x"]) % 128}), y {f0["y"]} -> {f2["y"]}')
    return f0, f1, f2
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2); h.debug(f'loadbin {OUT}special.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('F10 opens the manager', open_manager(h))
        # ---------- 1) the old file with unpaired doors
        pick(h, 'Levels'); pick(h, 'LONE'); pick(h, 'Edit', 1.5)
        gr = grid(h)
        chk('old file: the editor loads LONE, grid == the record (lone door, ledge at its opposite, a pair)', [[gr[a * 256 + r] for r in range(48)] for a in range(16)], OLD)
        at(h, 3, 3); K(h, 'c')
        chk('clearing a cell of a LONE door leaves the cell 8 columns away alone (a ledge, not a door)', (col(h, 3, 2, 3), col(h, 11, 2, 3)), ([0x83, 0, 0x83], [0, 0x81, 0]))
        at(h, 6, 11); K(h, 'c')
        chk('clearing one cell of a PAIR clears its partner, the other cells stay', (col(h, 6, 10, 3), col(h, 14, 10, 3)), ([0x83, 0, 0x83], [0x83, 0, 0x83]))
        at(h, 14, 10); K(h, 'l')
        chk('overwriting a door cell with a ledge clears the partner (6,10); the ledge is placed', (cell(h, 14, 10), cell(h, 6, 10), cell(h, 6, 12), cell(h, 14, 12)), (0x81, 0, 0x83, 0x83))
        at(h, 3, 3); K(h, 'd')
        chk('Door at (3,3): rows 3-5 and the opposite column 11 rows 3-5 (the ledge at (11,3) is replaced, lone door cells (3,2) kept)', (col(h, 3, 2, 4), col(h, 11, 2, 4)), ([0x83] * 4, [0, 0x83, 0x83, 0x83]))
        h.shot(OUT + '01_old_file_edit.png')
        h.key('F10', hold=0.4); time.sleep(1.5)
        h.key('Left', hold=0.2); time.sleep(1.2)
        # ---------- 2) a new level
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        gr = grid(h); chk('new level: ring on row 1, no door yet', ([gr[a * 256 + 1] for a in range(16)], [v for v in gr if v & 0x83 == 0x83 and v != 0xc3]), ([0x81] * 16, []))
        at(h, 3, 6); K(h, 'd')
        chk('D at (3,6): door rows 6-8 in column 3 AND column 11', (col(h, 3, 5, 5), col(h, 11, 5, 5)), ([0, 0x83, 0x83, 0x83, 0], [0, 0x83, 0x83, 0x83, 0]))
        chk('status line says "Door + opposite"', msg(h), 'Door + opposite'); h.shot(OUT + '02_door_placed.png')
        at(h, 14, 10); h.key('Control_R', hold=0.35); time.sleep(1.5); pick(h, 'Door opening', 1.2)
        chk('menu item Door opening at (14,10): column 14 and its opposite column 6 (wrap), rows 10-12', (col(h, 14, 9, 5), col(h, 6, 9, 5)), ([0, 0x83, 0x83, 0x83, 0], [0, 0x83, 0x83, 0x83, 0]))
        chk('menu route status "Door + opposite"', msg(h), 'Door + opposite'); h.shot(OUT + '03_door_menu.png')
        at(h, 12, 16); K(h, 'd')
        chk('Door at column 12: opposite is column 4 (rows 16-18)', (col(h, 12, 16, 3), col(h, 4, 16, 3)), ([0x83] * 3, [0x83] * 3))
        at(h, 11, 7); K(h, 'c')
        chk('Delete (11,7): the partner (3,7) goes too, the other four cells stay', (col(h, 3, 6, 3), col(h, 11, 6, 3)), ([0x83, 0, 0x83], [0x83, 0, 0x83]))
        at(h, 3, 6); K(h, 'l')
        chk('Ledge over (3,6): partner (11,6) cleared', (cell(h, 3, 6), cell(h, 11, 6), cell(h, 11, 8), cell(h, 3, 8)), (0x81, 0, 0x83, 0x83))
        at(h, 4, 24); K(h, 'x')
        chk('Exit door X at (4,24): 3 cells, NO partner at column 12', (col(h, 4, 23, 5), col(h, 12, 23, 5)), ([0, 0xc3, 0xc3, 0xc3, 0], [0] * 5))
        chk('status line says "Exit (finish)"', msg(h), 'Exit (finish)'); h.shot(OUT + '04_exit_placed.png')
        at(h, 3, 8); K(h, 'x')
        chk('Exit door over the door cell (3,8): the exit is placed, the old partner (11,8) is cleared', (cell(h, 3, 8), cell(h, 11, 8), cell(h, 11, 9)), (0xc3, 0, 0))
        rows = W(h, RS + 16)
        at(h, 7, rows - 2); K(h, 'd')
        chk('Door at the top (rows-2): clipped to 2 cells, the opposite too', (col(h, 7, rows - 3, 3), col(h, 15, rows - 3, 3)), ([0, 0x83, 0x83], [0, 0x83, 0x83]))
        P(f'   cells(7,{rows-1}), (15,{rows-1}) = {cell(h, 7, rows - 1):#x}, {cell(h, 15, rows - 1):#x}')
        h.key('F10', hold=0.4); time.sleep(1.5); h.key('Left', hold=0.2); time.sleep(1.2)
        # ---------- 3) playtest of a level made in the editor: door at column 0, exit door at column 9, the frog tunnels to column 8 and walks into the exit
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        at(h, 0, 2); K(h, 'd'); at(h, 9, 2); K(h, 'x')
        chk('editor level: doors (0,2-4)+(8,2-4), exit (9,2-4), no door at column 1', (col(h, 0, 2, 3), col(h, 8, 2, 3), col(h, 9, 2, 3), col(h, 1, 2, 3)), ([0x83] * 3, [0x83] * 3, [0xc3] * 3, [0] * 3))
        h.key('Control_R', hold=0.35); time.sleep(1.0); pick(h, 'Playtest', 1.0)
        chk('playtest running', wait_running(h, 120)); chk('E trainer on (no enemies)', enemies_off(h) != 0)
        chk('playtest grid has the pair (RAM)', (col(h, 0, 2, 3), col(h, 8, 2, 3)), ([0x83] * 3, [0x83] * 3)); h.shot(OUT + '05_playtest_start.png')
        f0, f1, f2 = tunnel(h, 'door at column 0')
        chk('the frog was in the tunnel state', f1['st'], 4)
        chk('comes out 8 columns away: x + 64, column 8, same y, standing (state 0) in the opposite door', (f2['x'], f2['x'] >> 3, f2['y'], f2['st'], cell(h, f2['x'] >> 3, f2['y'] >> 2)), (68, 8, f0['y'], 0, 0x83))
        h.shot(OUT + '06_arrived_col8.png')
        for _ in range(30):
            f = frog(h)
            if f['x'] >= 74: break
            tap(h, 'Right', 0.1)
        P(f'   walked right onto the exit door: {frog(h)}')
        tap(h, 'Up', 0.15)
        done = False
        for _ in range(60):
            time.sleep(0.7)
            if W(h, RS + 8) == 0 and W(h, RS + 6) == 1: done = True; break
        chk('Up in the exit door finishes the playtest: back in the editor (rsTest 0, rsEd 1)', done); h.shot(OUT + '07_back_in_editor.png')
        h.key('F10', hold=0.4); time.sleep(1.5); h.key('Left', hold=0.2); time.sleep(1.2)
        # ---------- 4) an ORIGINAL tower: campaign ORIG = original M1 T1; its door at column 2 pairs with column 10
        pick(h, 'Campaigns'); pick(h, 'ORIG'); pick(h, 'Play', 1.0)
        chk('original tower 1 running', wait_running(h, 120)); chk('E trainer on (no enemies)', enemies_off(h) != 0)
        chk('rsLvl 0 = original tower; doors (2,2-4),(10,2-4) in RAM', (W(h, RS + 4), col(h, 2, 2, 3), col(h, 10, 2, 3)), (0, [0x83] * 3, [0x83] * 3))
        for _ in range(40):
            f = frog(h)
            if 17 <= f['x'] <= 22: break
            tap(h, 'Right', 0.08)
        time.sleep(0.5); f = frog(h); P(f'   walked to {f}')
        f0, f1, f2 = tunnel(h, 'original tower 1 door at column 2')
        chk('original door: tunnel, comes out at column 10 (x + 64 after centring on the column), same y', (f1['st'], f0['x'] >> 3, f2['x'] >> 3, f2['y'], f2['st'] in (0,)), (4, 2, 10, f0['y'], True))
        h.shot(OUT + '08_original_tower.png')
        chk('no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e203_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
