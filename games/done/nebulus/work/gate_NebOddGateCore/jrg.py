"""NebGateCore wrapper: work/junkram/jr.py with its output dirs (J) redirected to work/gate_NebOddGateCore, own Hatari workdir.
usage: jrg.py BUILDDIR MACHINE MODE TAG SEED...   MODE = rs | all | leftover:<name> (files work/gate_NebOddGateCore/left/leftover_<name>_{0,1}.bin)
Prints one JSON row per boot (build field = TAG)."""
import sys, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/junkram')
import jr
from pathlib import Path
MY = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateCore')
jr.J = MY / 'left'          # leftover_*.bin are read from here (jr.one: J / f'leftover_..')
(MY / 'left' / 'shots').mkdir(parents=True, exist_ok=True)
_N = jr.Nebulus
jr.Nebulus = lambda **kw: _N(**{**kw, 'workdir': '/tmp/strun-oddcore-jr-' + kw.get('machine', 'ste')})
build, machine, mode, tag = sys.argv[1:5]
for s in sys.argv[5:]:
    r = jr.one(build, machine, mode, int(s))
    r['build'] = tag
    print(json.dumps(r), flush=True)
