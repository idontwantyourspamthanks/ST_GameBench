"""Emulator kernel-table gate: stock vs mx (X_TEST extras) per pass over the whole code/state area $1000-$19000 on a dump of any track.
python3 kgate.py DUMP NPASS NTEST [kind=zig] [LIVEPREFIX]   (run from work/extrap: it needs its modules)"""
import sys, os, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
os.chdir('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
import gate2, gate3
from gate2 import *
live = sys.argv[5] if len(sys.argv) > 5 else '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/int/mx/live/emu'
gate3.apply_live = lambda e: gate2.apply_live(e, live)
dump, npass, ntest = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); kind = sys.argv[4] if len(sys.argv) > 4 else 'zig'
es, S = gate3.runs_(dump, npass, 0, False, kind)
ep, P = gate3.runs_(dump, npass, ntest, True, kind)
bad = {}
for p in range(npass):
    for a in list(range(0x1000, 0x7000)) + list(range(0x7000, 0x19000)):
        if S[p][a] != P[p][a] and not gate3.masked(a): bad.setdefault(a, []).append(p)
print(f"{dump} {npass} passes ntest={ntest} input={kind}: groups {ep.l(0xB8F3C)}/{ep.l(0xB8F40)} extras {ep.l(0xB8F38)}; differing bytes {len(bad)}; runs:",
      [f"{s:x}-{t:x}@{min(bad[s])}({len(bad[s])})" for s, t in region_runs(sorted(bad))][:40])
