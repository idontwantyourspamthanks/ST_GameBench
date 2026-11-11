#!/usr/bin/env python3
"""coldboot.py MACHINE [--types foot,jeep,speedboat,biplane,heli] [--build DIR] [--out DIR]
Cold boot the candidate build (default build/vehp3cp: `mw2patch.py build --only <cand_names + pp_* + mw2_credit>`) to the Raids map once, save the map state
(the patched code was loaded by the cold boot; the deferred patches are applied by the load hook on every 3D entry), then enter each island from it and measure:
  marker $b2ff8 (MWPO), type/view, the three hooks in RAM, bus errors,
  ticks/s at $31586 (once per 5 Hz tick) and PH samples,
  a per-flip pose log while moving (flip VBL, X, Y, heading, bank): the 'frame strip' numbers, plus a contact sheet of 6 screenshots,
  fps while moving at 8 / 16 / 32 MHz.
MACHINE: ste1 | megaste4 | tt4 | st1"""
import sys, re, time, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from vt import *
from stharness import TOS
import mw2raids
from mw2raids import cold_to_raid_map, enter_raid
from PIL import Image
BUILD = GAME / 'build' / 'vehp3cp'
OUT = GAME / 'work' / 'vehicles_p3b' / 'cold'
CFG = {'ste1': dict(machine='ste', tos=TOS['1.62'], memsize_kb=1024, extra=[], clock=None),
       'st1': dict(machine='st', tos=TOS['1.04'], memsize_kb=1024, extra=[], clock=None),
       'megaste4': dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096, extra=[], clock=16),
       'tt4': dict(machine='tt', tos=TOS['3.06'], memsize_kb=4096, extra=['--mmu', 'true'], clock=32)}
ISL = {'foot': (591, 231, 5), 'jeep': (446, 177, 1), 'speedboat': (275, 249, 6), 'biplane': (344, 230, 12), 'heli': (149, 271, 13)}
def mk(c, snap=None):
    return Hatari(snapshot=snap, memsize_kb=c['memsize_kb'], game_dir=BUILD, machine=c['machine'], tos=c['tos'], extra=c['extra'])

def posedump(h, vbls, during=None):
    """pose at every presented flip over `vbls` VBL: [(vbl, X, Y, heading, bank)]"""
    lf = h.R / 'pose.txt'; lf.write_text('e VBL\nm $66e6 8\nm $6742 2\nm $6746 2\n')
    h.debug('b all', 0.3); s = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b ($ff8201).b ! ($ff8201).b :trace :file {lf}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + vbls} :trace :once'); time.sleep(0.2)
    if during: during()                                   # input sent while the dump is armed (turn impulses)
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[s:]:
        if time.time() - t > 300: break
        time.sleep(0.3)
    out = h._logtext()[s:]; h.debug('b all', 0.3)
    rows = []
    for m in re.finditer(r'#(\d+) \(dec\)[^\n]*\n> m \$66e6 8\n0*66e6:\s+((?:[0-9a-f]{2} ){8})[^\n]*\n> m \$6742 2\n0*6742:\s+(\w\w) (\w\w)[^\n]*\n> m \$6746 2\n0*6746:\s+(\w\w) (\w\w)', out, re.I):
        b = bytes.fromhex(m.group(2).replace(' ', ''))
        rows.append((int(m.group(1)), sw(b[:4]), sw(b[4:]), int(m.group(3) + m.group(4), 16), sw(bytes.fromhex(m.group(5) + m.group(6)))))
    return rows

def strip(h, name, n=6, gap=0.3):
    imgs = []
    for i in range(n):
        im = Image.open(h.shot()).convert('RGB')
        imgs.append(im.crop((0, 0, 640, 400) if im.width == 640 else (96, 58, 736, 458)).resize((320, 200)))   # a TT shot has no border
        time.sleep(gap)
    W = Image.new('RGB', (960, 400))
    for i, im in enumerate(imgs): W.paste(im, ((i % 3) * 320, (i // 3) * 200))
    OUT.mkdir(exist_ok=True)
    p = OUT / f'{name}.png'; W.save(p)
    return str(p)

def smooth(rows):
    """per-flip pose delta statistics: flips, flips whose pose differs from the previous flip, distinct poses, mean/max VBL gap between flips"""
    if len(rows) < 3: return dict(flips=len(rows))
    ch = sum(1 for a, b in zip(rows, rows[1:]) if a[1:4] != b[1:4])
    gaps = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
    hc = sum(1 for a, b in zip(rows, rows[1:]) if a[3] != b[3])
    return dict(flips=len(rows), pose_changes=ch, heading_changes=hc, heading_span=max(r[3] for r in rows) - min(r[3] for r in rows), distinct=len({r[1:4] for r in rows}), mean_gap_vbl=round(sum(gaps) / len(gaps), 2), max_gap_vbl=max(gaps))

def measure(h, c, name):
    d = {}
    d['marker'] = memb(h, 0xb2ff8, 4)
    d['type'] = h.peekw(0x6220); d['view'] = h.peekw(0x700a)
    d['hook'] = memb(h, 0x31570, 6).hex(); d['head'] = memb(h, 0x31486, 8).hex()
    # forward (mouse Y is the throttle), then measure the 5 Hz tick rate
    h.rel(0, -200); time.sleep(0.3); h.rel(0, -200); time.sleep(0.3)
    p0 = memb(h, 0x66e6, 8)
    lf = h.R / 'tk.txt'; lf.write_text('e VBL\nm $b3400 4\n')
    h.debug('b all', 0.3); s = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b pc = $31586 :trace :file {lf}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + 400} :trace :once'); time.sleep(0.2)
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[s:]:
        if time.time() - t > 900: break
        time.sleep(0.5)
    out = h._logtext()[s:]; h.debug('b all', 0.3)
    # (VBL, clock) pairs: a bare `#(\d+) \(dec\)` scan also counts the window-END breakpoint's line as a tick (the 4.4-4.65 ticks/s artefact)
    pr = [(int(a), int(b.replace(' ', ''), 16)) for a, b in re.findall(r'#(\d+) \(dec\)[^\n]*\n> m \$b3400 4\n0*b3400:\s+((?:[0-9a-f]{2} ){4})', out, re.I)]
    vb = [a for a, b in pr]
    # rate from the tick_vbl clock ($b3400, 1/300 s = real time): the VBL rate is 50 OR 60 Hz (the Mega STE cold boot runs 60 Hz) and the sync register read is unreliable on a TT
    ck = [b for a, b in pr]
    d['ticks'] = len(vb)
    d['ticks_per_s'] = round((len(ck) - 1) * 300.0 / max(1, ck[-1] - ck[0]), 3) if len(ck) > 2 and len(ck) == len(vb) else None
    d['vbl_per_s'] = round((vb[-1] - vb[0]) * 300.0 / max(1, ck[-1] - ck[0]), 2) if len(ck) > 2 else None
    d['PH_samples'] = [h.peekw(0xb42e6) for _ in range(12) if not time.sleep(0.07)]
    p1 = memb(h, 0x66e6, 8)
    d['moved'] = (sw(p0[:4]), sw(p0[4:]), sw(p1[:4]), sw(p1[4:]))
    # turn while moving: pose per flip
    for _ in range(6): h.rel(25, 0, steps=5); time.sleep(0.25)
    rows = posedump(h, 150)
    d['posedump'] = rows[:60]
    d['smooth_turn'] = smooth(rows)
    d['strip'] = strip(h, name)
    # fps while moving at three clocks
    d['fps'] = {}
    for mhz in (8, 16, 32):
        try:
            h.set_cpuclock(mhz); time.sleep(2)
            d['fps'][mhz] = round(h.fps(500)['fps'], 2)
        except Exception as e:
            d['fps'][mhz] = repr(e)
    d['bus_error'] = 'Bus Error' in h._logtext() or 'bus error' in h._logtext()
    d['marker_after'] = memb(h, 0xb2ff8, 4)
    return d

def main():
    mach = sys.argv[1]; types = ['foot', 'jeep', 'speedboat', 'biplane', 'heli']
    if '--types' in sys.argv: types = sys.argv[sys.argv.index('--types') + 1].split(',')
    global BUILD
    if '--build' in sys.argv: BUILD = GAME / sys.argv[sys.argv.index('--build') + 1]
    c = CFG[mach]
    mapsav = f'/tmp/cold_{mach}_map.sav'
    h = mk(c)
    try:
        t0 = time.time()
        cold_to_raid_map(h)
        print(mach, 'cold boot to the raid map: %d s, marker %s' % (time.time() - t0, memb(h, 0xb2ff8, 4)), flush=True)
        h.savemem(mapsav)
    finally:
        h.close()
    for ty in types:
        x, y, want = ISL[ty]
        h = mk(c, mapsav)
        try:
            if c['clock']: h.set_cpuclock(c['clock'])
            time.sleep(4)
            r = enter_raid(h, x, y)
            time.sleep(8)
            d = measure(h, c, f'{mach}_{ty}')
            d['enter'] = r; d['want'] = want
            print(mach, ty, json.dumps(d, default=str), flush=True)
        except Exception as e:
            print(mach, ty, 'ERROR', repr(e), flush=True)
        finally:
            h.close()
if __name__ == '__main__':
    main()
