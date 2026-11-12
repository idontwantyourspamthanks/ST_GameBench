"""Shared helpers for the MW1 Jaguar-pad tests (see work/notes/jagpad.md)."""
import json, re, sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools']
from pathlib import Path
from mw1 import MW1, SNAP, TOS   # noqa

GAME = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter')
HERE = GAME / 'work' / 'jagpad'
PAD = ['--joy1', 'keys', '--configfile', str(HERE / 'pad.cfg')]
FLIP = 0xBD9A
# pad button -> host key (pad.cfg)
KEY = dict(up='w', down='s', left='a', right='d', sup='Up', sdown='Down', sleft='Left', sright='Right', sfire='Control_R', A='z', B='x', C='v', opt='o', pause='p',
           n1='1', n2='2', n3='3', star='F5', hash='F6')


def kd(h, k): h._xdo('keydown', '--window', h.win, KEY.get(k, k))
def ku(h, k): h._xdo('keyup', '--window', h.win, KEY.get(k, k))


def s16(v): return v - 0x10000 if v & 0x8000 else v
def s32(v): return v - (1 << 32) if v & 0x80000000 else v


class Sampler:
    """One debugger `parse` file per sample: VBL + a list of (addr, len) peeks."""
    n_inst = 0

    def __init__(self, h, items):
        self.h, self.items = h, items
        Sampler.n_inst += 1
        self.f = h.R / f'sample{Sampler.n_inst}.txt'
        self.f.write_text('e VBL\n' + ''.join(f'm ${a:x} {n}\n' for a, n in items))

    def __call__(self):
        for _ in range(6):
            r = self._once()
            if r is not None:
                return r
        raise RuntimeError('sampler: incomplete debugger output:\n' + self.last[-1500:])

    def _once(self):
        h = self.h
        n = len(h._logtext())
        h.cmd(f'hatari-debug parse {self.f}')
        want = sum((n_ + 15) // 16 + (1 if (a % 16) + n_ > 16 and False else 0) for a, n_ in self.items)
        for _ in range(120):
            time.sleep(0.05)
            out = h._logtext()[n:]
            if len(re.findall(r'^[0-9A-F]{8}: ', out, re.M)) >= want and re.search(r'#\d+ \(dec\)', out):
                break
        time.sleep(0.05)
        out = h._logtext()[n:]
        vbl = int(re.findall(r'#(\d+) \(dec\)', out)[-1])
        mem = {}
        for a, b in re.findall(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', out, re.M):
            a = int(a, 16)
            for i, x in enumerate(b.split()):
                mem[a + i] = int(x, 16)
        if any(a + i not in mem for a, n_ in self.items for i in range(n_)):
            self.last = out
            return None
        res = {'vbl': vbl}
        for a, n_ in self.items:
            res[a] = bytes(mem.get(a + i, 0) for i in range(n_))
        return res


def apply_live(h, live, pokes=()):
    """Apply a `mw1patch.py live` set at the next flip (never while the CPU is mid-routine)."""
    spec = json.loads(Path(live + '.json').read_text())
    cmds = [f"loadbin {Path(live + '.img')} ${spec['img_base']:x}"]
    for s in spec['sites']:
        raw = bytes.fromhex(s['new'])
        for o in range(0, len(raw), 40):
            cmds.append(f"w ${s['addr'] + o:x} " + ' '.join(f'${b:02x}' for b in raw[o:o + 40]))
    cmds += list(pokes)
    app = h.R / 'apply.txt'
    app.write_text('\n'.join(cmds) + '\n')
    h.debug('b all', 0.3)
    n = len(h._logtext())
    h.cmd(f'hatari-debug b pc = ${FLIP:x} :trace :once :file {app}')
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[n:]:
        if time.time() - t > 120:
            raise TimeoutError('apply bp never fired')
        time.sleep(0.3)
    time.sleep(0.5)


def blob_cost(h, vbls=100, lo=0xb6900, hi=0xb6c40):
    """Hatari `profile cycles` over `vbls` VBLs: (cycles per VBL spent in [lo,hi), share of all profiled cycles, per-address list)."""
    prof = h.profile(vbls, top=40000)
    tot = sum(c for _, c in prof)
    mine = [(a, c) for a, c in prof if lo <= a < hi]
    s = sum(c for _, c in mine)
    return s / vbls, 100.0 * s / tot if tot else 0.0, mine, tot / vbls
