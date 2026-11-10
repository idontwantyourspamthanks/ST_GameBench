"""MW2VehAir scratch harness (analyst; never touches patches/).
mklive(name, only): build live set from work/vehair/patches (scratch copy) -> work/vehair/live/<name>.{img,json}
trace(snap, live, pokes, cond, nrows, tag, dumps): restore snapshot, at a flip apply live+pokes, log dumps at every hit of cond.
"""
import sys, re, time, json, subprocess, os
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
W = ROOT / 'work' / 'vehair'
OUT = W / 'out'; OUT.mkdir(exist_ok=True)

def setmask(mask, patchdir=W / 'patches'):
    f = Path(patchdir) / 'p3b_head.s'
    t = f.read_text()
    t = re.sub(r'^MASK    equ     \$[0-9a-f]+', 'MASK    equ     $%x' % mask, t, flags=re.M)
    f.write_text(t)

def mklive(name, only, patchdir=W / 'patches'):
    import importlib, mw2patch as m
    m.PATCHDIR = Path(patchdir)
    ps = m.load_patches()
    sel = [p for p in ps if p.name in set(only)]
    assert len(sel) == len(set(only)), set(only) - {p.name for p in ps}
    m.cmd_live(sel, W / 'live' / name)
    return str(W / 'live' / name)

# memory regions dumped per sample (address -> bytes)
REG = [(0x6740, 0x40), (0x7640, 0x50), (0x66e0, 0x20), (0x6290, 0x10), (0xeb8c, 4), (0x34936, 6),
       (0x6fb6, 12), (0x6220, 2), (0xb42e0, 32), (0x688e, 8), (0x6888, 4), (0x18102, 2), (0x674e, 2), (0xf984, 4), (0xefb2, 8), (0x40b6, 2)]
DUMPS = [f"m ${a:x} {n}" for a, n in REG]

def parse(txt):
    """rows of {addr: byte}; a row ends when an address is dumped twice"""
    rows = []; cur = {}; seen = set()
    for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)', txt, re.M | re.I):
        a = int(m.group(1), 16)
        if a == 0x6740 and cur:
            rows.append(cur); cur = {}
        b = bytes.fromhex(m.group(2).replace(' ', ''))
        for i, x in enumerate(b): cur[a + i] = x
    if cur: rows.append(cur)
    return rows

class S:
    def __init__(self, mem): self.m = mem
    def w(self, a): return (self.m[a] << 8) | self.m[a + 1]
    def sw(self, a): v = self.w(a); return v - 65536 if v & 0x8000 else v
    def l(self, a): return (self.w(a) << 16) | self.w(a + 2)
    def sl(self, a): v = self.l(a); return v - (1 << 32) if v & (1 << 31) else v

def trace(snap, live, pokes, cond, nrows, tag, dumps=DUMPS, timeout=1200, extra_after=(), settle=3):
    h = Hatari(snapshot=str(snap), memsize_kb=2048)
    try:
        R = h.R
        hit = R / 'hit.txt'; hit.write_text("\n".join(dumps) + "\n")
        cmds = []
        if live:
            spec = json.loads(Path(live + '.json').read_text())
            cmds.append(f"loadbin {live}.img ${spec['img_base']:x}")
            for s in spec['sites']:
                new = bytes.fromhex(s['new'])
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in new))
        cmds += list(pokes)
        cmds += list(dumps)          # row 0 = state at apply instant
        cmds.append(f"b {cond} :trace :file {hit}")
        app = R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
        v = h.vbl()
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {v + settle} && pc = $26e98 :trace :once :file {app}")
        t = time.time()
        while True:
            txt = h._logtext()[start:]
            n = len(re.findall(r'^00006740:', txt, re.M | re.I))
            if n >= nrows + 1: break
            if time.time() - t > timeout: raise TimeoutError(txt[-1500:])
            time.sleep(0.5)
        h.debug("b all", 0.5)
        txt = h._logtext()[start:]
        (OUT / f'{tag}.log').write_text(txt)
        return [S(r) for r in parse(txt)]
    finally:
        h.close()
