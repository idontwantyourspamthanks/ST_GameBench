"""capture.py BUILD MACHINE TAG: boot BUILD (patched), use the editor (F10 open/leave), dirty the state cells, then dump the RAM a relaunch would find
($75728..$77ec0 and $AA000..$C0000) to work/junkram/leftover_<TAG>_0.bin/_1.bin for `jr.py BUILD MACHINE leftover:<TAG> SEED`."""
import sys, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/junkram')
from jr import *
from relaunch import wait_title
MY = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore')
build, machine, tag = sys.argv[1:4]
ste = machine == 'ste'
kw = {} if ste else dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)
path = Path(build)
h = Nebulus(game=path, workdir=f'/tmp/strun-gcore-cap-{machine}', **kw)
try:
    print('title', wait_title(h, ste, 100 if ste else 330), flush=True); time.sleep(3)
    h.key('F10', hold=0.12); time.sleep(2.0); h.key('F10', hold=0.12); time.sleep(2.0)
    h.debug('w $76c02 $ff $ff $ff $ff', 0.3); h.debug('w $76d00 $00 $01 $00 $01', 0.3); h.debug('w $77ca8 $00 $01', 0.3)
    h.debug('w $77cb4 $de $ad $be $ef $00 $07 $11 $22 $33 $44', 0.3)
    print('marker', rdh(h, 0xb0020, 4), 'trainers', rdh(h, 0x76c00, 8), flush=True)
    for i, (lo, hi) in enumerate(((0x75728, 0x77ec0), (0xAA000, 0xC0000))):
        f = MY / f'left/leftover_{tag}_{i}.bin'
        h.debug(f'savebin {f} ${lo:x} ${hi - lo:x}', 1.5)
        print(f, f.stat().st_size, hi - lo, flush=True)
finally:
    h.close()
