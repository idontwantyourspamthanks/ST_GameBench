"""Floppy build UI gate for per-level colours/enemies (NebLooksGate): boot the floppy game disk (real FDC), F10 manager, new level, Tower > Colours/Enemies,
Playtest (palette/raster/skyline/eye frames == stock tower values of the HD base8 dump), leave (commit), Save to campaign disk (image swapped in drive A:), image check,
zero the store, Load from the saved image, flags persist, Edit shows them, Play from the list.   usage: fl_ui.py GAME.st WORKDIR REFDIR(HD base8 run_look dump) [ste|st|megaste]"""
import sys; sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebFloppyEject')
from lib import *
import shutil, re
sys.path.insert(0, G + 'tools')
import nebcampaign as nc, ovl
GAME, WD, REFDIR = sys.argv[1], sys.argv[2], sys.argv[3]; MACH = sys.argv[4] if len(sys.argv) > 4 else 'ste'
MEM = {'ste': 1024, 'st': 1024, 'megaste': 4096}[MACH]
V = 0x77cc0; RS = 0x77c80
OUT = WD + '_out/'; shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
disk = OUT + 'camp.st'; shutil.copy('/tmp/neblooksui/lg/fl_new/Nebulus_campaign_disk.st', disk); open(OUT + 'zero.ovl', 'wb').write(bytes(8192))
h = NebFloppy(GAME, machine=MACH, mem=MEM, workdir=WD, trace='fdc'); t = T(h)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def menu():
    p = L(h, V + 4); d = grab(h, p, 700, 'menu'); n = d[0]; items = []; i = 1
    for _ in range(n):
        j = i + 2
        while d[j]: j += 1
        items.append(d[i + 2:j].decode('latin1')); i = j + 1
    return items, W(h, V + 8)
def goto(idx):
    for _ in range(40):
        items, sel = menu()
        if sel == idx: return
        h.key('Down' if idx > sel else 'Up', hold=0.2); time.sleep(0.45)
    raise RuntimeError('goto')
def pick(what, gap=1.3):
    items, sel = menu(); idx = what if isinstance(what, int) else [i for i, x in enumerate(items) if x.startswith(what)][0]
    goto(idx); h.key('Control_R', hold=0.35); time.sleep(gap)
def level_menu(label, gap=1.3):
    h.key('Control_R', hold=0.35); time.sleep(1.5)
    pick('Level >', 1.0); pick(label, gap)
TMAP = [int(x) for x in re.search(r"^tmap:\s+dc\.b\s+([\d,]+)", open(G + 'patches/ed_editor.s').read(), re.M).group(1).split(',')]
def theme(k):
    pal = grab(h, 0x35250 + k * 32, 32, 'tp'); return b''.join(pal[b:b + 2] for b in TMAP)
def epal(): return grab(h, 0xA8980, 32, 'ep')
def flag_byte(): return grab(h, RS + 50, 1, 'fl')[0]
def flags_of(data):
    out = []; p = ovl.LV0
    for i in range(struct.unpack('>H', data[6:8])[0]): out.append(data[p + 3]); p += 20 + struct.unpack('>H', data[p + 4:p + 6])[0]
    return out
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
def ref(tw, a, n): return open(f'{REFDIR}/lvl{tw}.bin', 'rb').read()[a:a + n]
def look_check(tag, c, e, base):
    ct = c - 1 if c else base; et = e - 1 if e else base
    chk(f'{tag}: palette == stock tower {ct+1}', grab(h, 0x351ac, 32, 'p'), ref(ct, 0x351ac, 32))
    chk(f'{tag}: raster colours ($40390 on the floppy) == stock tower {ct+1}', grab(h, 0x40390, 8, 'r'), ref(ct, 0x40398, 8))
    chk(f'{tag}: skyline buffer == stock tower {ct+1}', grab(h, 0x100e0, 4096, 's'), ref(ct, 0x100e0, 4096))
    chk(f'{tag}: eye frames == stock tower {et+1} design', grab(h, 0x24be0, 0xaf00, 'e'), ref(et, 0x24be0, 0xaf00))
try:
    print('floppy title', bool(h.boot_to_title(timeout=400, space_at=25 if MEM > 1024 else 20)), flush=True); time.sleep(3)
    print('info: word at PP address $3dbf0 on the floppy (the floppy code is displaced: not the hook site):', hex(W(h, 0x3dbf0)), flush=True)
    v0 = L(h, 0x70); h.shot(OUT + '01_title.png')
    h.key('F10', hold=0.5); time.sleep(2.5); chk('F10 opens the manager (VBL vector changed)', L(h, 0x70) != v0); h.shot(OUT + '02_manager.png')
    pick('Levels'); pick('<new level>', 1.5)
    chk('editor: new level starts with flags 0', flag_byte(), 0)
    level_menu('Colours >', 1.2); items, sel = menu()
    chk('floppy: Colours list = the 8 tower names (the floppy build reads the name table at its own address)', (items[0], items[7], items[8], sel), ('1 The Tower Of Eyes', '8 The Edge Of Doom', '< back', 0))
    ok = True
    for k in range(1, 8):
        h.key('Down', hold=0.2); time.sleep(0.6)
        if epal() != theme(k): ok = False
    chk('floppy: every cursor move re-themes the screen: EPAL == palette table of set k (k = 2..8)', ok); h.shot(OUT + '02b_colour_list_hl8.png')
    goto(4); h.key('Control_R', hold=0.35); time.sleep(1.5)
    chk('floppy: pick colours 5 -> tower byte 4, flags 0, map theme 5', (W(h, RS + 14), flag_byte(), epal() == theme(4)), (4, 0, True))
    level_menu('Enemies >', 1.2); goto(2); h.key('Control_R', hold=0.35); time.sleep(1.5)
    chk('floppy: pick enemies 3 -> flags 3', flag_byte(), 3); h.shot(OUT + '03_panel_S5_E3.png')
    h.key('l', hold=0.2); time.sleep(0.4)
    h.key('Control_R', hold=0.35); time.sleep(1.0); pick('Playtest', 1.0)
    chk('playtest running', wait_running()); time.sleep(2.0)
    look_check('floppy playtest colours 5 / enemies 3', 5, 3, 4); chk('base tower word $3390c = 4', W(h, 0x3390c), 4); h.shot(OUT + '04_playtest.png')
    h.key('F10', hold=0.4); time.sleep(2.0); chk('back in the editor, flags still 3', flag_byte(), 3)
    h.key('F10', hold=0.4); time.sleep(1.5); ram = t.store(); chk('committed record flags', flags_of(ram), [3]); chk('store validates', ovl.validate(ram), [])
    t.insert(disk); m = op(save=True); chk('Save to campaign disk', m, 'Saved'); h.shot(OUT + '05_saved.png')
    t.insert(D + 'blank.st'); time.sleep(3)
    ok, text, data = nc.status(open(disk, 'rb').read()); chk('saved image usable', ok); chk('saved file flags', flags_of(data), [3]); chk('saved file == RAM store', data == ram)
    h.debug(f'loadbin {OUT}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
    chk('store zeroed', flags_of(t.store()) if t.store()[:4] == b'NCMP' else [], [])
    t.insert(disk); m = op(); chk('Load from campaign disk', m, 'Loaded 1 levels / 0 campaigns')
    chk('reloaded store flags (RAM) == saved', flags_of(t.store()), [3])
    pick('Levels'); pick(0); pick('Edit', 1.5); chk('Edit shows flags 3 / tower 4', (flag_byte(), W(h, RS + 14)), (3, 4)); h.shot(OUT + '06_edit_after_reload.png')
    h.key('F10', hold=0.4); time.sleep(1.5); pick(0); pick('Play', 1.0)
    chk('Play from the list: running', wait_running()); time.sleep(2.0); look_check('floppy Play of reloaded level', 5, 3, 4); h.shot(OUT + '07_play_reloaded.png')
except Exception as ex:
    import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
finally:
    h.close(); time.sleep(1)
log = open(WD + '/log.txt', errors='replace').read() if os.path.exists(WD + '/log.txt') else ''
crash = re.findall(r'Address error|Illegal|double bus|CPU halted|bus error', log, re.I)
chk('no crash lines in the Hatari log', crash, [])
print('FAILS', fails); open(f'/tmp/neblooksui/lg/logs/fl_ui_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
