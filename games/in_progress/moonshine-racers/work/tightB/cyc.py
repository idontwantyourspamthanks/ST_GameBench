"""(tightB copy: VARIANT = base[+patch...]) Cycles per pass (loop top $796a -> flip $d1ca; interrupts included) with the ticker state: python3 cyc3.py SNAP VARIANT NPASS OUT.json"""
import sys, json, re, time, statistics
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools')
import msrabtest as ab
from msr import Moonshine
snap, var, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
BASE = ['mr_edge', 'rd_geom', 'rd_draw', 'rd_init', 'hd_stage', 'hd_init', 'hd_clouds', 'hd_nomap', 'hd_nomap2']
SETS = {'stock': None, 'base': BASE}
for a in sys.argv[2].split('+'): pass
CYC = 160256
names = BASE + [x for x in var.split('+')[1:] if x] if var.startswith('base') else None
live = ab.live_build(names) if names else None
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    time.sleep(0.4); h.debug('b all', 0.3)
    (h.R / 'c1.txt').write_text(f"e VBL\ne FrameCycles\nb pc = $d1ca :trace :once :file {h.R}/c2.txt\n")
    (h.R / 'c2.txt').write_text(f"e VBL\ne FrameCycles\nm $100e 2\nm $11ab 1\nm $bf000 2\nm $bf008 2\nm $bf004 4\nb pc = $796a :trace :once :file {h.R}/c1.txt\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $796a :trace :once :file {h.R}/c1.txt")
    t0 = time.time()
    while h._logtext()[n0:].count('> e FrameCycles') < 2 * npass + 2 and time.time() - t0 < 1500: time.sleep(1)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
segs = log.split('> e VBL')[1:]
rows = []; start = None
for sg in segs:
    nums = re.findall(r'#(\d+) \(dec\)', sg)
    if len(nums) < 2: continue
    t = int(nums[0]) * CYC + int(nums[1])
    m1 = re.search(r'0000100E:\s+([0-9a-f]{2}) ([0-9a-f]{2})', sg, re.I); m2 = re.search(r'000011AB:\s+([0-9a-f]{2})', sg, re.I)
    if m1 and m2 and start is not None:
        rows.append(dict(p=int(m1.group(1) + m1.group(2), 16), work=t - start, speech=int(m2.group(1), 16) != 0)); start = None
    elif not m1: start = t
import re as _re
for a in ('000BF000','000BF008','000BF004'):
    mm=_re.findall(a+r':\s+((?:[0-9a-f]{2} ?)+)', log, _re.I)
    if mm: print('mem', a, mm[-1])
json.dump(rows, open(out, 'w'))
for nm, sel in (('no speech', [x['work'] for x in rows if not x['speech']]), ('speech', [x['work'] for x in rows if x['speech']])):
    if sel: print(snap, var, nm, 'n', len(sel), 'mean', round(statistics.mean(sel)), 'min', min(sel), 'max', max(sel))
