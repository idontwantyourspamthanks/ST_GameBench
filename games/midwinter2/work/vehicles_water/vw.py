"""Water-vehicle p3b experiments: shared Hatari helpers (analyst scratch; never edits patches/)."""
import sys, re, time, json, pickle, subprocess
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
import os
ABS_VBL = int(os.environ.get("VW_ABS", "154250"))
OUT = ROOT / 'work/vehicles_water'
SNAP = ROOT / 'work/snapshots'

# memory blocks sampled per hit: (addr, len)
BLOCKS = [(0x6740, 64), (0x66e0, 32), (0x6280, 32), (0x7640, 64), (0x7680, 16), (0x6880, 32),
          (0xeb8c, 4), (0xf984, 4), (0xefb0, 16), (0x34930, 16), (0x6fb6, 16), (0x6220, 2), (0xb42e0, 32), (0x6770, 16), (0x6900, 16), (0x18770, 16), (0x3532, 600), (0x66b8, 16)]

def dumps():
    return [f"m ${a:x} {n}" for a, n in BLOCKS]

class Mem(dict):
    def b(self, a, n):
        return bytes(self[a + i] for i in range(n))
    def w(self, a):
        return int.from_bytes(self.b(a, 2), 'big')
    def sw(self, a):
        return int.from_bytes(self.b(a, 2), 'big', signed=True)
    def l(self, a):
        return int.from_bytes(self.b(a, 4), 'big', signed=True)

def parse(txt):
    """rows: one Mem per sample (a new row starts when the first block address repeats)."""
    rows = []; cur = Mem()
    first = BLOCKS[0][0]
    for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)', txt, re.M | re.I):
        a = int(m.group(1), 16); bs = bytes.fromhex(m.group(2).replace(' ', ''))
        if a == first and cur:
            rows.append(cur); cur = Mem()
        for i, x in enumerate(bs):
            cur[a + i] = x
    if cur: rows.append(cur)
    return rows

def live_build(name, patchdir, only):
    """Assemble a scratch patch set from `patchdir` (own copies) into /tmp/vw/<name>.{img,json}."""
    import importlib
    sys.path.insert(0, str(ROOT / 'tools'))
    code = f"""
import sys; sys.path.insert(0,'{ROOT}/tools')
import mw2patch as m
from pathlib import Path
m.PATCHDIR = Path('{patchdir}')
ps = [p for p in m.load_patches() if p.name in {only!r}]
assert {{p.name for p in ps}} == set({only!r}), ({{p.name for p in ps}})
m.cmd_live(ps, Path('/tmp/vw/{name}'))
"""
    Path('/tmp/vw').mkdir(exist_ok=True)
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=ROOT)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return f'/tmp/vw/{name}'

def apply_cmds(live):
    spec = json.loads(Path(live + '.json').read_text())
    c = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s['new'])) for s in spec['sites']]
    return c

def wb(addr, val, n):
    return f"w ${addr:x} " + " ".join(f"${b:02x}" for b in (val & ((1 << 8 * n) - 1)).to_bytes(n, 'big'))

def run(snap, tag, nhits, live=None, pokes=(), sample='pc = $3158c', timeout=1500, vbl_after=3, keep=True):
    h = Hatari(snapshot=str(snap), memsize_kb=2048)
    try:
        R = h.R
        hit = R / 'hit.txt'; hit.write_text("\n".join(dumps()) + "\n")
        cmds = []
        if live: cmds += apply_cmds(live)
        cmds += list(pokes)
        cmds += dumps()                       # row 0: state at the apply instant
        cmds.append(f"b {sample} :trace :file {hit}")
        app = R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
        v = h.vbl()
        assert v < ABS_VBL - 20, v
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {ABS_VBL} && pc = $26e98 :trace :once :file {app}")
        t = time.time()
        first = f'{BLOCKS[0][0]:08X}:'
        while True:
            txt = h._logtext()[start:]
            n = len(re.findall('^' + first, txt, re.M | re.I))
            if n >= nhits + 1: break
            if time.time() - t > timeout: raise TimeoutError(txt[-1500:])
            time.sleep(0.5)
        h.debug("b all", 0.5)
        txt = h._logtext()[start:]
        (OUT / 'logs').mkdir(exist_ok=True)
        (OUT / 'logs' / f'{tag}.log').write_text(txt)
        return parse(txt)
    finally:
        h.close()
