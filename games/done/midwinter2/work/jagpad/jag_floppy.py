"""Floppy build cold boot (STE TOS 1.62, 1 MB) to the Lobos 3D view (campaign start = Helicopter), then pad tests.
Adapted from work/floppy_tests/run_cell.py. usage: jag_floppy.py DISKDIR SEQ"""
import sys, shutil, time, traceback
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
from PIL import Image, ImageChops, ImageStat
from stharness import MACHINE_TOS
diskdir = Path(sys.argv[1]); seq = sys.argv[2]
FT = G / 'work/floppy_tests'
def sdiff(h, ref, box):
    cur = Image.open(h.shot()).convert('RGB').crop(box)
    d = ImageChops.difference(cur, Image.open(ref).convert('RGB').crop(box))
    return sum(ImageStat.Stat(d).mean) / 3
scratch = Path('/tmp/fl/run_jag'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
for src, dst in (('FFA_boot.st', 'A.st'), ('FFB_graphics.st', 'B.st')):
    shutil.copy(diskdir / src, scratch / dst)
shutil.copy(G / 'work/disk_overlay/FILES/FFD', scratch / 'D.st')
empty = scratch / 'empty'; empty.mkdir()
h = Hatari(snapshot=None, memsize_kb=1024, machine='ste', tos=MACHINE_TOS['ste'], game_dir=empty,
           extra=PADX + ['--disk-a', str(scratch / 'A.st'), '--disk-b', str(scratch / 'D.st')])
try:
    ins = FT / 'ref_insert_graphics.png'; box = (280, 360, 560, 420)
    t0 = time.time()
    while time.time() - t0 < 300:
        time.sleep(4)
        if sdiff(h, ins, box) < 0.3: break
    else: raise RuntimeError('never saw the Insert Graphics Disk prompt')
    print('insert-graphics prompt after %.0f s' % (time.time() - t0), flush=True)
    h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}"); time.sleep(2)
    ref = G / 'work/ref/mode_select.png'
    for i in range(40):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    else: raise RuntimeError('never reached the M/J/K screen')
    print('M/J/K screen; marker', memb(h, 0xb2ff8, 4), 'sites', [memb(h, a, 6).hex() for a in (0x262f6, 0x26b66, 0x26bea)], flush=True)
    for _ in range(5):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    HALL = (FT / 'ref_hall.png', (96, 350, 736, 458)); PERS = (FT / 'ref_personnel.png', (96, 100, 330, 350)); MAP = (FT / 'ref_map.png', (96, 300, 560, 458))
    def wait_match(target, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if sdiff(h, target[0], target[1]) < 4: return True
            time.sleep(3)
        return False
    def step(point, target, timeout=40, key=None):
        for attempt in range(4):
            h.goto(*point)
            if key: h.key(key)
            else: h.click()
            if wait_match(target, timeout): return attempt
        raise RuntimeError(f'click at {point} never produced the expected screen')
    if not wait_match(HALL, 90): raise RuntimeError('never saw the HQ hall')
    print('hall; personnel', step((554, 105), PERS), flush=True)
    print('agent', step((389, 140), HALL), flush=True)
    print('control door', step((414, 185), MAP, timeout=100), flush=True)
    time.sleep(25)
    h.goto(150, 280); h.key('space'); time.sleep(18)
    h.goto(230, 410); h.click(); time.sleep(15)
    boss = G / 'work/ref/boss_thumbs.png'
    for _ in range(6):
        h.goto(140, 415); h.click(); time.sleep(8)
        if h.screen_matches(boss, (590, 60, 740, 125)): break
    else: raise RuntimeError('never reached the boss screen')
    h.goto(625, 92); h.click(); time.sleep(40)
    for _ in range(12):
        if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2: break
        time.sleep(5)
    else: raise RuntimeError('did not reach the 3D view')
    time.sleep(30)
    print('3D view: type', w(h, 0x6220), 'marker', memb(h, 0xb2ff8, 4), flush=True)
    h.center()
    jmode(h); time.sleep(2)
    S(h, 'J idle')
    battery(h, seq.split(','))
    d = memb(h, 0xb9ea0, 1)
    print('floppy J_ST', d[0], 'PASS' if d[0] == 1 else 'FAIL', 'sites', [memb(h, a, 6).hex() for a in (0x262f6, 0x26b66, 0x26bea)], 'p5', memb(h, 0xb433a, 4).hex())
    print('bus-error log lines:', bus_errors(h)[:6])
    h.shot(str(G / 'work/jagpad/floppy_end.png'))
except Exception as e:
    print('EXC', repr(e)); traceback.print_exc()
    try: h.shot(str(G / 'work/jagpad/floppy_exc.png'))
    except Exception: pass
finally:
    h.close()
