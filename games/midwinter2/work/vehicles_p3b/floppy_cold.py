#!/usr/bin/env python3
"""floppy_cold.py MACHINE [--build DIR] [--raids]: cold boot the candidate FLOPPY build (mw2patch build --floppy --only <cand>) from the disk images to the Lobos 3D view
(campaign start: Helicopter, $6220 = 13), check MWPO, then run coldboot.measure (ticks/s, per-flip pose while turning, contact sheet, fps at 8/16/32 MHz).
Then Esc (hold 0.6 s) from the Helicopter: Parachute (17) and, after the landing, on foot (5): the vehicle types the floppy campaign reaches without the Raids map.
MACHINE: ste | tt.  Procedure after work/floppy_tests/run_cell.py (drive A boots FFA, swapped to the graphics disk at the prompt; drive B = the campaign disk)."""
import sys, time, json, shutil, subprocess, traceback
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
import coldboot
from coldboot import measure, posedump, smooth, strip, OUT
from stharness import TOS
CFG = {'ste': dict(machine='ste', tos=TOS['1.62'], memsize_kb=1024, extra=[], clock=None),
       'tt': dict(machine='tt', tos=TOS['3.06'], memsize_kb=4096, extra=[], clock=32)}
FT = GAME / 'work' / 'floppy_tests'

def build(dst):
    names = cand_names() + ['floppy_copybuf', 'mw2_credit']
    subprocess.run([sys.executable, str(GAME / 'tools/mw2patch.py'), 'build', '--floppy', '--only', *names, '--out', str(dst)], check=True, cwd=GAME, stdout=subprocess.DEVNULL)

def matches(h, ref, box, tol=4.0):
    return h.screen_matches(ref, box, tol=tol)

def main():
    mach = sys.argv[1]; c = CFG[mach]
    dst = GAME / (sys.argv[sys.argv.index('--build') + 1] if '--build' in sys.argv else 'build/fl_cand')
    if '--nobuild' not in sys.argv: build(dst)
    scratch = Path(f'/tmp/flc_{mach}'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
    for src, d in (('FFA_boot.st', 'A.st'), ('FFB_graphics.st', 'B.st')):
        shutil.copy(dst / src, scratch / d)
    shutil.copy(GAME / 'work/disk_overlay/FILES/FFD', scratch / 'D.st')
    empty = scratch / 'empty'; empty.mkdir()
    res = {'machine': mach}
    h = Hatari(snapshot=None, memsize_kb=c['memsize_kb'], machine=c['machine'], tos=c['tos'], game_dir=empty,
               extra=['--disk-a', str(scratch / 'A.st'), '--disk-b', str(scratch / 'D.st')] + c['extra'])
    try:
        t0 = time.time()
        ins = FT / 'ref_insert_graphics.png'; box = (280, 360, 560, 420)
        while time.time() - t0 < 300:
            time.sleep(4)
            if matches(h, ins, box, 0.3 * 8): break
        else:
            raise RuntimeError('never saw the Insert Graphics Disk prompt')
        print(mach, 'insert-graphics prompt after %d s' % (time.time() - t0), flush=True)
        h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}"); time.sleep(2)
        ref = GAME / 'work/ref/mode_select.png'
        for i in range(40):
            h.cmd('hatari-event keypress 57'); time.sleep(5)
            if h.screen_matches(ref, (280, 350, 560, 420)): break
        else:
            raise RuntimeError('never reached the M/J/K screen')
        res['marker'] = memb(h, 0xb2ff8, 4).hex()
        h.debug('w $2c574 $60 $02')              # TEST ONLY: PP's skip of the security check (the floppy build has none)
        for _ in range(5):
            time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(5)
            if not h.screen_matches(ref, (280, 350, 560, 420)): break
        HALL = (FT / 'ref_hall.png', (96, 350, 736, 458)); PERS = (FT / 'ref_personnel.png', (96, 100, 330, 350)); MAP = (FT / 'ref_map.png', (96, 300, 560, 458))
        def wait_match(t, timeout):
            t0 = time.time()
            while time.time() - t0 < timeout:
                if h.screen_matches(t[0], t[1], tol=4.0): return True
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
        step((554, 105), PERS); step((389, 140), HALL); step((414, 185), MAP, timeout=100)
        time.sleep(25)
        h.goto(150, 280); h.key('space'); time.sleep(18)
        h.goto(230, 410); h.click(); time.sleep(15)
        boss = GAME / 'work/ref/boss_thumbs.png'
        for _ in range(6):
            h.goto(140, 415); h.click(); time.sleep(8)
            if h.screen_matches(boss, (590, 60, 740, 125)): break
        else:
            raise RuntimeError('never reached the boss screen')
        h.goto(625, 92); h.click(); time.sleep(40)
        for _ in range(12):
            if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2: break
            time.sleep(5)
        else:
            raise RuntimeError('did not reach the 3D view')
        time.sleep(30)
        print(mach, 'boot to the 3D view: %d s' % (time.time() - t0), 'type', h.peekw(0x6220), 'marker', memb(h, 0xb2ff8, 4), flush=True)
        if c['clock']: h.set_cpuclock(c['clock'])
        d = measure(h, c, f'fl_{mach}_heli')
        d['marker_boot'] = res['marker']
        print(mach, 'heli', json.dumps(d, default=str), flush=True)
        # Esc from the Helicopter -> Parachute -> (landing) on foot
        h.set_cpuclock(c['clock'] or 8)
        for _ in range(8):
            h.key('Escape', hold=0.6); time.sleep(2)
            if h.peekw(0x6220) != 13: break
        t1 = h.peekw(0x6220); time.sleep(40); t2 = h.peekw(0x6220)
        print(mach, 'Esc from the Helicopter: type', t1, '-> after 40 s', t2, flush=True)
        if t2 == 5:
            d2 = measure(h, c, f'fl_{mach}_foot'); print(mach, 'foot', json.dumps(d2, default=str), flush=True)
    except Exception as e:
        print(mach, 'ERROR', repr(e), traceback.format_exc()[-800:], flush=True)
        try: h.shot(str(OUT / f'fl_{mach}_exc.png'))
        except Exception: pass
    finally:
        h.close()
main()
