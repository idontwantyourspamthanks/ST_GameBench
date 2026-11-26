"""NebConveyor gate: the conveyor ledges $a1 (pushes the frog left) / $b1 (pushes right) can be placed in the editor and behave as the game defines them.
 1) cell menu: 'Conveyor left  N' / 'Conveyor right  M' after 'Crumble ledge' (15 items, 'Leave editor' still last); menu items and the keys N / M write $a1 / $b1;
    Return repeats; a conveyor over a door cell clears the partner door (the common `place` rule); C clears
 2) editor view: the tiles of $81 / $91 / $a1 / $b1 in the editor screen RAM (ES $A0000) == the `tiles` table of ed_editor.s (ids 2 / 3 / 19 / 20), all four different;
    the status-line name under the cursor == the menu item's own glyphs ('Conveyor left', 'Conveyor right', 'Crumble ledge', 'Ledge', 'Pillar')
 3) Level > Time +50, Leave editor (commit): the stored record parses, validates (ovl.validate == the in-game ov_check: magic kept) and holds the cells;
    Copy = same grid, Delete removes it; Edit loads the cells back
 0) two stored levels (plain ring / ring with conveyors in view) played from the manager: start screenshot crops equal (the game draws conveyors like ledges)
 4) playtest of the level built in the editor, with a Hatari change-watch on the frog x word: on a plain ledge no change; walked onto $b1 and released, x goes on
    +1 per step with joystick dx 0 to the end of the run; on $a1 -1 per step (direction per sub_03ab84: $20 -> -1, $30 -> +1); a $91 crumble cell still clears under the frog
usage: e208.py BUILD WORKDIR [ste|megaste|st] [--snap FILE]"""
import sys, os, time, struct, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
from PIL import Image, ImageChops
args = sys.argv[1:]
SNAP = None
if '--snap' in args: i = args.index('--snap'); SNAP = args[i + 1]; del args[i:i + 2]
BUILD, WD = args[0], args[1]; MACH = args[2] if len(args) > 2 else 'ste'
SNAP = SNAP or f'/tmp/nlcv/x/title_{MACH}_new.sav'; OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def P(line): print(line, flush=True); LOG.append(line)
SIGS = (b'Conveyor left  N', b'Conveyor right  M', b'Door + opposite', b'Crumble ledge', bytes.fromhex('10307e3010ffff0002080c7e0c08ffff0002'))   # the last = the two conveyor tiles of THIS build
if not os.path.exists(SNAP): print('snapshot boot', mk_snap(BUILD, SNAP, MACH, WD + '_snap'), flush=True)
snapdata = gzip.open(SNAP).read()
for sig in SIGS:                                                        # freshness guard (SNAP_EXPECT): the snapshot must hold THIS build's editor
    assert sig in snapdata, f'stale snapshot {SNAP}: {sig!r} missing'
    assert sig in open(f'{BUILD}/NEPATCH.BIN', 'rb').read(), f'the build under test has no {sig!r}'
del snapdata
GRID = 0x327f0; ES = 0xA0000
def cell(h, c, r): return grab(h, GRID + c * 256 + r, 1, 'c')[0]
def col(h, c, r0, n): return list(grab(h, GRID + c * 256 + r0, n, 'col'))
def row(h, r, cols): g = grab(h, GRID, 0x1000, 'g'); return [g[c * 256 + r] for c in cols]
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
def es(h): time.sleep(0.25); return grab(h, ES, 32000, 'es')
def glyph(E, c, line):
    """the 8 x 16 pixel text cell (4 planes) at text column c, 16-pixel line `line` (the editor's `txt` layout)"""
    b = line * 2560 + (c >> 1) * 8 + (c & 1)
    return bytes(E[b + r * 160 + 2 * p] for r in range(16) for p in range(4))
def glyphs(E, c, line, n): return [glyph(E, c + i, line) for i in range(n)]
def tile_px(E, c, ln):
    """the 16 x 8 pixel map cell at column c, screen line ln: 8 rows of 3 plane words"""
    b = ln * 1280 + c * 8
    return [struct.unpack('>3H', E[b + r * 160:b + r * 160 + 6]) for r in range(8)]
def tile_exp(tid):
    pat, colr = ovl.tiles()[tid]
    ex = [sum(((b >> (7 - i)) & 1) * (3 << (14 - 2 * i)) for i in range(8)) for b in pat]
    return [tuple(w if colr >> p & 1 else 0 for p in range(3)) for w in ex]
def enemies_off(h):
    if W(h, 0x76c04) == 0: h.key('e', hold=0.2); time.sleep(0.5)      # E trainer (persists between plays): the time-waster flyer cannot kill a standing frog
    return W(h, 0x76c04)
def frog(h):
    d = grab(h, 0x33a16, 14, 'f'); x, y, _, dirn, an, st, spr = struct.unpack('>7H', d); return dict(x=x, y=y, st=st)
def key(h, k, down): h._xdo('keydown' if down else 'keyup', '--window', h.win, k)
def walk_to(h, k, cond, tmo=14):
    """hold a direction key until cond(frog) -> the frog at release"""
    key(h, k, True); t0 = time.time(); f = frog(h)
    while time.time() - t0 < tmo and not cond(f): f = frog(h)
    key(h, k, False); return f
def trace_x(h, on):
    """Hatari change-watch on the frog x word $33a16: every change is logged with the joystick dx word $338f2 (0 = no horizontal input) -> [(x, dx)]"""
    log = h.R / 'log.txt'
    if on:
        open(OUT + 'xt.ini', 'w').write('m $33a16 2\nm $338f2 2\n'); trace_x.n0 = os.path.getsize(log)
        h.debug(f'b ($33a16).w ! ($33a16).w :trace :file {OUT}xt.ini', 0.5); return None
    h.debug('b all', 0.6)
    txt = open(log, errors='replace').read()[trace_x.n0:]
    return [(int(a, 16) << 8 | int(b, 16), int(c, 16) << 8 | int(d, 16)) for a, b, c, d in re.findall(r'00033A16: (..) (..)[^\n]*\n> m \$338f2 2\n000338F2: (..) (..)', txt)]
def ride(tr, x0, step):
    """the part of an x trace made without input (dx == 0): (number of changes, every change == step mod 128, first x, last x)"""
    xs = [x0] + [x for x, dx in tr]; free = [(a, b) for (a, b), (_, dx) in zip(zip(xs, xs[1:]), tr) if dx == 0]
    return (len(free), all((b - a) % 128 == step % 128 for a, b in free), free[0][0] if free else None, free[-1][1] if free else None)
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
def play(h, idx):
    pick(h, 'Levels'); pick(h, idx); pick(h, 'Play', 1.0)
    ok = wait_running(h, 90); time.sleep(1.0); return ok
def leave_to_manager(h):
    h.key('F10', hold=0.4); time.sleep(1.5); h.key('Left', hold=0.2); time.sleep(1.2)       # F10 = Leave editor (commit) -> Levels list; Left = '< back' -> main menu
BOX = (96, 110, 736, 290)
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2)
        # ---------- 0) in play a conveyor looks like a ledge: two stored levels, the plain ring and the same ring with $b1 at columns 1-3 and $a1 at 13-15 (all in view at the start)
        g = ring()
        for c in (1, 2, 3): g[c][1] = 0xb1
        for c in (13, 14, 15): g[c][1] = 0xa1
        data = ovl.build([ovl.level(1, 0, 48, ring(), time=0x0450, name='PLAIN'), ovl.level(1, 0, 48, g, time=0x0450, name='CONVLOOK')], [])
        assert not ovl.validate(data); open(OUT + 'look.ovl', 'wb').write(data)
        h.debug(f'loadbin {OUT}look.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('F10 opens the manager', open_manager(h))
        chk('play PLAIN', play(h, 0)); h.shot(OUT + '00_plain_play.png')
        h.key('q', hold=0.3); time.sleep(3.0); chk('open manager again', open_manager(h))
        chk('play CONVLOOK', play(h, 1)); h.shot(OUT + '00_conveyor_play.png')
        chk('CONVLOOK grid row 1 in RAM', row(h, 1, range(16)), [0x81, 0xb1, 0xb1, 0xb1] + [0x81] * 9 + [0xa1] * 3)
        dbb = ImageChops.difference(Image.open(OUT + '00_plain_play.png').convert('RGB').crop(BOX), Image.open(OUT + '00_conveyor_play.png').convert('RGB').crop(BOX)).getbbox()
        chk('start screenshot crop (sky, skyline, tower, ledge ring, frog) of CONVLOOK == PLAIN: the game draws a conveyor exactly like a ledge', dbb, None)
        h.key('q', hold=0.3); time.sleep(3.0); chk('open manager again', open_manager(h))
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        # ---------- 1) the cell menu and the keys
        h.key('Control_R', hold=0.35); time.sleep(1.2); items, sel = menu(h); EM = es(h); h.shot(OUT + '01_cell_menu.png')
        names = [t for a, p, t in items]
        chk('cell menu: 15 items, Conveyor left / right after Crumble ledge, Leave editor last',
            (len(items), names[2:5], items[3][:2], items[4][:2], names[-1]), (15, ['Crumble ledge', 'Conveyor left  N', 'Conveyor right  M'], (0, 0xa1), (0, 0xb1), 'Leave editor'))
        chk('cell menu: the 13 old items are unchanged and in the old order',
            names[:3] + names[5:], ['Empty  C', 'Ledge  L', 'Crumble ledge', 'Pillar  P', 'Blue block (shoot) B', 'Lift >', 'Door opening  D', 'Exit door  X', 'Enemy >', 'Level >', 'Playtest', 'Save to campaign disk', 'Leave editor'])
        mg = {t: glyphs(EM, 9, i, len(t)) for i, t in enumerate(names) if i < 12}          # the menu's own glyphs of each item text (column 9: after the cursor mark)
        h.key('F10', hold=0.3); time.sleep(0.8)                                              # close the menu (F10 in a menu = nothing; Left = last item = Leave) -> use the Empty item instead
        if W(h, V + 2) != 0:
            pick(h, 'Level >', 1.0); pick(h, '< back', 1.0)                                  # Level > back = map view, nothing placed
        chk('back in the map view', (W(h, V + 2), W(h, V + 30)), (0, 1))
        at(h, 5, 6); h.key('Control_R', hold=0.35); time.sleep(1.2); pick(h, 'Conveyor left', 1.2)
        chk('menu item Conveyor left at (5,6) writes $a1', cell(h, 5, 6), 0xa1)
        at(h, 6, 6); h.key('Control_R', hold=0.35); time.sleep(1.2); pick(h, 'Conveyor right', 1.2)
        chk('menu item Conveyor right at (6,6) writes $b1', cell(h, 6, 6), 0xb1)
        at(h, 7, 6); h.key('Control_R', hold=0.35); time.sleep(1.2); pick(h, 'Crumble ledge', 1.2)
        at(h, 8, 6); K(h, 'l'); at(h, 9, 6); K(h, 'p')
        chk('row 6 cols 5..9 = conveyor left, conveyor right, crumble, ledge, pillar', row(h, 6, range(5, 10)), [0xa1, 0xb1, 0x91, 0x81, 0x80])
        at(h, 5, 8); K(h, 'n'); at(h, 6, 8); K(h, 'm'); at(h, 7, 8); K(h, 'Return'); at(h, 8, 8); K(h, 'space')
        chk('keys: N at (5,8) = $a1, M at (6,8) = $b1, Return / Space repeat the last tile', row(h, 8, range(5, 9)), [0xa1, 0xb1, 0xb1, 0xb1])
        at(h, 8, 8); K(h, 'c'); at(h, 7, 8); K(h, 'Delete')
        chk('C / Delete clear a conveyor cell', row(h, 8, range(5, 9)), [0xa1, 0xb1, 0, 0])
        at(h, 3, 12); K(h, 'd')
        chk('door pair placed at columns 3 / 11 rows 12-14', (col(h, 3, 12, 3), col(h, 11, 12, 3)), ([0x83] * 3, [0x83] * 3))
        at(h, 3, 13); K(h, 'n'); at(h, 11, 14); K(h, 'm')
        chk('a conveyor over a door cell clears the partner door cell (same rule as every other tile)', (col(h, 3, 12, 3), col(h, 11, 12, 3)), ([0x83, 0xa1, 0], [0x83, 0, 0xb1]))
        # ---------- 2) what the editor shows
        top = W(h, RS + 24)
        at(h, 12, 6); E0 = es(h); h.shot(OUT + '02_map_tiles.png'); ln = top - 6
        px = {v: tile_px(E0, c, ln) for c, v in ((5, 0xa1), (6, 0xb1), (7, 0x91), (8, 0x81), (9, 0x80))}
        for v, tid, nm in ((0xa1, 19, 'conveyor left'), (0xb1, 20, 'conveyor right'), (0x91, 3, 'crumble'), (0x81, 2, 'ledge'), (0x80, 4, 'pillar')):
            chk(f'editor screen RAM: the ${v:02x} cell == tile {tid} of ed_editor.s ({nm})', px[v] == tile_exp(tid))
        chk('the four ledge kinds are four different pictures', len({repr(px[v]) for v in (0xa1, 0xb1, 0x91, 0x81)}), 4)
        P('   $a1 tile rows (plane 1 words): ' + ' '.join(f'{r[1]:016b}' for r in px[0xa1][:5]))
        P('   $b1 tile rows (plane 1 words): ' + ' '.join(f'{r[1]:016b}' for r in px[0xb1][:5]))
        for c, t in ((5, 'Conveyor left'), (6, 'Conveyor right'), (7, 'Crumble ledge'), (8, 'Ledge'), (9, 'Pillar')):
            at(h, c, 6); E1 = es(h)
            item = next(k for k in mg if k.startswith(t)); n = len(t)
            got = glyphs(E1, 0, 11, n + 1)
            chk(f'status line under the cursor on ${cell(h, c, 6):02x} shows "{t}" (the same glyphs as the menu item, then a blank)', (got[:n] == mg[item][:n], any(got[n])), (True, False))
            if c == 5: h.shot(OUT + '03_status_conveyor_left.png')
            if c == 6: h.shot(OUT + '04_status_conveyor_right.png')
        # ---------- 3) the level for the playtest; Time; commit; store; copy / delete / edit
        for c in (1, 2, 3, 4, 5): at(h, c, 1); K(h, 'm')
        for c in (10, 11, 12, 13, 14): at(h, c, 1); K(h, 'n')
        at(h, 7, 1); h.key('Control_R', hold=0.35); time.sleep(1.2); pick(h, 'Crumble ledge', 1.2); at(h, 8, 1); K(h, 'Return')
        ROW1 = [0x81, 0xb1, 0xb1, 0xb1, 0xb1, 0xb1, 0x81, 0x91, 0x91, 0x81, 0xa1, 0xa1, 0xa1, 0xa1, 0xa1, 0x81]
        chk('row 1: $b1 at columns 1-5, $91 at 7-8, $a1 at 10-14, plain ledge elsewhere', row(h, 1, range(16)), ROW1)
        t0 = W(h, RS + 18); level_menu(h, 'Time +50')
        chk('Level > Time +50: 450 -> 500 (BCD)', (t0, W(h, RS + 18)), (0x0450, 0x0500))
        G0 = grab(h, GRID, 0x1000, 'g'); h.shot(OUT + '05_level_ready.png')
        leave_to_manager(h)
        d, p = store(h); chk('Leave editor: the store validates (ovl.validate, the PC twin of ov_check)', ovl.validate(d), [])
        lv = p[0][-1]; gr = lv['grid']
        chk('stored record: time 0500, row 1 as built, conveyors at (5,6) (6,6) (5,8) (6,8) (3,13) (11,14)',
            (lv['time'], [gr[c][1] for c in range(16)], gr[5][6], gr[6][6], gr[5][8], gr[6][8], gr[3][13], gr[11][14]), (0x0500, ROW1, 0xa1, 0xb1, 0xa1, 0xb1, 0xa1, 0xb1))
        chk('stored grid == the editor grid', [[gr[c][r] for r in range(48)] for c in range(16)], [list(G0[c * 256:c * 256 + 48]) for c in range(16)])
        n0 = len(p[0]); poke(h, RS + 40, bytes([0, 0]))                                       # rsOk = 0: the game validates the store again at the next use
        pick(h, 'Levels'); items, _ = menu(h); pick(h, n0 - 1); pick(h, 'Copy', 1.2)
        d, p = store(h); chk('in-game validator (ov_check, re-run) keeps the magic; Copy made level n+1 with the same grid', (d[:4], len(p[0]), p[0][-1]['grid'] == p[0][-2]['grid']), (b'NCMP', n0 + 1, True))
        pick(h, n0); pick(h, 'Delete', 1.2)
        d, p = store(h); chk('Delete removed the copy; the store still validates', (len(p[0]), ovl.validate(d)), (n0, []))
        pick(h, n0 - 1); pick(h, 'Edit', 1.5)
        chk('Edit loads the conveyors back into the grid', grab(h, GRID, 0x1000, 'g') == G0)
        # ---------- 4) play
        h.key('Control_R', hold=0.35); time.sleep(1.0); pick(h, 'Playtest', 1.0)
        chk('playtest running', wait_running(h, 120)); time.sleep(1.0); h.shot(OUT + '06_conveyor_play.png')
        chk('playtest grid row 1 (RAM)', row(h, 1, range(16)), ROW1)
        chk('E trainer on (no enemies)', enemies_off(h) != 0)
        trace_x(h, True); time.sleep(1.5); tr = trace_x(h, False); f0 = frog(h)
        chk('at the start (plain ledge, column 0) the frog stands still without input: x 4, no x change in 1.5 s', (f0['x'], tr), (4, []))
        trace_x(h, True); f1 = walk_to(h, 'Right', lambda f: f['x'] >= 9); time.sleep(3.5); tr = trace_x(h, False); f = frog(h)     # x >= 8 = on the first $b1 cell (the sample lags the frog)
        P(f'   conveyor right: Right held until {f1}; every x change (x, joystick dx): {tr}')
        P(f'   changes without input: {ride(tr, 4, 1)[0]} (x {ride(tr, 4, 1)[2]} -> {ride(tr, 4, 1)[3]})')
        chk('on $b1 with NO input (dx 0) the frog is carried right: >= 8 changes, every one exactly +1, up to x 48 = the first pixel past the run (column 6), then it stands',
            (ride(tr, 4, 1)[0] >= 8, ride(tr, 4, 1)[1], ride(tr, 4, 1)[3], (f['x'], f['st'])), (True, True, 48, (48, 0)))
        h.shot(OUT + '07_after_conveyor_right.png')
        trace_x(h, True); f2 = walk_to(h, 'Left', lambda f: 100 <= f['x'] <= 118, 25); time.sleep(4.0); tr = trace_x(h, False); f = frog(h)
        P(f'   conveyor left: Left held (over the $b1 cells and round the tower) until {f2}; every x change (x, joystick dx): {tr}')
        chk('walking Left over the $b1 cells with input is a normal walk (every change with dx != 0 is -1)', all((b - a) % 128 == 127 for (a, b), (_, dx) in zip(zip([48] + [x for x, _ in tr], [x for x, _ in tr]), tr) if dx != 0))
        P(f'   changes without input: {ride(tr, 48, -1)[0]} (x {ride(tr, 48, -1)[2]} -> {ride(tr, 48, -1)[3]})')
        chk('on $a1 with NO input the frog is carried left: >= 8 changes, every one exactly -1, down to x 79 = the last pixel before the run (column 9), then it stands',
            (ride(tr, 48, -1)[0] >= 8, ride(tr, 48, -1)[1], ride(tr, 48, -1)[3], (f['x'], f['st'])), (True, True, 79, (79, 0)))
        h.shot(OUT + '08_after_conveyor_left.png')
        chk('the conveyor cells are still there after the rides (not consumed)', row(h, 1, range(16)), ROW1)
        key(h, 'Left', True); fell = None
        for i in range(60):
            time.sleep(0.1); r1 = row(h, 1, (7, 8))
            if r1 != [0x91, 0x91]: fell = (i, r1, frog(h)); break
        key(h, 'Left', False)
        P(f'   crumble: walking Left from column 9: {fell}')
        chk('crumble unaffected: the $91 cell (8,1) under the frog is cleared', fell is not None and fell[1][1] == 0)
        chk('no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e208_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
