"""Vehicle p3b test library (MW2VehImpl). Run from anywhere; absolute paths."""
import sys, json, re, time, subprocess, os
from pathlib import Path
GAME = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(GAME / 'tools'))
from mw2harness import Hatari
SNAP = GAME / 'work/snapshots'

def build_live(only, name):
    out = GAME / 'build' / 'veh' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(GAME / 'tools/mw2patch.py'), 'live', '--out', str(out.relative_to(GAME))]
    if only is not None:
        cmd += ['--only', *only]
    subprocess.run(cmd, check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    return str(out)

def apply_cmds(prefix):
    spec = json.loads(Path(prefix + '.json').read_text())
    c = [f"loadbin {Path(prefix + '.img').resolve()} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + ' '.join(f"${b:02x}" for b in bytes.fromhex(s['new'])) for s in spec['sites']]
    return c

def wait_gone(h, start, timeout=900):
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError('breakpoint never fired:\n' + h._logtext()[-1500:])
        time.sleep(0.3)
    time.sleep(0.3)

def at_flip(h, cmds, after_vbl):
    f = h.R / 'atflip.txt'
    f.write_text('\n'.join(cmds) + '\n')
    h.debug('b all', 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {after_vbl} && pc = ${h.FLIP:x} :trace :once :file {f}")
    wait_gone(h, start, 300)

def pokew(addr, v): return f"w ${addr:x} ${(v>>8)&255:02x} ${v&255:02x}"
def pokel(addr, v): return f"w ${addr:x} " + ' '.join(f"${b:02x}" for b in (v & 0xffffffff).to_bytes(4, 'big'))

def memb(h, addr, n):
    out = h.debug(f"m ${addr:x} {n}", 0.7)
    bs = b''
    for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)', out, re.M | re.I):
        bs += bytes.fromhex(m.group(2).replace(' ', ''))
    return bs

def sw(b): return int.from_bytes(b, 'big', signed=True)
def uw(b): return int.from_bytes(b, 'big')


def default_names():
    """names of the `default: yes` boot/deferred patches (no HAGA file patches, no floppy_*, no credit)"""
    out = subprocess.run([sys.executable, str(GAME / 'tools/mw2patch.py'), 'list'], capture_output=True, text=True, cwd=GAME).stdout
    return [l.split()[0] for l in out.splitlines()[1:] if len(l.split()) > 2 and l.split()[1] == 'yes' and 'HAGA' not in l
            and not l.startswith(('pp_', 'floppy')) and l.split()[0] != 'mw2_credit']

CAND_OFF = set()
def cand_names():
    """the candidate set: defaults + p3cp_head + p3c_sim + p7_skip_render (the three `default: no` patches the lead flips); crop OFF"""
    out = subprocess.run([sys.executable, str(GAME / 'tools/mw2patch.py'), 'list'], capture_output=True, text=True, cwd=GAME).stdout
    have = {l.split()[0] for l in out.splitlines()[1:] if l.split()}
    names = [n for n in default_names() if n not in CAND_OFF]
    for n in ('p3cp_head', 'p3c_sim', 'p7_skip_render'):
        if n in have and n not in names: names.append(n)
    return names
