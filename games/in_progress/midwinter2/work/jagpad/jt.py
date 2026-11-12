"""Jaguar-pad test library for MW2 (JagMW2). Absolute paths; run from anywhere.
Pad keys (work/jagpad/pad.cfg, Hatari pad A): Up/Down/Left/Right = D-pad, z=A x=B v=C o=Option p=Pause q=* w=# 0-9 = keypad digits.
"""
import sys, re, time, json, subprocess
from pathlib import Path
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(G / 'tools')); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
SNAP = G / 'work/snapshots'
PADCFG = G / 'work/jagpad/pad.cfg'
PADX = ['--joy1', 'none', '--configfile', str(PADCFG)]

def names(extra=(), drop=()):
    out = subprocess.run([sys.executable, str(G / 'tools/mw2patch.py'), 'list'], capture_output=True, text=True, cwd=G).stdout
    d = [l.split()[0] for l in out.splitlines()[1:] if len(l.split()) > 2 and l.split()[1] == 'yes' and 'HAGA' not in l
         and not l.startswith(('pp_', 'floppy'))]
    return [n for n in d if n not in drop] + list(extra)

def build_live(only, name):
    out = G / 'build' / 'live' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(G / 'tools/mw2patch.py'), 'live', '--out', str(out.relative_to(G)), '--only', *only],
                   check=True, cwd=G, stdout=subprocess.DEVNULL)
    return str(out)

def apply_live(h, prefix):
    spec = json.loads(Path(prefix + '.json').read_text())
    h.debug(f"loadbin {Path(prefix + '.img').resolve()} ${spec['img_base']:x}", 1.0)
    for s in spec['sites']:
        h.debug(f"w ${s['addr']:x} " + ' '.join(f"${b:02x}" for b in bytes.fromhex(s['new'])), 0.4)

def memb(h, addr, n):
    for tries in range(8):
        got = {}
        out = h.debug(f"m ${addr:x} {n}", 0.7 + 0.3 * tries)
        for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)', out, re.M | re.I):
            got[int(m.group(1), 16)] = bytes.fromhex(m.group(2).replace(' ', ''))
        bs = b''.join(got[k] for k in sorted(got))
        if len(bs) >= n:
            return bs[:n]
    raise RuntimeError(f'memory read ${addr:x} {n} failed')

def w(h, addr): return int.from_bytes(memb(h, addr, 2), 'big')
def sw(h, addr): return int.from_bytes(memb(h, addr, 2), 'big', signed=True)
def l(h, addr): return int.from_bytes(memb(h, addr, 4), 'big')
def sl(h, addr): return int.from_bytes(memb(h, addr, 4), 'big', signed=True)

def hold(h, key, secs=1.5):
    h._xdo('keydown', '--window', h.win, key); time.sleep(secs)

def rel(h, key, secs=0.6):
    h._xdo('keyup', '--window', h.win, key); time.sleep(secs)

def jmode(h):
    h.debug('w $eb76 $ff $ff $00 $00 $00 $00', 0.5)   # $eb76 J, $eb78 K, $eb7a M

def mmode(h):
    h.debug('w $eb76 $00 $00 $00 $00 $ff $ff', 0.5)

def keydown_list(h):
    kd = memb(h, 0x7686, 0x80)
    return [f'{i:02x}' for i, v in enumerate(kd) if v]


def S(h, tag):
    d = memb(h, 0xb9ea0, 32); pj = memb(h, 0xb9ee1, 2)
    print(f'{tag:14s} type={w(h,0x6220):2d} head={w(h,0x6742):4d} thr$6750={sw(h,0x6750):6d} spd$6772={sw(h,0x6772):6d} bank$6746={sw(h,0x6746):6d} '
          f'alt$764c={sw(h,0x764c):6d} $6fbe={w(h,0x6fbe):04x} $6872={w(h,0x6872):04x} yaw={sw(h,0x6766):5d} '
          f'J_ST={d[0]:02x} PADJ={pj[0]:02x} BTN={pj[1]:02x} S={d[20:24].hex()} keys={keydown_list(h)}', flush=True)


def battery(h, seq, secs=2.5):
    """hold each pad key for `secs`, print the state while held and after release; seq items 'key' or 'key:secs'"""
    for k in seq:
        k, _, hs = k.partition(':')
        hs = float(hs) if hs else secs
        if k == 'wait':
            time.sleep(hs); S(h, f'wait {hs}'); continue
        hold(h, k, hs); S(h, f'hold {k}')
        rel(h, k, 1.2); S(h, '  released')


def bus_errors(h):
    return [x for x in h._logtext().splitlines() if 'us error' in x.lower() or 'Bus Error' in x]
