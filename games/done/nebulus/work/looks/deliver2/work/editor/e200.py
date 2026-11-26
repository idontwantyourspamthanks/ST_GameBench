"""NebLooksUI gate: colour / enemy / copy-tower list pickers with live preview, the editor view recolouring (EPAL), Crumble ledge placement, playtest of the pick, store round trip.
usage: e200.py BUILD_DIR WORKDIR [ste|megaste|st] [--snap FILE]"""
import sys, os, time, struct, re, shutil, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl, nebcampaign as nc
args = sys.argv[1:]
SNAP = None
if '--snap' in args: i = args.index('--snap'); SNAP = args[i + 1]; del args[i:i + 2]
BUILD, WD = args[0], args[1]; MACH = args[2] if len(args) > 2 else 'ste'
SNAP = SNAP or f'/tmp/neblooksui/title_{MACH}_new.sav'
OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
if not os.path.exists(SNAP): print('snapshot boot', mk_snap(BUILD, SNAP, MACH, WD + '_snap'), flush=True)
data = gzip.open(SNAP).read()
for sig in (b'Crumble ledge', b'Colours >', b'Level >', bytes.fromhex('303900077cbe')):
    assert sig in data, f'stale snapshot {SNAP}: {sig!r} missing'
SRC = open('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/patches/ed_editor.s').read()
TMAP = [int(x) for x in re.search(r"^tmap:\s+dc\.b\s+([\d,]+)", SRC, re.M).group(1).split(',')]
EPAL = 0xA8980
REFDIR = os.environ.get('REFDIR', '/tmp/neblooksui/lg/r/base8_ste')
def rdref(t, a, n): return open(f'{REFDIR}/lvl{t}.bin', 'rb').read()[a:a + n]
def theme(h, k):
    pal = grab(h, 0x35250 + k * 32, 32, 'tp'); return b''.join(pal[b:b + 2] for b in TMAP)
def epal(h): return grab(h, EPAL, 32, 'ep')
def flags_of(data):
    out = []; p = ovl.LV0
    for i in range(struct.unpack('>H', data[6:8])[0]): out.append(data[p + 3]); p += 20 + struct.unpack('>H', data[p + 4:p + 6])[0]
    return out
def recs(data):
    out = []; p = ovl.LV0
    for i in range(struct.unpack('>H', data[6:8])[0]):
        out.append(tuple(data[p:p + 4])); p += 20 + struct.unpack('>H', data[p + 4:p + 6])[0]
    return out
def lst(h): items, sel = menu(h); return [t for a, p, t in items], sel
def cell_at(h, x, y): return grab(h, 0x327f0 + x * 256 + y, 1, 'c')[0]
def open_list(h, label):
    level_menu(h, label, 1.2); return lst(h)
def run():
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **({'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}))
    D = OUT
    disk = D + 'camp.st'; shutil.copy('/tmp/neblooksui/lg/ne/d/blank.st', disk); open(D + 'zero.ovl', 'wb').write(bytes(8192))
    try:
        time.sleep(2); h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('F10 opens the manager', open_manager(h))
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        chk('new level: tower 0, mission 1, flags 0', (W(h, RS + 14), W(h, RS + 12), flag_byte(h)), (0, 1, 0))
        chk('map view palette == theme of colour set 1 (the editor recolours itself)', epal(h), theme(h, 0))
        h.shot(D + '01_new_level_map.png')
        h.key('Control_R', hold=0.35); time.sleep(1.5)
        items, sel = lst(h); chk('root menu has Crumble ledge and Level >, no Conveyor, no Tower >', ('Crumble ledge' in items, 'Level >' in items, 'Tower >' in items), (True, True, False))
        h.shot(D + '02_root_menu.png')
        pick(h, 'Level >', 1.0); items, sel = lst(h)
        chk('Level > items', items, ['Colours >', 'Enemies >', 'Copy tower >', 'Blank grid', 'Time +50', 'Time -50', 'Name...', '< back'])
        h.shot(D + '03_level_menu.png')
        pick(h, 'Colours >', 1.2); items, sel = lst(h)
        names = ['The Tower Of Eyes', 'Realm Of The Robots', 'Trap Of Tricks', 'The Slippery Slide', 'The Broken Path', "Swimmer's Delight", 'The Nasty One', 'The Edge Of Doom']
        chk('Colours list = the 8 tower names numbered + back; cursor on the current (1)', (items, sel), ([f'{i + 1} {n}' for i, n in enumerate(names)] + ['< back'], 0))
        h.shot(D + '04_colour_list_1.png')
        ok = True
        for k in range(1, 8):
            h.key('Down', hold=0.2); time.sleep(0.6)
            _, s2 = lst(h); e = epal(h)
            if s2 != k or e != theme(h, k): ok = False; print('preview mismatch', k, s2, e.hex(), theme(h, k).hex())
            if k in (3, 7): h.shot(D + f'05_colour_list_hl{k + 1}.png')
        chk('moving the cursor re-themes the screen: EPAL == theme(k) at every one of the 8 highlights', ok)
        h.key('Left', hold=0.2); time.sleep(1.3)                          # left = "< back"
        chk('back: map again, theme restored to the current choice, nothing changed', (epal(h) == theme(h, 0), W(h, RS + 14), flag_byte(h)), (True, 0, 0))
        level_menu(h, 'Colours >', 1.2); goto(h, 4); time.sleep(0.5); h.key('Control_R', hold=0.35); time.sleep(1.5)
        chk('pick colours 5: tower byte 4, flags colour nibble 0, enemies unchanged', (W(h, RS + 14), flag_byte(h)), (4, 0))
        chk('after the pick the map shows colour set 5 (EPAL == theme(4))', epal(h), theme(h, 4))
        h.shot(D + '06_map_colours5.png')
        items, sel = open_list(h, 'Enemies >')
        chk('Enemies list: 4 designs + back, cursor on the effective one (tower 5 -> design 1)', (items, sel), (['1 Eyelid', '2 Studded', '3 Four orbs', '4 Split plate', '< back'], 0))
        h.shot(D + '07_enemy_list.png')
        goto(h, 2); h.key('Control_R', hold=0.35); time.sleep(1.5)
        chk('pick enemies 3: flags low nibble 3, tower byte kept', (flag_byte(h), W(h, RS + 14)), (3, 4))
        items, sel = open_list(h, 'Colours >'); chk('colours list opens on the current scheme 5', sel, 4)
        h.key('Left', hold=0.2); time.sleep(1.3)
        items, sel = open_list(h, 'Enemies >'); chk('enemies list opens on the current design 3', sel, 2)
        h.key('Left', hold=0.2); time.sleep(1.3)
        h.shot(D + '08_map_S5_E3.png')
        items, sel = open_list(h, 'Copy tower >')
        chk('Copy tower list: 16 towers (mission 1 then 2) + back; cursor = (mission-1)*8+tower', (len(items), sel, items[0], items[8], items[15]), (17, 4, '1 The Tower Of Eyes', '1 A Blink Of The Eye', '8 The Last Trump'))
        h.shot(D + '09_copy_list.png')
        goto(h, 12); time.sleep(0.5); chk('copy list preview = theme of tower 5', epal(h), theme(h, 4)); h.key('Control_R', hold=0.35); time.sleep(2.0)
        chk('Copy tower M2 T5: mission 2, tower 4, flags cleared, rows', (W(h, RS + 12), W(h, RS + 14), flag_byte(h)), (2, 4, 0))
        sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/level/tools'); og, orows = ovl.original(2, 4)
        d = grab(h, 0x327f0, 0x1000, 'g'); rows = W(h, RS + 16)
        chk('grid == the original mission 2 tower 5 decode, rows equal', ([d[a * 256 + r] for a in range(16) for r in range(orows)], rows), ([og[a][r] for a in range(16) for r in range(orows)], orows))
        h.shot(D + '10_after_copy.png')
        # crumble ledge through the UI: put it at the cursor
        h.key('Control_R', hold=0.35); time.sleep(1.5); pick(h, 'Crumble ledge', 1.2)
        chk('Crumble ledge menu item writes $91 at the cursor (0,1)', cell_at(h, 0, 1), 0x91)
        h.shot(D + '11_crumble_placed.png')
        # colours 6 + enemies 2 then playtest: palette / raster / skyline / eyes == stock
        level_menu(h, 'Colours >', 1.2); goto(h, 5); h.key('Control_R', hold=0.35); time.sleep(1.5)
        items, sel = open_list(h, 'Enemies >'); goto(h, 1); h.key('Control_R', hold=0.35); time.sleep(1.5)
        h.key('l', hold=0.2); time.sleep(0.4)
        chk('flags = enemies 2 only ($02), tower 5', (flag_byte(h), W(h, RS + 14)), (2, 5))
        h.key('Control_R', hold=0.35); time.sleep(1.0); pick(h, 'Playtest', 1.0)
        chk('playtest running', wait_running(h, 120)); time.sleep(2.0)
        chk('playtest palette == stock tower 6', grab(h, 0x351ac, 32, 'p'), rdref(5, 0x351ac, 32))
        chk('playtest raster == stock tower 6', grab(h, 0x40398, 8, 'r'), rdref(5, 0x40398, 8))
        chk('playtest skyline buffer == stock tower 6', grab(h, 0x100e0, 4096, 's'), rdref(5, 0x100e0, 4096))
        chk('playtest eye frames == stock design 2 (tower 2)', grab(h, 0x24be0, 0xaf00, 'e'), rdref(1, 0x24be0, 0xaf00))
        chk('playtest $3390c = 5', W(h, 0x3390c), 5)
        h.shot(D + '12_playtest_colours6_enemies2.png')
        h.key('F10', hold=0.4); time.sleep(2.0)
        chk('back in the editor with the pick intact', (flag_byte(h), W(h, RS + 14), W(h, RS + 6)), (2, 5, 1))
        chk('and the map theme is colour set 6 again', epal(h), theme(h, 5))
        h.key('F10', hold=0.4); time.sleep(1.5)
        ram = grab(h, 0xBC000, 8192, 'fl'); chk('committed record (mission, tower, rows, flags)', recs(ram), [(2, 5, rows, 2)]); chk('store validates', ovl.validate(ram), [])
        # save / load / edit round trip
        h.key('Left', hold=0.2); time.sleep(1.2)
        h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        chk('Save to campaign disk', save_load_disk(h, disk, 'Save to campaign disk'), 'Saved')
        h.cmd('hatari-option --disk-a /tmp/neblooksui/lg/ne/d/blank.st'); time.sleep(3.0)
        ok, text, dd = nc.status(open(disk, 'rb').read()); chk('saved disk usable, record == RAM store', (ok, dd == ram), (True, True))
        h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0])); h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        chk('Load from campaign disk', save_load_disk(h, disk, 'Load from campaign disk'), 'Loaded 1 levels / 0 campaigns')
        pick(h, 'Levels'); pick(h, 0); pick(h, 'Edit', 1.5)
        chk('Edit: tower 5, flags 2; Colours list opens on scheme 6, Enemies on design 2', (W(h, RS + 14), flag_byte(h), open_list(h, 'Colours >')[1]), (5, 2, 5))
        h.key('Left', hold=0.2); time.sleep(1.3); chk('Enemies list opens on design 2', open_list(h, 'Enemies >')[1], 1)
        h.key('Left', hold=0.2); time.sleep(1.3)
        h.key('F10', hold=0.4); time.sleep(1.5)
        pick(h, 0); pick(h, 'Copy', 1.5); chk('Copy keeps the record bytes', recs(grab(h, 0xBC000, 8192, 'fl')), [(2, 5, rows, 2)] * 2)
        pick(h, '<new level>', 1.5)
        chk('a new level starts with tower 0 mission 1 flags 0 and theme 1', (W(h, RS + 14), W(h, RS + 12), flag_byte(h), epal(h) == theme(h, 0)), (0, 1, 0, True))
        chk('no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e200_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
