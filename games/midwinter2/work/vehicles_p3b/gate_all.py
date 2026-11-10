#!/usr/bin/env python3
"""gate_all.py MHZ OUT [TYPES] [SCENS] [SET=P]: the per-type exactness gate (A vs SET, group ends) for all 22 types x stand / movturn / allin.
One line per run: type, scenario, ticks compared, ticks with any diff (runtype.py + vcmp.py, same masks as vehicles_p3b.md section 4)."""
import sys, subprocess
H = '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b'
NAMES = "Tank Jeep Truck Bus Train Foot Speedboat Crawler Minisub Submarine Ship Frogman Biplane Helicopter Zeppelin Balloon Rocket Parachute FlyingBoat Hovercraft FlyingSub Swimming".split()
mhz, out = sys.argv[1], sys.argv[2]
types = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[3] != '-' else [5, 1, 2, 3, 0, 4, 7, 6, 10, 19, 21, 9, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20]
scens = sys.argv[4].split(',') if len(sys.argv) > 4 else ['stand', 'movturn', 'allin']
sset = sys.argv[5] if len(sys.argv) > 5 else 'P'
with open(out, 'a') as f:
    for t in types:
        for s in scens:
            r = subprocess.run(['python3', H + '/runtype.py', str(t), s, sset, '--mhz', mhz], capture_output=True, text=True)
            lines = [l for l in r.stdout.splitlines() if 'ticks compared' in l]
            first = lines[0].split(': ', 1)[1] if lines else 'NO RESULT ' + r.stdout[-300:].replace('\n', ' ') + r.stderr[-200:].replace('\n', ' ')
            # diff detail lines (first 4) when not clean
            det = ''
            if lines and ' 0' != first[-2:]:
                body = r.stdout.splitlines()
                i = body.index(lines[0]) if lines[0] in body else -1
                det = ' || ' + ' ; '.join(x.strip() for x in body[i + 1:i + 5])
            f.write(f'GATE {mhz}MHz type {t} {NAMES[t]} {s}: {first}{det}\n'); f.flush()
    f.write('DONE\n')
