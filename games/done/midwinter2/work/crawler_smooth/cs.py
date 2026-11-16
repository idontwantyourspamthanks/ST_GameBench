"""Crawler smoothing study helpers (CrawlerSmooth). Scratch only."""
import sys, json, re, time, subprocess, os
from pathlib import Path
GAME = Path('/home/ryan/Code/AtariST/gamebench/games/done/midwinter2')
HERE = GAME / 'work/crawler_smooth'
sys.path.insert(0, str(GAME / 'tools'))
from mw2harness import Hatari
SNAP = GAME / 'work/snapshots'
DUMP = (GAME / 'work/dumps/ram_ingame_lobos.bin').read_bytes()

def build_live(only, name, patchdir=None):
    out = HERE / 'build' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(GAME / 'tools/mw2patch.py'), 'live', '--out', str(out.relative_to(GAME))]
    if only is not None:
        cmd += ['--only', *only]
    env = dict(os.environ)
    if patchdir: env['PATCHDIR'] = str(patchdir)
    subprocess.run(cmd, check=True, cwd=GAME, stdout=subprocess.DEVNULL, env=env)
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

def blk(t):
    b = DUMP[0x54dc0+t*0x3e:0x54dc0+(t+1)*0x3e]
    w = lambda o: int.from_bytes(b[o:o+2],'big',signed=True)
    return dict(Ydz=w(4), Ylo=w(6), Yhi=w(8), Xdz=w(0x12), Xlo=w(0x14), Xhi=w(0x16))

def move_pokes(t, fwd=True, turn=True):
    b = blk(t); p = []
    f = min(b['Yhi'], b['Ydz'] + 150); tn = -(b['Xdz'] + 60)
    if tn < b['Xlo']: tn = b['Xlo']
    if fwd: p.append(pokel(0x6fba, (f & 0xffff) << 16))
    if turn: p.append(pokel(0x6fb6, (tn & 0xffff) << 16))
    return p

def default_names():
    out = subprocess.run([sys.executable, str(GAME / 'tools/mw2patch.py'), 'list'], capture_output=True, text=True, cwd=GAME).stdout
    return [l.split()[0] for l in out.splitlines()[1:] if len(l.split()) > 2 and l.split()[1] == 'yes' and 'HAGA' not in l and '(floppy)' not in l
            and not l.startswith(('pp_', 'floppy', 'jag_')) and l.split()[0] != 'mw2_credit']

def parse_hits(txt, first):
    """rows of {addr: byte} per hit; a hit starts with the `m $first` line"""
    rows = []; cur = None
    for m in re.finditer(r'(?:#(\d+) \(dec\)|^([0-9A-F]{8}):((?: [0-9a-f]{2})+))', txt, re.M | re.I):
        if m.group(1):
            cur = {'vbl': int(m.group(1))}; rows.append(cur); continue
        if cur is None: continue
        a = int(m.group(2), 16)
        for i, b in enumerate(bytes.fromhex(m.group(3).replace(' ', ''))):
            cur[a + i] = b
    return [r for r in rows if first in r]

def rd(r, a, n=2, signed=False):
    return int.from_bytes(bytes(r[a+i] for i in range(n)), 'big', signed=signed)

def build_scratch(name, only=None):
    """live image from the scratch patch dir work/crawler_smooth/patches (own copies; p3cp_head.s carries the experiment)"""
    only = only or default_names()
    out = HERE / 'build' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    code = f"""
import sys; sys.path.insert(0,'{GAME}/tools')
import mw2patch as m
from pathlib import Path
m.PATCHDIR = Path('{HERE}/patches')
ps = [p for p in m.load_patches() if p.name in {only!r}]
assert {{p.name for p in ps}} == set({only!r}), ({{p.name for p in ps}})
m.cmd_live(ps, Path('{out}'))
"""
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return str(out)
