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
       'tt': dict(machine='tt', tos=TOS['3.06'], memsize_kb=4096, extra=['--mmu', 'true'], clock=32)}
FT = GAME / 'work' / 'floppy_tests'

def build(dst):
    names = cand_names() + ['floppy_copybuf', 'mw2_credit']
    subprocess.run([sys.executable, str(GAME / 'tools/mw2patch.py'), 'build', '--floppy', '--only', *names, '--out', str(dst)], check=True, cwd=GAME, stdout=subprocess.DEVNULL)

def sdiff(h, ref, box):
    """run_cell.py's comparison: the reference images are FULL ST screenshots (832x588); both are cropped to `box` (ST-screenshot coordinates; a TT shot has no border: shifted)"""
    from PIL import Image, ImageChops, ImageStat
    img = Image.open(h.shot()).convert('RGB')
    ib = (box[0] - 96, box[1] - 58, box[2] - 96, box[3] - 58) if img.width == 640 else box
    d = ImageChops.difference(img.crop(ib), Image.open(ref).convert('RGB').crop(box))
    return sum(ImageStat.Stat(d).mean) / 3

def matches(h, ref, box, tol=4.0):
    return sdiff(h, ref, box) < tol

def esctrace(h, vbls):
    """arm a per-flip dump, press Esc (hold 0.6 s) from the current vehicle, return [(vbl, X, Y, heading, alt, type)] over `vbls` VBL"""
    lf = h.R / 'esc.txt'; lf.write_text('e VBL\nm $66e6 8\nm $6742 2\nm $764c 2\nm $6220 2\n')
    h.debug('b all', 0.3); st = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b ($ff8201).b ! ($ff8201).b :trace :file {lf}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + vbls} :trace :once'); time.sleep(0.2)
    h._xdo('keydown', '--window', h.win, 'Escape'); time.sleep(0.6)
    h._xdo('keyup', '--window', h.win, 'Escape')
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[st:]:
        if time.time() - t > 900: break
        time.sleep(0.5)
    out = h._logtext()[st:]; h.debug('b all', 0.3)
    rows = []
    pat = r'#(\d+) \(dec\)[^\n]*\n> m \$66e6 8\n0*66e6:\s+((?:[0-9a-f]{2} ){8})[^\n]*\n> m \$6742 2\n0*6742:\s+(\w\w) (\w\w)[^\n]*\n> m \$764c 2\n0*764c:\s+(\w\w) (\w\w)[^\n]*\n> m \$6220 2\n0*6220:\s+(\w\w) (\w\w)'
    for m in re.finditer(pat, out, re.I):
        b = bytes.fromhex(m.group(2).replace(' ', ''))
        rows.append((int(m.group(1)), sw(b[:4]), sw(b[4:]), int(m.group(3) + m.group(4), 16), int(m.group(5) + m.group(6), 16), int(m.group(7) + m.group(8), 16)))
    return rows

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
            if matches(h, ins, box, 0.3): break
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
                if matches(h, t[0], t[1], 4.0): return True
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
        t1 = time.time()
        while h.peekw(0xb42e6) == 0 and time.time() - t1 < 900: time.sleep(5)      # $6220/$700a are already set on the vehicle wireframe loading screen (slow on a TT): wait for the game loop (p3cp PH word)
        print(mach, 'game loop running (p3cp PH word %d) %d s after the loading screen' % (h.peekw(0xb42e6), time.time() - t1), flush=True)
        time.sleep(30)
        print(mach, 'boot to the 3D view: %d s' % (time.time() - t0), 'type', h.peekw(0x6220), 'marker', memb(h, 0xb2ff8, 4), flush=True)
        if c['clock']: h.set_cpuclock(c['clock'])
        if '--esc-first' not in sys.argv:
            d = measure(h, c, f'fl_{mach}_heli')
            d['marker_boot'] = res['marker']
            print(mach, 'heli', json.dumps(d, default=str), flush=True)
        # Esc from the Helicopter -> Parachute -> (landing) on foot: per-flip trace (VBL, X, Y, heading, altitude $764c, type) from just before the Esc.
        # --esc-first: Esc while the Helicopter still stands at its start altitude (2000; after the forward flight of measure() it is down at the terrain, 1945, and Esc there gives on foot (5) directly;
        # a poke of $764c does not survive: p3cp's fixup restores the pose words at every PH 1)
        h.set_cpuclock(c['clock'] or 8)
        print(mach, 'altitude $764c before Esc:', h.peekw(0x764c), flush=True)
        rows = esctrace(h, 900)
        types = []
        for r in rows:
            if not types or types[-1][0] != r[5]: types.append((r[5], r[0]))
        res['esc_types'] = types
        print(mach, 'Esc from the Helicopter: type sequence (type, first flip VBL):', types, flush=True)
        for ty in (17, 5):
            sub = [r for r in rows if r[5] == ty]
            if len(sub) > 2:
                ch = sum(1 for x, y in zip(sub, sub[1:]) if x[1:5] != y[1:5])
                print(mach, 'type', ty, 'flips', len(sub), 'flips whose pose (X,Y,heading,alt) differs from the previous flip', ch, 'mean gap VBL', round((sub[-1][0] - sub[0][0]) / (len(sub) - 1), 2), flush=True)
        if h.peekw(0x6220) == 5:
            time.sleep(5)
            d2 = measure(h, c, f'fl_{mach}_foot'); print(mach, 'foot', json.dumps(d2, default=str), flush=True)
    except Exception as e:
        print(mach, 'ERROR', repr(e), traceback.format_exc()[-800:], flush=True)
        try: h.shot(str(OUT / f'fl_{mach}_exc.png'))
        except Exception: pass
    finally:
        h.close()
main()
