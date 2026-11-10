#!/usr/bin/env python3
"""coldboot.py MACHINE [--types foot,jeep,speedboat,biplane,heli]: cold boot the candidate build (build/vehp3cp) to the Raids map once, save the map state,
then enter each island from it (the patched code was loaded by the cold boot; the deferred patches are applied by the load hook on every 3D entry), and measure.
MACHINE: ste1 | megaste4 | tt4 | st1"""
import sys, re, time, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from vt import *
from stharness import TOS
import mw2raids
from mw2raids import cold_to_raid_map, enter_raid
BUILD = GAME / 'build' / 'vehp3cp'
CFG = {'ste1': dict(machine='ste', tos=TOS['1.62'], memsize_kb=1024, extra=[], clock=None),
       'st1': dict(machine='st', tos=TOS['1.04'], memsize_kb=1024, extra=[], clock=None),
       'megaste4': dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096, extra=[], clock=16),
       'tt4': dict(machine='tt', tos=TOS['3.06'], memsize_kb=4096, extra=['--mmu', 'true'], clock=32)}
ISL = {'foot': (591, 231, 5), 'jeep': (446, 177, 1), 'speedboat': (275, 249, 6), 'biplane': (344, 230, 12), 'heli': (149, 271, 13)}
def mk(c, snap=None):
    return Hatari(snapshot=snap, memsize_kb=c['memsize_kb'], game_dir=BUILD, machine=c['machine'], tos=c['tos'], extra=c['extra'])
def measure(h, ticks_vbl=400):
    """ticks/s at $31586 (once per 5 Hz tick), PH sampling, flips, pose motion; returns dict"""
    d = {}
    d['marker'] = memb(h, 0xb2ff8, 4)
    d['type'] = h.peekw(0x6220); d['view'] = h.peekw(0x700a)
    d['hook'] = memb(h, 0x31570, 6).hex(); d['head'] = memb(h, 0x31486, 8).hex()
    # input: forward (mouse Y) twice, then a turn burst
    h.rel(0, -200); time.sleep(0.3); h.rel(0, -200); time.sleep(0.3)
    p0 = memb(h, 0x66e6, 8)
    lf = h.R / 'tk.txt'; lf.write_text('e VBL\nm $b42e6 2\n')
    h.debug('b all', 0.3); s = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b pc = $31586 :trace :file {lf}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + ticks_vbl} :trace :once'); time.sleep(0.2)
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[s:]:
        if time.time() - t > 900: break
        time.sleep(0.5)
    out = h._logtext()[s:]; h.debug('b all', 0.3)
    vb = [int(x) for x in re.findall(r'#(\d+) \(dec\)', out)]
    d['ticks'] = len(vb); d['span_vbl'] = (vb[-1] - vb[0]) if vb else 0
    sync = h.peekw(0xff820a) >> 8; hz = 50 if sync & 2 else 60
    d['ticks_per_s'] = round((len(vb) - 1) * hz / max(1, vb[-1] - vb[0]), 3) if len(vb) > 2 else None
    d['hz'] = hz
    ph = []
    for _ in range(12): ph.append(h.peekw(0xb42e6)); time.sleep(0.07)
    d['PH_samples'] = ph
    p1 = memb(h, 0x66e6, 8)
    d['moved'] = (sw(p0[:4]), sw(p0[4:]), sw(p1[:4]), sw(p1[4:]))
    f = h.fps(500); d['fps'] = f['fps']
    d['bus_error'] = 'Bus Error' in h._logtext()
    return d
def main():
    mach = sys.argv[1]; types = ['foot', 'jeep', 'speedboat', 'biplane', 'heli']
    if '--types' in sys.argv: types = sys.argv[sys.argv.index('--types') + 1].split(',')
    c = CFG[mach]
    res = {}
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
            d = measure(h)
            d['enter'] = r; d['want'] = want
            res[ty] = d
            print(mach, ty, json.dumps(d, default=str), flush=True)
        except Exception as e:
            print(mach, ty, 'ERROR', repr(e), flush=True)
        finally:
            h.close()
main()
