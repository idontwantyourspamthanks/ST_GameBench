"""dumpcmp.py BUILD MACHINE: cold boot (no junk), at the title dump the patched game text $33b1c..$3e382 and the patch zone $75728..$77ec0 + RS/V and print md5s
(compare two builds: the loader change must not change a byte of the patched result)."""
import sys, hashlib, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/junkram')
from jr import *
from relaunch import wait_title
build, machine, tag = sys.argv[1:4]
ste = machine == 'ste'
kw = {} if ste else dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)
path = Path(build) if Path(build).is_absolute() else J / 'build' / build
h = Nebulus(game=path, workdir=f'/tmp/strun-oddcore-{machine}', **kw)
try:
    ok = wait_title(h, ste, 100 if ste else 330); time.sleep(4)
    out = dict(build=tag, machine=machine, title=ok, marker=rdh(h, 0xb0020, 8))
    for nm, lo, hi in (('text', 0x33b1c, 0x3e382), ('zone', 0x75728, 0x77ec0)):
        f = J / Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateCore/out')/f'dump_{tag}_{machine}_{nm}.bin'
        h.debug(f'savebin {f} ${lo:x} ${hi - lo:x}', 2.0)
        d = f.read_bytes(); out[nm] = (len(d), hashlib.md5(d).hexdigest())
    print(json.dumps(out), flush=True)
finally:
    h.close()
