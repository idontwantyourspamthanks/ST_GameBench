"""Floppy cold boot + editor round trip (gate12): boot the floppy game disk, record every editor menu/list as it is (docs check), build a level with
conveyors / crumble / paired doors / exit / colours / enemies in the editor, Save to the campaign disk, zero the store, Load, Edit, Play, ride the conveyors.
usage: rt.py GAME.st WORKDIR CAMP.st [ste|st|megaste]   (env CPU16=1: hatari-option --cpuclock 16 after the title)"""
import sys; sys.path.insert(0, '/tmp/ng12fl/s')
from lib import *
import shutil, re, json
sys.path.insert(0, G + 'tools')
import nebcampaign as nc, ovl
GAME, WD, CAMP = sys.argv[1], sys.argv[2], sys.argv[3]; MACH = sys.argv[4] if len(sys.argv) > 4 else 'ste'
MEM = {'ste': 1024, 'st': 1024, 'megaste': 4096}[MACH]
V = 0x77cc0; RS = 0x77c80; GRID = 0x327f0
OUT = WD + '_out/'; shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
disk = OUT + 'camp.st'; shutil.copy(CAMP, disk); open(OUT + 'zero.ovl', 'wb').write(bytes(8192))
h = NebFloppy(GAME, machine=MACH, mem=MEM, workdir=WD, trace='fdc'); t = T(h)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def P(line): print(line, flush=True); LOG.append(line)
def menu():
    p = L(h, V + 4); d = grab(h, p, 900, 'menu'); n = d[0]; items = []; i = 1
    for _ in range(n):
        j = i + 2
        while d[j]: j += 1
        items.append((d[i], d[i + 1], d[i + 2:j].decode('latin1'))); i = j + 1
    return items, W(h, V + 8)
def names(): return [x[2] for x in menu()[0]]
def goto(idx):
    for _ in range(60):
        items, sel = menu()
        if sel == idx: return
        h.key('Down' if idx > sel else 'Up', hold=0.2); time.sleep(0.45)
    raise RuntimeError('goto')
def pick(what, gap=1.3):
    items, sel = menu(); idx = what if isinstance(what, int) else [i for i, x in enumerate(items) if x[2].startswith(what)][0]
    goto(idx); h.key('Control_R', hold=0.35); time.sleep(gap)
def fire(gap=1.2): h.key('Control_R', hold=0.35); time.sleep(gap)
def K(k, n=1, hold=0.12, gap=0.3):
    for _ in range(n): h.key(k, hold=hold); time.sleep(gap)
def at(c, r):
    cx, cy = W(h, RS + 20), W(h, RS + 22); dx = (c - cx) % 16
    K('Left', 16 - dx) if dx > 8 else K('Right', dx)
    K('Up', r - cy) if r > cy else K('Down', cy - r)
    assert (W(h, RS + 20), W(h, RS + 22)) == (c, r), ((W(h, RS + 20), W(h, RS + 22)), (c, r))
def col(c, r0, n): return list(grab(h, GRID + c * 256 + r0, n, 'col'))
def row(r, cols): g = grab(h, GRID, 0x1000, 'g'); return [g[c * 256 + r] for c in cols]
def gridnow(rows=48): g = grab(h, GRID, 0x1000, 'g'); return [list(g[c * 256:c * 256 + rows]) for c in range(16)]
def msgnow():
    p = L(h, V + 20); return grab(h, p, 24, 'm').split(b'\0')[0].decode('latin1') if p else ''
def flag_byte(): return grab(h, RS + 50, 1, 'fl')[0]
def wait_running(tmo=90):
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(0.7)
        if W(h, 0x33a20) == 0 and W(h, 0x33938) == 1: time.sleep(0.8); return True
    return False
def op(save=False):
    h.key('F10', hold=0.4); time.sleep(2.5); h.key('F10', hold=0.4); time.sleep(2.5)
    t.K('Down', 4 if save else 3, hold=0.2, gap=0.4); t.F(1.0); t.F(1.0); m = None
    for _ in range(60):
        time.sleep(0.5)
        try: busy = struct.unpack('>H', grab(h, V + 174, 2, 'vd'))[0]
        except Exception: continue
        if busy == 0:
            m = t.msg()
            if m is not None: break
    return m
def frog():
    d = grab(h, 0x33a16, 14, 'f'); x, y, _, dirn, an, st, spr = struct.unpack('>7H', d); return dict(x=x, y=y, st=st)
def key(k, down): h._xdo('keydown' if down else 'keyup', '--window', h.win, k)
def walk_to(k, cond, tmo=14):
    key(k, True); t0 = time.time(); f = frog()
    while time.time() - t0 < tmo and not cond(f): f = frog()
    key(k, False); return f
def trace_x(on):
    log = h.R / 'log.txt'
    if on:
        open(OUT + 'xt.ini', 'w').write('m $33a16 2\nm $338f2 2\n'); trace_x.n0 = os.path.getsize(log)
        h.debug(f'b ($33a16).w ! ($33a16).w :trace :file {OUT}xt.ini', 0.5); return None
    h.debug('b all', 0.6)
    txt = open(log, errors='replace').read()[trace_x.n0:]
    return [(int(a, 16) << 8 | int(b, 16), int(c, 16) << 8 | int(d, 16)) for a, b, c, d in re.findall(r'00033A16: (..) (..)[^\n]*\n> m \$338f2 2\n000338F2: (..) (..)', txt)]
def ride(tr, x0, step):
    xs = [x0] + [x for x, dx in tr]; free = [(a, b) for (a, b), (_, dx) in zip(zip(xs, xs[1:]), tr) if dx == 0]
    return (len(free), all((b - a) % 128 == step % 128 for a, b in free), free[0][0] if free else None, free[-1][1] if free else None)
def ensure_map():
    for _ in range(4):
        if W(h, V + 2) == 0: return True
        h.key('Left', hold=0.2); time.sleep(1.0)
    return W(h, V + 2) == 0
def lvl(label, gap=1.2):
    ensure_map(); fire(1.2); pick('Level >', 1.0); pick(label, gap)
DOC = {}
try:
    print('floppy title', bool(h.boot_to_title(timeout=500, space_at=25 if MEM > 1024 else 20)), flush=True); time.sleep(3)
    h.shot(OUT + '01_title.png')
    h.key('F10', hold=0.5); time.sleep(2.5)
    DOC['manager'] = names(); P('manager items: %r' % DOC['manager']); h.shot(OUT + '02_manager.png')
    pick('Levels'); P('levels list: %r' % names()); pick('<new level>', 1.5)
    h.shot(OUT + '03_editor_new.png'); chk('editor: new level starts with flags 0', flag_byte(), 0)
    g0 = gridnow(); P('new level: row1 = %r, rows %d' % ([g0[c][1] for c in range(16)], W(h, RS + 24)))
    fire(1.2); items, sel = menu(); DOC['cell'] = [(a, p, tx) for a, p, tx in items]; P('cell menu: %r' % DOC['cell']); h.shot(OUT + '04_cell_menu.png')
    pick('Enemy >', 1.0); DOC['enemy'] = menu()[0]; P('Enemy > : %r' % DOC['enemy']); h.shot(OUT + '05_enemy_menu.png')
    ensure_map(); fire(1.2); pick('Lift >', 1.0); DOC['lift'] = menu()[0]; P('Lift > : %r' % DOC['lift']); h.shot(OUT + '06_lift_menu.png')
    ensure_map(); fire(1.2); pick('Level >', 1.0); DOC['level'] = menu()[0]; P('Level > : %r' % DOC['level']); h.shot(OUT + '07_level_menu.png')
    pick('Colours >', 1.2); DOC['colours'] = names(); P('Colours > : %r' % DOC['colours']); h.shot(OUT + '08_colours.png')
    ensure_map(); lvl('Enemies >'); DOC['enemies'] = names(); P('Enemies > : %r' % DOC['enemies']); h.shot(OUT + '09_enemies.png')
    ensure_map(); lvl('Copy tower >'); DOC['copy'] = names(); P('Copy tower > : %r' % DOC['copy']); h.shot(OUT + '10_copy.png')
    P('after backing out of the lists: map view = %r' % ensure_map())
    # ---- Copy tower: first entry, then Blank grid (the blank tower has 48 rows)
    lvl('Copy tower >'); pick(0, 1.5); gc = gridnow(96); P('after Copy tower 1: flags %d, tower word %d' % (flag_byte(), W(h, RS + 14)))
    chk('Copy tower picks a shipped grid (differs from the blank ring)', [c[:48] for c in gc] != g0 and any(gc[c][5] for c in range(16)))
    h.shot(OUT + '11_after_copy.png'); ensure_map()
    lvl('Blank grid', 1.5)
    chk('Blank grid restores the blank ring (row 1 ledge ring)', row(1, range(16)), [0x81] * 16); g1 = gridnow()
    # ---- build the level
    for c in (1, 2, 3, 4, 5): at(c, 1); K('m')
    for c in (10, 11, 12, 13, 14): at(c, 1); K('n')
    at(7, 1); fire(1.2); pick('Crumble ledge', 1.2); at(8, 1); K('Return')
    ROW1 = [0x81, 0xb1, 0xb1, 0xb1, 0xb1, 0xb1, 0x81, 0x91, 0x91, 0x81, 0xa1, 0xa1, 0xa1, 0xa1, 0xa1, 0x81]
    chk('row 1: $b1 at 1-5 (key M), $91 at 7-8 (menu + Return), $a1 at 10-14 (key N)', row(1, range(16)), ROW1)
    at(3, 12); K('d'); chk('Door opening D at col 3 rows 12-14 also places the partner at col 11', (col(3, 12, 3), col(11, 12, 3)), ([0x83] * 3, [0x83] * 3))
    h.shot(OUT + '12_door.png'); P('status line after D: %r' % msgnow())
    at(5, 20); fire(1.2); pick('Door opening', 1.2); chk('menu Door opening at col 5 rows 20-22 -> partner col 13', (col(5, 20, 3), col(13, 20, 3)), ([0x83] * 3, [0x83] * 3))
    at(2, 30); K('x'); chk('Exit door X at col 2 rows 30-32, NO partner at col 10', (col(2, 30, 3), col(10, 30, 3)), ([0xc3] * 3, [0, 0, 0])); P('status line after X: %r' % msgnow()); h.shot(OUT + '13_exit.png')
    at(5, 6); fire(1.2); pick('Conveyor left', 1.2); at(6, 6); fire(1.2); pick('Conveyor right', 1.2)
    chk('menu Conveyor left at (5,6) = $a1, Conveyor right at (6,6) = $b1', (col(5, 6, 1), col(6, 6, 1)), ([0xa1], [0xb1]))
    # colours / enemies via the lists: colours 3 (tower byte 2), enemies 2 (flags low nibble 2)
    pick_at = None
    lvl('Colours >'); goto(2); fire(1.5)
    chk('Colours pick 3 -> tower byte 2, flags colour nibble 0', (W(h, RS + 14), flag_byte() >> 4), (2, 0))
    lvl('Enemies >'); goto(1); fire(1.5)
    chk('Enemies pick 2 -> flags low nibble 2', flag_byte(), 2); h.shot(OUT + '14_panel.png')
    lvl('Time +50', 1.0)
    G0 = gridnow(); h.shot(OUT + '15_level_ready.png')
    ensure_map(); h.key('F10', hold=0.4); time.sleep(1.5)                       # leave editor (commit)
    ram = t.store(); lv, _ = ovl.parse(ram); chk('store validates after Leave editor', ovl.validate(ram), [])
    chk('stored record: 1 level, flags 2, tower 2, grid == editor grid', (len(lv), lv[0]['flags'], lv[0]['tower'], lv[0]['grid'] == G0), (1, 2, 2, True))
    open(OUT + 'ram_store.ovl', 'wb').write(ram)
    t.insert(disk); m = op(save=True); chk('Save to campaign disk', m, 'Saved')
    t.insert(D + 'blank.st'); time.sleep(3)
    ok, text, data = nc.status(open(disk, 'rb').read()); chk('saved image usable', ok); open(OUT + 'saved.ovl', 'wb').write(data); chk('saved file == RAM store', data == ram)
    h.debug(f'loadbin {OUT}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
    t.insert(disk); m = op(); chk('Load from campaign disk', m, 'Loaded 1 levels / 0 campaigns')
    chk('reloaded store == saved file', t.store() == data)
    pick('Levels'); pick(0); pick('Edit', 1.5); chk('Edit after reload: grid == original editor grid, flags 2, tower 2', (gridnow() == G0, flag_byte(), W(h, RS + 14)), (True, 2, 2))
    h.key('F10', hold=0.4); time.sleep(1.5); pick(0); pick('Play', 1.0)
    chk('Play of the reloaded level: running', wait_running()); time.sleep(1.5); h.shot(OUT + '16_play.png')
    chk('play grid row 1 (RAM)', row(1, range(16)), ROW1)
    if W(h, 0x76c04) == 0: h.key('e', hold=0.2); time.sleep(0.5)
    trace_x(True); time.sleep(1.5); tr = trace_x(False); f0 = frog()
    chk('start: frog x 4 standing still without input', (f0['x'], tr), (4, []))
    trace_x(True); f1 = walk_to('Right', lambda f: f['x'] >= 9); time.sleep(3.5); tr = trace_x(False); f = frog()
    r = ride(tr, 4, 1); P(f'   conveyor right: changes without input {r[0]}, every +1: {r[1]}, x {r[2]} -> {r[3]}, final {f}')
    chk('$b1: carried right with no input, each change +1, to x 48, then stands', (r[0] >= 8, r[1], r[3], (f['x'], f['st'])), (True, True, 48, (48, 0)))
    trace_x(True); f2 = walk_to('Left', lambda f: 100 <= f['x'] <= 118, 25); time.sleep(4.0); tr = trace_x(False); f = frog()
    r = ride(tr, 48, -1); P(f'   conveyor left: changes without input {r[0]}, every -1: {r[1]}, x {r[2]} -> {r[3]}, final {f}')
    chk('$a1: carried left with no input, each change -1, to x 79, then stands', (r[0] >= 8, r[1], r[3], (f['x'], f['st'])), (True, True, 79, (79, 0)))
    chk('conveyor cells not consumed', row(1, range(16)), ROW1)
    key('Left', True); fell = None
    for i in range(60):
        time.sleep(0.1); r1 = row(1, (7, 8))
        if r1 != [0x91, 0x91]: fell = (i, r1, frog()); break
    key('Left', False); P(f'   crumble: walking Left from column 9: {fell}'); chk('crumble: the $91 cell (8,1) under the frog is cleared', fell is not None and fell[1][1] == 0)
    time.sleep(2.0); h.shot(OUT + '17_after_crumble.png'); P('frog after crumble: %r' % frog())
    json.dump({k: v for k, v in DOC.items()}, open(OUT + 'doc.json', 'w'), indent=1)
except Exception as ex:
    import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
finally:
    h.close(); time.sleep(1)
log = open(WD + '/log.txt', errors='replace').read() if os.path.exists(WD + '/log.txt') else ''
crash = re.findall(r'Address error|Illegal|double bus|CPU halted|bus error', log, re.I)
chk('no crash lines in the Hatari log', crash, [])
print('FAILS', fails); open(f'/tmp/ng12fl/out/rt_{MACH}{"_16" if os.environ.get("CPU16") else ""}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
