"""Per-call cost of the generated car path in Hatari (e CycleCounter at stub entry $BF500, hit-path jmp $BF5E6, return $ed70, create $BF6E8..$BF93A).
   python3 carcost.py SNAP NPASSVBL [extra patch names...]"""
import sys, re, time, os, statistics
from pathlib import Path
GAME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GAME / 'tools'))
os.environ.setdefault('MSRPATCH_TOOL', str(GAME / 'work/tightB/msrpatch_priv.py')); os.environ.setdefault('MSR_LIVETAG', '_tb')
import msrabtest as ab
from msr import Moonshine
snap, nvbl = sys.argv[1], int(sys.argv[2]); extra = sys.argv[3:] or ['tb_car', 'tb_carph']
BASE = ['mr_edge', 'rd_geom', 'rd_draw', 'rd_init', 'hd_stage', 'hd_init', 'hd_clouds', 'hd_nomap', 'hd_nomap2']
live = ab.live_build(BASE + extra)
PCS = {0xBF500: 'entry', 0xBF5E6: 'hit', 0xED70: 'ret', 0xBF6E8: 'cr0', 0xBF93A: 'cr1'}
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5); h.debug('b all', 0.3)
    ab.apply_live(h, live, 0x7A88); time.sleep(0.4); h.debug('b all', 0.3)
    for pc, nm in PCS.items(): (h.R / f'cc_{pc:x}.txt').write_text("e CycleCounter\ne a2\n")
    n0 = len(h._logtext()); v0 = h.vbl()
    for pc in PCS: h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R}/cc_{pc:x}.txt"); time.sleep(0.2)
    t0 = time.time()
    while h.vbl() < v0 + nvbl and time.time() - t0 < 600: time.sleep(1)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
ev = []
parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", log)
for i in range(1, len(parts) - 1, 2):
    pc = int(parts[i].split('$')[1], 16); nums = re.findall(r"#(\d+)(?:/-?\d+)? \(dec\)", parts[i + 1])
    if len(nums) >= 2: ev.append((PCS[pc], int(nums[0]), int(nums[1])))
res = {'stub': [], 'draw': [], 'total': [], 'create': []}
cur = None
for nm, cyc, a2 in ev:
    if nm == 'entry': cur = {'e': cyc, 'a2': a2}
    elif nm == 'hit' and cur: cur['h'] = cyc
    elif nm == 'ret' and cur and 'h' in cur:
        res['stub'].append(cur['h'] - cur['e']); res['draw'].append(cyc - cur['h']); res['total'].append((cur['a2'], cyc - cur['e'])); cur = None
    elif nm == 'cr0': cur = None; c0 = cyc
    elif nm == 'cr1': res['create'].append(cyc - c0)
for a2 in (0x2c68, 0x3480):
    t = [x for a, x in res['total'] if a == a2]
    if t: print(f"slot ${a2:x}: calls {len(t)} total (stub entry -> return) mean {statistics.mean(t):.0f} min {min(t)} max {max(t)}")
if res['stub']: print(f"stub overhead (entry -> jmp (a4)) mean {statistics.mean(res['stub']):.0f}; compiled code mean {statistics.mean(res['draw']):.0f}")
print('create (generation) calls', len(res['create']), res['create'][:20])
