"""NebLooksUI user-flow gate on the ALL-GAMES hard disk image (the user's flow), Mega STE TOS 2.06 4 MB, cold boot (slow), C:\\NEBULUS\\START.TOS autostarted, real keys:
F10 -> Levels -> <new level> -> Level > Colours > (cursor to 6) FIRE -> Enemies > 2 -> Playtest (palette/raster/skyline/eyes vs stock, screenshot) -> F10 -> leave editor
-> Campaigns -> <new campaign> -> <add entry> -> Change source until 'L NEW LEVEL' -> back -> Play: the campaign plays the level with the picked look (palette == stock tower 6, screenshot).
usage: e202.py IMG WORKDIR  (IMG = a COPY of dist/AtariST_enhanced_games_*.img whose NEBULUS\\START.TOS / NEPATCH.BIN / NEBLEVEL.OVL are the build under test)"""
import sys, os, time, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl
IMG, WD = sys.argv[1], sys.argv[2]; OUT = WD + '_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
REFDIR = os.environ.get('REFDIR', '/tmp/nlg/x/lg/r/base8_ste')
def rdref(t, a, n): return open(f'{REFDIR}/lvl{t}.bin', 'rb').read()[a:a + n]
def run():
    h = UH(IMG, WD)
    try:
        t0 = time.time(); chk('title reached', h.boot_to_title(timeout=400, space_until=400)); time.sleep(3)
        chk('NEPO marker', grab(h, 0xB0020, 4, 'n'), b'NEPO')
        chk('F10 opens the manager', open_manager(h)); h.shot(OUT + '01_manager.png')
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        level_menu(h, 'Colours >', 1.2); h.shot(OUT + '02_colour_list.png'); goto(h, 5); time.sleep(0.5); h.shot(OUT + '03_colour_list_hl6.png')
        h.key('Control_R', hold=0.35); time.sleep(1.5); h.shot(OUT + '04_editor_colours6.png')
        level_menu(h, 'Enemies >', 1.2); goto(h, 1); h.key('Control_R', hold=0.35); time.sleep(1.5)
        chk('tower byte 5 (colours 6), flags 2 (enemies 2)', (W(h, RS + 14), flag_byte(h)), (5, 2))
        h.key('Control_R', hold=0.35); time.sleep(1.0); pick(h, 'Playtest', 1.0)
        chk('playtest running', wait_running(h, 150)); time.sleep(2)
        chk('playtest palette == stock tower 6', grab(h, 0x351ac, 32, 'p'), rdref(5, 0x351ac, 32))
        chk('playtest raster == stock tower 6', grab(h, 0x40398, 8, 'r'), rdref(5, 0x40398, 8))
        chk('playtest skyline buffer == stock tower 6', grab(h, 0x100e0, 4096, 's'), rdref(5, 0x100e0, 4096))
        chk('playtest eye frames == design 2', grab(h, 0x24be0, 0xaf00, 'e'), rdref(1, 0x24be0, 0xaf00))
        h.shot(OUT + '05_playtest.png')
        h.key('F10', hold=0.4); time.sleep(2.0); h.key('F10', hold=0.4); time.sleep(1.5)       # back in the editor, then leave (commit)
        # we are at the level list now; back to the manager and make a campaign
        h.key('Left', hold=0.2); time.sleep(1.2)
        pick(h, 'Campaigns'); pick(h, '<new campaign>', 1.5)
        pick(h, '<add entry>', 1.2)
        for k in range(17):
            items, sel = menu(h)
            if any(t.startswith('01 L') for a, p, t in items): break
            pick(h, 0, 1.0); pick(h, 'Change source', 1.2)
        items, sel = menu(h); chk('entry 1 is the custom level', items[0][2].startswith('01 L'), True); h.shot(OUT + '06_entry.png')
        h.key('Left', hold=0.2); time.sleep(1.2)
        pick(h, 0); pick(h, 'Play', 1.0)
        chk('campaign running', wait_running(h, 150)); time.sleep(2)
        chk('campaign: rsCamp set, rsLvl = level 1', (W(h, RS), W(h, RS + 4)), (1, 1))
        chk('campaign palette == stock tower 6', grab(h, 0x351ac, 32, 'p'), rdref(5, 0x351ac, 32))
        chk('campaign raster == stock tower 6', grab(h, 0x40398, 8, 'r'), rdref(5, 0x40398, 8))
        chk('campaign skyline == stock tower 6', grab(h, 0x100e0, 4096, 's'), rdref(5, 0x100e0, 4096))
        chk('campaign eye frames == design 2', grab(h, 0x24be0, 0xaf00, 'e'), rdref(1, 0x24be0, 0xaf00))
        h.shot(OUT + '07_campaign_play.png')
        chk('no Address/Bus Error/exception after the boot noise', [e for e in errors(h) if 'e001a0' not in e and 'fff000' not in e and 'ffff8781' not in e], [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e202.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
