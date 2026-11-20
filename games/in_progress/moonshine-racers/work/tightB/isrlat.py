"""Interrupt entry latency in Hatari for a patched build running a driving snapshot with interrupts on.
   python3 isrlat.py SNAP VARIANT NVBL OUT.json   (VARIANT = base[+patch...])
Persistent trace breakpoints: Timer B ISR $d616, VBL ISR $d11e, IKBD ISR $cfb4: each logs `e LineCycles` and `e VBL` (+ FrameCycles); 3 key presses are injected for the ACIA ISR.
Hatari does NOT model the blitter holding off interrupt acknowledge in a way that delays the entry (see sprites.md section 6): this measures what the emulator shows."""
import sys, json, re, time, os, statistics
from pathlib import Path
GAME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GAME / 'tools'))
os.environ.setdefault('MSRPATCH_TOOL', str(GAME / 'work/tightB/msrpatch_priv.py')); os.environ.setdefault('MSR_LIVETAG', '_tb')
import msrabtest as ab
from msr import Moonshine
snap, var, nvbl, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
BASE = ['mr_edge', 'rd_geom', 'rd_draw', 'rd_init', 'hd_stage', 'hd_init', 'hd_clouds', 'hd_nomap', 'hd_nomap2']
names = BASE + [x for x in var.split('+')[1:] if x]
live = ab.live_build(names)
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5)
    ab.apply_live(h, live, 0x7A88); time.sleep(0.4); h.debug('b all', 0.3)
    for nm, pc in (('tb', 0xd616), ('vbl', 0xd11e), ('kb', 0xcfb4)):
        (h.R / f'l_{nm}.txt').write_text(f"e LineCycles\ne VBL\ne FrameCycles\n")
    n0 = len(h._logtext()); v0 = h.vbl()
    for nm, pc in (('tb', 0xd616), ('vbl', 0xd11e), ('kb', 0xcfb4)):
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R}/l_{nm}.txt"); time.sleep(0.2)
    t0 = time.time(); k = 0
    while h.vbl() < v0 + nvbl and time.time() - t0 < 900:
        time.sleep(2); k += 1
        if k in (3, 6, 9): h.keypress(44)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
res = {'tb': [], 'vbl': [], 'kb': []}
parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", log)
for i in range(1, len(parts) - 1, 2):
    pc = int(parts[i].split('$')[1], 16); nums = re.findall(r"#(\d+)(?:/-?\d+)? \(dec\)", parts[i + 1])
    if len(nums) >= 3: res[{0xd616: 'tb', 0xd11e: 'vbl', 0xcfb4: 'kb'}[pc]].append((int(nums[0]), int(nums[1]), int(nums[2])))
json.dump(res, open(out, 'w'))
for nm, v in res.items():
    lc = sorted(x[0] for x in v)
    if lc: print(f"{var:28s} {nm:3s} entries {len(lc):5d} LineCycles min {lc[0]} median {lc[len(lc)//2]} p90 {lc[int(len(lc)*.9)]} p99 {lc[int(len(lc)*.99)]} max {lc[-1]}")
