#!/usr/bin/env python3
"""Cold boot for machines slower than the 1 MB STE recipe (e.g. Mega STE 4 MB, TOS 2.06 ~100 s memory test).
A non-stopping breakpoint at the game entry pc=$33b00 dumps RAM; space is pressed every 2 s from --t0 until it fires.
No title/fire handling: this reaches `jmp $33b00` only (loader proof), not a tower.
usage: boot4.py OUTDIR [--machine megaste --mem 4096 --tos 2.06 --game DIR --t0 20 --dump KB --settle 6 --peek ADDR[,ADDR]]"""
import argparse, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, str(HERE.parent.parent / 'tools'))
from nebulus import Nebulus, TOS, ORIGIN
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--machine', default='ste')
ap.add_argument('--mem', type=int, default=1024); ap.add_argument('--tos', default='1.62')
ap.add_argument('--game', default=str(ORIGIN)); ap.add_argument('--t0', type=float, default=2.0)
ap.add_argument('--dump', type=int, default=1024, help='KB to dump at entry and after settle'); ap.add_argument('--settle', type=float, default=8.0)
ap.add_argument('--timeout', type=float, default=400.0); ap.add_argument('--work', default='scratch/b4')
ap.add_argument('--cpuclock', default=None); ap.add_argument('--stage2', action='store_true', help='break at pc=$38624 (game after its own relocation) instead of $33b00')
a = ap.parse_args()
out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
extra = ['--cpuclock', a.cpuclock] if a.cpuclock else None
h = Nebulus(workdir=str(HERE / a.work), machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, game=Path(a.game), extra=extra)
try:
    cmdf = out / 'entry.cmd'
    ent = out / 'ram_entry.bin'
    for f in ('ram_entry.bin', 'ram_settle.bin', 'final.png'):
        (out / f).unlink(missing_ok=True)
    cmdf.write_text(f"savebin {ent} 0 ${a.dump*1024:x}\n")
    h.cmd(f"hatari-debug b pc = {'$38624' if a.stage2 else '$33b00'} :trace :once :file {cmdf}")
    t0 = time.time(); n = 0
    while time.time() - t0 < a.timeout and not (ent.exists() and ent.stat().st_size >= a.dump * 1024):
        time.sleep(2)
        if time.time() - t0 > a.t0:
            h.keypress(57); n += 1
    print('entry reached', ent.exists(), 'after %.0f s, %d spaces' % (time.time() - t0, n))
    time.sleep(a.settle)
    h.dump(str(out / 'ram_settle.bin'), 0, a.dump * 1024)
    h.shot(str(out / 'final.png'))
finally:
    h.close()
