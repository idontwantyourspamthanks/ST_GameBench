#!/usr/bin/env python3
"""coldtrace.py MACHINE [--types foot,jeep,heli] [--vbl 900]: cold boot of build/vehp3cp, then per island:
 direct per-tick trace (every pc=$31586 hit: VBL and the tick_vbl clock $b3400, 1/300 s units) over --vbl VBL while moving,
 then turn + per-flip pose dump + contact sheet.  ticks/s is computed from the tick_vbl clock (real time, independent of 50/60 Hz)."""
import sys, re, time, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
import coldboot
from coldboot import *

def tickrun(h, nvbl):
    lf = h.R / 'tk.txt'; lf.write_text('e VBL\nm $b3400 4\nm $66e6 8\nm $6742 2\n')
    h.debug('b all', 0.3); s = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b pc = $31586 :trace :file {lf}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + nvbl} :trace :once'); time.sleep(0.2)
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[s:]:
        if time.time() - t > 1500: break
        time.sleep(0.5)
    out = h._logtext()[s:]; h.debug('b all', 0.3)
    rows = []
    for m in re.finditer(r'#(\d+) \(dec\)[^\n]*\n> m \$b3400 4\n0*b3400:\s+((?:[0-9a-f]{2} ){4})[^\n]*\n> m \$66e6 8\n0*66e6:\s+((?:[0-9a-f]{2} ){8})[^\n]*\n> m \$6742 2\n0*6742:\s+(\w\w) (\w\w)', out, re.I):
        rows.append((int(m.group(1)), int(m.group(2).replace(' ', ''), 16), m.group(3).replace(' ', '') + m.group(4) + m.group(5)))
    return rows

def tstats(rows):
    if len(rows) < 3: return dict(ticks=len(rows))
    vb = [r[0] for r in rows]; ck = [r[1] for r in rows]
    iv = [b - a for a, b in zip(vb, vb[1:])]
    span_c = ck[-1] - ck[0]
    short = [i for i in range(1, len(rows)) if vb[i] - vb[i - 1] <= 1]
    same = [i for i in range(1, len(rows)) if rows[i][2] == rows[i - 1][2]]
    return dict(ticks=len(rows), span_vbl=vb[-1] - vb[0], span_s=round(span_c / 300, 2), ticks_per_s_clock=round((len(rows) - 1) * 300 / span_c, 3),
                ticks_per_s_50hz=round((len(rows) - 1) * 50 / (vb[-1] - vb[0]), 3), max_gap_vbl=max(iv), min_gap_vbl=min(iv),
                short_hits=len(short), pose_unchanged_hits=len(same), short_and_unchanged=len(set(short) & set(same)), max_gap_s=round(max(b - a for a, b in zip(ck, ck[1:])) / 300, 3), gaps_hist={g: iv.count(g) for g in sorted(set(iv))})

def main():
    mach = sys.argv[1]; types = ['foot', 'jeep', 'heli']
    nv = int(sys.argv[sys.argv.index('--vbl') + 1]) if '--vbl' in sys.argv else 900
    if '--types' in sys.argv: types = sys.argv[sys.argv.index('--types') + 1].split(',')
    c = CFG[mach]; mapsav = f'/tmp/cold_{mach}_map.sav'
    h = None if '--reuse' in sys.argv else mk(c)
    if h is not None:
      try:
        t0 = time.time(); cold_to_raid_map(h)
        print(mach, 'cold boot to the raid map: %d s, marker %s' % (time.time() - t0, memb(h, 0xb2ff8, 4)), flush=True)
        h.savemem(mapsav)
      finally:
        h.close()
    for ty in types:
        x, y, want = ISL[ty]
        h = mk(c, mapsav); d = {}
        try:
            if c['clock']: h.set_cpuclock(c['clock'])
            time.sleep(4)
            d['enter'] = enter_raid(h, x, y); time.sleep(8)
            t1 = time.time()
            while h.peekw(0x6220) != want and time.time() - t1 < 120: time.sleep(2)      # the foot island starts as Parachute (17) and lands on foot (5)
            d['marker'] = memb(h, 0xb2ff8, 4).hex(); d['type'] = h.peekw(0x6220); d['want'] = want; d['view'] = h.peekw(0x700a)
            d['hook'] = memb(h, 0x31570, 6).hex(); d['head'] = memb(h, 0x31486, 8).hex()
            h.rel(0, -200); time.sleep(0.3); h.rel(0, -200); time.sleep(0.3)
            d['tick_move'] = tstats(tickrun(h, nv))
            d['type_after'] = h.peekw(0x6220)
            def turn():
                for _ in range(10): h.rel(25, 0, steps=5); time.sleep(0.2)
            rows = posedump(h, 150, during=turn)
            d['posedump_first'] = rows[:30]; d['posedump_all'] = rows; d['smooth_turn'] = smooth(rows)
            d['strip'] = strip(h, f'{mach}_{ty}_v2')
            d['bus_error'] = 'bus error' in h._logtext().lower(); d['marker_after'] = memb(h, 0xb2ff8, 4).hex()
            print(mach, ty, json.dumps(d, default=str), flush=True)
        except Exception as e:
            import traceback
            print(mach, ty, 'ERROR', repr(e), traceback.format_exc()[-600:], json.dumps(d, default=str), flush=True)
        finally:
            h.close()
main()
