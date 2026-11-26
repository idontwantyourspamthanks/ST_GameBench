"""NebConveyor A/B equivalence gate for the code-size pass of ed_editor.s: the SAME scripted editor session is run on the build before the pass (deliver2+3 = gate2
merge) and on the new build; at every checkpoint the editor screen RAM (ES $A0000, 32000 B = every pixel the editor draws: menus, lists, map tiles, panel, cell
names, status messages), the editor palette (EPAL), the working grid, the campaign store, the runtime state RS and the menu / message text are dumped and must be
byte-identical.  The session never opens the cell menu at a checkpoint (it has two more items by design) and places no conveyor.
  e208_ab.py run BUILD SNAP OUTDIR [ste|megaste|st]     (SNAP is made from BUILD when missing; freshness-checked with SIG)
  e208_ab.py cmp OUTDIR_A OUTDIR_B
env SIG = hex bytes the snapshot and the build must contain, NOSIG = hex bytes they must NOT contain"""
import sys, os, time, struct, gzip, shutil, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
if sys.argv[1] == 'cmp':
    A, B = sys.argv[2], sys.argv[3]
    la, lb = json.load(open(A + '/index.json')), json.load(open(B + '/index.json'))
    bad = 0
    print(f'checkpoints: {len(la)} / {len(lb)}')
    if [x['name'] for x in la] != [x['name'] for x in lb]: print('FAIL checkpoint lists differ'); bad += 1
    tot = {}
    for xa, xb in zip(la, lb):
        diffs = []
        for part in ('es', 'pal', 'grid', 'ovs', 'rs'):
            da, db = open(f"{A}/{xa['file']}.{part}", 'rb').read(), open(f"{B}/{xb['file']}.{part}", 'rb').read()
            tot[part] = tot.get(part, 0) + len(da)
            if da != db:
                n = sum(1 for p, q in zip(da, db) if p != q); first = next(i for i, (p, q) in enumerate(zip(da, db)) if p != q)
                diffs.append(f'{part}: {n} bytes differ, first at +{first:#x}')
        for k in ('menu', 'sel', 'mtop', 'vars', 'msg'):
            if xa[k] != xb[k]: diffs.append(f'{k}: {xa[k]!r} != {xb[k]!r}')
        print(('FAIL' if diffs else 'same'), xa['file'], xa['name'], '; '.join(diffs)); bad += bool(diffs)
    print('bytes compared per part:', tot)
    print(f'RESULT: {len(la) - bad} of {len(la)} checkpoints identical, {bad} differ')
    sys.exit(1 if bad else 0)
from ulib_ui import *
import ovl
BUILD, SNAP, OUT = sys.argv[2], sys.argv[3], sys.argv[4].rstrip('/') + '/'; MACH = sys.argv[5] if len(sys.argv) > 5 else 'ste'
os.makedirs(OUT, exist_ok=True); WD = OUT.rstrip('/') + '_wd'
if not os.path.exists(SNAP): print('snapshot boot', mk_snap(BUILD, SNAP, MACH, WD + '_snap'), flush=True)
snapdata = gzip.open(SNAP).read(); nep = open(f'{BUILD}/NEPATCH.BIN', 'rb').read()
for s in filter(None, os.environ.get('SIG', '').split(',')): assert bytes.fromhex(s) in snapdata and bytes.fromhex(s) in nep, f'stale snapshot / wrong build: {s}'
for s in filter(None, os.environ.get('NOSIG', '').split(',')): assert bytes.fromhex(s) not in snapdata and bytes.fromhex(s) not in nep, f'wrong snapshot / build: has {s}'
del snapdata, nep
GRID = 0x327f0; ES = 0xA0000; IDX = []
def K(h, k, n=1, hold=0.12, gap=0.3):
    for _ in range(n): h.key(k, hold=hold); time.sleep(gap)
def at(h, c, r):
    cx, cy = W(h, RS + 20), W(h, RS + 22)
    dx = (c - cx) % 16
    K(h, 'Left', 16 - dx) if dx > 8 else K(h, 'Right', dx)
    K(h, 'Up', r - cy) if r > cy else K(h, 'Down', cy - r)
    assert (W(h, RS + 20), W(h, RS + 22)) == (c, r), ((W(h, RS + 20), W(h, RS + 22)), (c, r))
def fire(h, gap=1.2): h.key('Control_R', hold=0.35); time.sleep(gap)
def cp(h, name):
    time.sleep(0.5)
    f = f'{len(IDX):03d}'
    v = grab(h, V, 256, 'v'); mode, scr = struct.unpack('>H', v[2:4])[0], struct.unpack('>H', v[30:32])[0]
    items, sel = (menu(h) if mode == 1 else ([], 0))
    mp = struct.unpack('>L', v[20:24])[0]
    msg = grab(h, mp, 48, 'm').split(b'\0')[0].decode('latin1') if mp else ''
    for part, a, n in (('es', ES, 32000), ('pal', 0xA8980, 32), ('grid', GRID, 0x1000), ('ovs', 0xBC000, 0x2000), ('rs', RS, 52)):
        open(OUT + f + '.' + part, 'wb').write(grab(h, a, n, part))
    vars_ = dict(mode=mode, scr=scr, mcol=struct.unpack('>H', v[168:170])[0], lift=struct.unpack('>H', v[172:174])[0], disk=struct.unpack('>H', v[174:176])[0], npos=struct.unpack('>H', v[156:158])[0])
    IDX.append(dict(file=f, name=name, menu=[list(x) for x in items], sel=sel, mtop=struct.unpack('>H', v[10:12])[0], vars=vars_, msg=msg))
    print(f, name, '|', msg, '|', [t for _, _, t in items][:4], flush=True)
def cycle_custom(h, idx):
    """Change source on entry idx until it shows a custom level ('nn L name'); the number of presses is the same on both builds (same store)"""
    for n in range(20):
        items, _ = menu(h)
        if items[idx][2][3:4] == 'L': return n
        pick(h, idx); pick(h, 'Change source', 0.9)
    raise RuntimeError('no custom entry')
def cellmenu(h, *labels, gap=1.2):
    fire(h)
    for l in labels: pick(h, l, gap)
def wait_disk(h):
    for _ in range(80):
        time.sleep(0.5)
        if W(h, V + 174) == 0: break
    time.sleep(0.5)
def dense():
    g = [[0x81] * 120 for _ in range(16)]
    for r in (117, 118, 119): g[4][r] = 0xc3
    return g
def tail(h):
    """part 2 (from the manager's main menu): a full store (copy refused, a 120-row level edited and committed smaller), the in-game validator, back to the title"""
    data = ovl.build([ovl.level(1, 2, 120, dense(), time=0x0300, name=f'DENSE{i}') for i in range(3)], [ovl.camp('FULL', [0, 1, 2])])
    assert not ovl.validate(data); open(OUT + 'full.ovl', 'wb').write(data)
    h.debug(f'loadbin {OUT}full.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
    pick(h, 'Levels'); cp(h, 'full store: levels list'); pick(h, 1); pick(h, 'Copy'); cp(h, 'copy: Overlay full (the level menu stays)')
    pick(h, 'Edit', 1.5); cp(h, 'dense level in the editor'); at(h, 3, 60); cp(h, 'dense level scrolled'); at(h, 3, 119); cp(h, 'dense level top')
    K(h, 'c'); cellmenu(h, 'Leave editor'); cp(h, 'dense level committed (smaller)')
    pick(h, '< back'); pick(h, 'Campaigns'); pick(h, 0); pick(h, 'Edit entries'); cp(h, 'FULL entries')
    pick(h, '< back'); pick(h, '< back')
    # the in-game validator (ov_check: its reject branches were re-laid out by the size pass): 13 bad stores + the good one.  The store is validated once, when the manager
    # opens (ed_run -> ov_ok), so each file is loaded on the TITLE with rsOk = 0 and the manager opened on it (a store swapped under an open manager is not a real case:
    # the list code trusts the count it has just read; the first version of this cell did that and both builds listed garbage names identically).
    good = bytearray(data); parity = []
    for nm, off, val in (('good', 0, b'N'), ('version 2', 5, b'\x02'), ('nlevels 200', 7, b'\xc8'), ('ncamps 9', 9, b'\x09'), ('campaign count 17', 28, b'\x11'), ('mission 3', 272, b'\x03'), ('mission 0', 272, b'\x00'),
                         ('tower 8', 273, b'\x08'), ('rows 15', 274, b'\x0f'), ('rows 121', 274, b'\x79'), ('len < 2*rows', 276, b'\x00\x64'), ('len 65535', 276, b'\xff\xff'), ('mask bit flipped', 292, bytes([good[292] ^ 1])),
                         ('nlevels 4 (4th record missing)', 7, b'\x04')):
        bad = bytearray(good); bad[off:off + len(val)] = val; open(OUT + 'fz.ovl', 'wb').write(bad)
        h.key('F10', hold=0.4)
        for _ in range(40):
            time.sleep(0.5)
            if L(h, 0x70) == 0x382d8: break
        time.sleep(1.0); h.debug(f'loadbin {OUT}fz.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        assert open_manager(h); magic = grab(h, 0xBC000, 4, 'mg')
        pick(h, 'Levels'); cp(h, 'validator: ' + nm); pick(h, '< back')
        parity.append((nm, magic == b'NCMP', not ovl.validate(bytes(bad)))); print('  validator', parity[-1], flush=True)
    IDX.append(dict(file=IDX[-1]['file'], name='validator parity with ovl.validate (name, game keeps the magic, ovl.py accepts)', menu=[], sel=0, mtop=0, vars={}, msg=repr(parity)))
    print('PARITY', 'ok' if all(a == b for _, a, b in parity) else 'FAIL', flush=True)
    pick(h, 'Original game', 2.0)
    IDX.append(dict(file=f'{len(IDX):03d}', name='Original game: back on the title', menu=[], sel=0, mtop=0, vars=dict(vbl=L(h, 0x70)), msg=''))
    for part, a, n in (('es', 0x33910, 2), ('pal', 0x3390c, 2), ('grid', GRID, 0x1000), ('ovs', 0xBC000, 0x2000), ('rs', RS, 52)):
        open(OUT + IDX[-1]['file'] + '.' + part, 'wb').write(grab(h, a, n, part))
    print('title vbl', hex(L(h, 0x70)), 'errors', errors(h), flush=True)
    IDX.append(dict(file=IDX[-1]['file'], name='Hatari log error lines', menu=[], sel=0, mtop=0, vars={}, msg=repr(errors(h))))
def run():
    kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **kw)
    try:
        time.sleep(2)
        assert open_manager(h); cp(h, 'manager main menu')
        if os.environ.get('PART') == '2': tail(h); return
        pick(h, 'Levels'); cp(h, 'levels list (empty)')
        pick(h, '<new level>', 1.5); cp(h, 'new level map')
        # every tile by its key on row 10 (the panel shows the cell name and value under the cursor)
        for c, k in enumerate('lpbsrwuijk', 1):
            at(h, c, 10); K(h, k); cp(h, f'key {k} at ({c},10)')
        at(h, 4, 10); K(h, 's'); cp(h, 'key s again on the stone ball (turn round)')
        at(h, 9, 10); K(h, 'j'); cp(h, 'key j again on the eye (turn round)')
        at(h, 12, 10); K(h, 'x'); cp(h, 'key x exit door')
        at(h, 13, 14); K(h, 'd'); cp(h, 'key d door + opposite')
        at(h, 5, 15); cp(h, 'cursor on the opposite door')
        at(h, 1, 12); cellmenu(h, 'Enemy >', 'Stone ball'); cp(h, 'menu: enemy direction (horizontal)')
        pick(h, 'Start left'); cp(h, 'menu: stone ball start left')
        at(h, 2, 12); cellmenu(h, 'Enemy >', 'Red ball waits'); cp(h, 'menu: red ball waits (no direction)')
        at(h, 3, 12); cellmenu(h, 'Enemy >', 'Eye up/down slow'); cp(h, 'menu: enemy direction (vertical)')
        pick(h, 'Start down'); cp(h, 'menu: eye start down')
        at(h, 4, 12); cellmenu(h, 'Enemy >', 'Eye l/r fast', 'Start right'); cp(h, 'menu: eye l/r fast start right')
        at(h, 5, 12); cellmenu(h, 'Enemy >', '< back'); cp(h, 'menu: enemy back')
        at(h, 1, 14); cellmenu(h, 'Pillar'); cp(h, 'menu: pillar')
        at(h, 2, 14); cellmenu(h, 'Crumble ledge'); cp(h, 'menu: crumble ledge')
        at(h, 3, 14); K(h, 'Return'); cp(h, 'Return repeats the crumble ledge')
        at(h, 4, 14); K(h, 'space'); cp(h, 'Space repeats')
        at(h, 8, 20); cellmenu(h, 'Exit door'); cp(h, 'menu: exit door')
        at(h, 2, 20); cellmenu(h, 'Door opening'); cp(h, 'menu: door opening')
        at(h, 9, 20); K(h, 'Return'); cp(h, 'Return repeats the door (3 cells + opposite)')
        at(h, 10, 21); K(h, 'l'); cp(h, 'ledge over a door cell clears the partner')
        at(h, 1, 10); K(h, 'c'); at(h, 2, 10); K(h, 'Delete'); cp(h, 'c / Delete clear')
        at(h, 0, 2); cp(h, 'cursor on the frog start'); at(h, 0, 0); cp(h, 'cursor bottom row'); at(h, 15, 47); cp(h, 'cursor top row (scrolled)'); at(h, 15, 30); cp(h, 'scrolled back')
        for k in 'qyfghovte': K(h, k)
        cp(h, 'unmapped letters do nothing')
        # lifts
        at(h, 6, 2); K(h, 'a'); cp(h, 'lift: from here (pick mode)')
        K(h, 'Left'); K(h, 'Right'); K(h, 'l'); cp(h, 'lift pick: left/right/letters ignored')
        K(h, 'Return'); cp(h, 'lift pick: same row = Pick another row')
        K(h, 'Up', 4); cp(h, 'lift pick: cursor up 4')
        K(h, 'Return'); cp(h, 'lift set (end above)')
        at(h, 6, 4); K(h, 'z'); cp(h, 'lift stop'); at(h, 6, 6); cp(h, 'cursor on the lift end'); at(h, 6, 2); cp(h, 'cursor on the lift start')
        at(h, 7, 4); K(h, 'p'); at(h, 7, 2); K(h, 'a'); K(h, 'Up', 4); fire(h); cp(h, 'lift set by FIRE through a pillar: warning')
        at(h, 8, 2); K(h, 'a'); h.key('F10', hold=0.3); time.sleep(1.0); cp(h, 'lift pick cancelled by F10')
        cellmenu(h, 'Lift >'); cp(h, 'menu: Lift >'); pick(h, 'Lift: delete'); cp(h, 'menu: lift delete')
        at(h, 9, 8); cellmenu(h, 'Lift >', 'Lift: from here'); K(h, 'Down', 3); K(h, 'space'); cp(h, 'lift set (end below, by Space)')
        at(h, 9, 6); cellmenu(h, 'Lift >', 'Lift: stop here'); cp(h, 'menu: lift stop here')
        at(h, 6, 3); cellmenu(h, 'Lift >', 'Lift: delete'); cp(h, 'menu: lift delete from the shaft')
        # Level >
        cellmenu(h, 'Level >'); cp(h, 'menu: Level >')
        pick(h, 'Colours'); cp(h, 'colour list'); K(h, 'Down', 2); cp(h, 'colour list preview +2'); K(h, 'Up', 1); cp(h, 'colour list preview -1')
        pick(h, 4); cp(h, 'colours 5 picked (map)')
        cellmenu(h, 'Level >', 'Enemies'); cp(h, 'enemy list'); pick(h, 2); cp(h, 'enemies 3 picked')
        cellmenu(h, 'Level >', 'Colours'); cp(h, 'colour list reopened on the current'); K(h, 'Left'); time.sleep(0.8); cp(h, 'colour list: left = back')
        cellmenu(h, 'Level >', 'Time +50'); cellmenu(h, 'Level >', 'Time +50'); cp(h, 'time +50 twice'); cellmenu(h, 'Level >', 'Time -50'); cp(h, 'time -50')
        cellmenu(h, 'Level >', 'Name'); cp(h, 'name entry')
        K(h, 'Up', 2); K(h, 'Right'); K(h, 'Down'); K(h, 'Right', 2); K(h, 'Up'); K(h, 'Left'); cp(h, 'name entry edited'); fire(h); cp(h, 'name entry done (map)')
        cellmenu(h, 'Level >', '< back'); cp(h, 'Level > back')
        h.key('F10', hold=0.4); time.sleep(1.5); cp(h, 'F10 = leave editor: levels list')
        pick(h, 0); cp(h, 'level menu'); pick(h, 'Copy'); cp(h, 'level copied: list')
        pick(h, 1); pick(h, 'Edit', 1.5); cp(h, 'edit the copy')
        cellmenu(h, 'Level >', 'Copy tower'); cp(h, 'tower list'); K(h, 'Down', 12); cp(h, 'tower list scrolled (preview)'); fire(h, 1.5); cp(h, 'tower M2 T5 copied (map)')
        at(h, 2, 30); cp(h, 'map of the copied tower, scrolled')
        cellmenu(h, 'Level >', 'Blank grid'); cp(h, 'blank grid')
        cellmenu(h, 'Leave editor'); cp(h, 'Leave editor: levels list')
        pick(h, 1); pick(h, 'Delete'); cp(h, 'copy deleted'); pick(h, 0); pick(h, '< back'); cp(h, 'level menu back')
        pick(h, '< back'); cp(h, 'main menu again')
        # campaigns
        pick(h, 'Campaigns'); cp(h, 'campaign list (empty)'); pick(h, '<new campaign>'); cp(h, 'new campaign: entry editor')
        for i in range(3): pick(h, '<add entry>')
        cp(h, '3 entries'); pick(h, 0); cp(h, 'entry menu'); pick(h, 'Change source'); cp(h, 'entry 1 changed')
        pick(h, 1); pick(h, 'Insert after'); cp(h, 'insert after 2'); pick(h, 0); pick(h, 'Move down'); cp(h, 'move down'); pick(h, 1); pick(h, 'Move up'); cp(h, 'move up')
        pick(h, 3); pick(h, 'Remove'); cp(h, 'remove 4')
        print('presses', cycle_custom(h, 2), flush=True)
        cp(h, 'entry 3 cycled to the custom level'); pick(h, 2); pick(h, 'Change source'); cp(h, 'entry 3 cycled once more (wrap)')
        print('presses', cycle_custom(h, 1), flush=True)
        cp(h, 'entry 2 = the custom level'); pick(h, 0); pick(h, '< back'); cp(h, 'entry menu back')
        pick(h, '< back'); cp(h, 'campaign list'); pick(h, 0); cp(h, 'campaign menu'); pick(h, 'Rename'); cp(h, 'campaign rename')
        K(h, 'Up', 3); K(h, 'Right'); K(h, 'Down', 2); cp(h, 'campaign rename edited'); fire(h); cp(h, 'campaign renamed: list')
        pick(h, 0); pick(h, 'Edit entries'); cp(h, 'entries again'); pick(h, '< back'); pick(h, '< back'); cp(h, 'main menu')
        pick(h, 'Levels'); pick(h, 0); pick(h, 'Copy'); pick(h, 0); pick(h, 'Delete'); cp(h, 'level 1 deleted: the campaign lost / renumbered its entry')
        pick(h, '< back'); pick(h, 'Campaigns'); pick(h, 0); pick(h, 'Edit entries'); cp(h, 'entries after the level delete'); pick(h, '< back')
        pick(h, '<new campaign>'); pick(h, '< back'); cp(h, 'two campaigns'); pick(h, 0); pick(h, 'Delete'); cp(h, 'campaign 1 deleted'); pick(h, '< back'); cp(h, 'main')
        # campaign disk
        pick(h, 'Save to campaign disk'); cp(h, 'disk prompt'); h.key('F10', hold=0.3); time.sleep(1.0); cp(h, 'disk prompt cancelled by F10')
        pick(h, 'Save to campaign disk'); fire(h, 0.5); wait_disk(h); cp(h, 'save without a disk')
        disk = OUT + 'camp.st'; shutil.copy('/tmp/nlcv/x/lg/ne/d/blank.st', disk); h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(3.0)
        pick(h, 'Save to campaign disk'); fire(h, 0.5); wait_disk(h); cp(h, 'saved to the campaign disk')
        pick(h, 'Levels'); pick(h, 0); pick(h, 'Delete'); pick(h, '< back'); cp(h, 'level deleted in RAM')
        pick(h, 'Load from campaign disk'); fire(h, 0.5); wait_disk(h); cp(h, 'loaded from the campaign disk')
        tail(h)
    finally:
        json.dump(IDX, open(OUT + 'index.json', 'w'), indent=0)
        h.close(); time.sleep(1)
run()
print('checkpoints', len(IDX))
