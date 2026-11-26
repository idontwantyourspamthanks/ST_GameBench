"""Deterministic scripted input for the example-campaign playtests: events are chained debugger breakpoints at the loop-top poll ($3dcf4, just before
`jsr $3853a`); an event pokes the game's IKBD cell $38498 (the game's single 'last byte': joystick $01 up $02 down $04 left $08 right $80 fire, i.e. what
the real keys send under --joy1 keys) when the condition on the frog variables holds.  Per flip ($3868e) the frog block + timer + tower words are logged."""
import sys, re, time, json
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/example')
from xlib import *

VARS = dict(x='($33a16).w', y='($33a18).w', st='($33a20).w', stp='($33a1e).w', dirn='($33a1c).w', run='($33938).w', done='($33a46).w', tower='($3390c).w')
def cond_expr(c):
    """'x=$20 & st=0' -> debugger condition on top of pc=$3dcf4"""
    if not c: return ''
    out = []
    for part in c.split('&'):
        m = re.match(r'\s*(\w+)\s*(>=|<=|=|>|<|!=)\s*(\$?[0-9a-fA-F]+)\s*$', part)
        v, op, val = m.groups()
        n = int(val[1:], 16) if val.startswith('$') else int(val)
        if op == '>=': op, n = '>', n - 1
        elif op == '<=': op, n = '<', n + 1
        out.append(f'{VARS[v]} {op} ${n:x}')
    return ' && ' + ' && '.join(out)

def write_chain(d, events):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    for f in d.glob('ev_*.txt'): f.unlink()
    for k, ev in enumerate(events):
        L = ['e VBL', 'w $38498 $%02x' % ev['cell']] + list(ev.get('cmds', []))
        if k + 1 < len(events):
            c = events[k+1].get("cond")
            for cc in (c if isinstance(c, list) else [c]):
                L.append(f'b pc = $3dcf4{cond_expr(cc)} :once :trace :file {d}/ev_{k+1}.txt')
        (d / f'ev_{k}.txt').write_text('\n'.join(L) + '\n')
    (d / 'flip.txt').write_text('m $33a16 16\nm $3ad98 6\nm $3390c 2\nm $33a46 2\nm $77c80 8\n')

def parse(txt):
    """-> list of per-flip dicts"""
    out = []; cur = None; ctx = None
    for line in txt.splitlines():
        if re.match(r'\d+\. CPU breakpoint condition', line): cur = {}; ctx = None; out.append(cur); continue
        if cur is None: continue
        m = re.match(r'> m \$([0-9a-f]+)', line)
        if m: ctx = int(m.group(1), 16); continue
        m = re.match(r'([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)', line)
        if m and ctx is not None:
            cur.setdefault(ctx, bytearray()); cur[ctx] += bytes.fromhex(m.group(2).replace(' ', ''))
    res = []
    for c in out:
        b = c.get(0x33a16); t = c.get(0x3ad98)
        if b is None or len(b) < 16: continue
        w = lambda o: int.from_bytes(b[o:o+2], 'big')
        r = dict(x=w(0), y=w(2), dirn=w(6), stp=w(8), st=w(10), pose=w(12))
        if t and len(t) >= 6: r['t'] = tuple(int.from_bytes(t[i:i+2], 'big') for i in (0, 2, 4))
        if 0x3390c in c: r['tower'] = int.from_bytes(c[0x3390c][:2], 'big')
        if 0x33a46 in c: r['done'] = int.from_bytes(c[0x33a46][:2], 'big')
        if 0x77c80 in c and len(c[0x77c80]) >= 8: r['rs'] = tuple(int.from_bytes(c[0x77c80][i:i+2], 'big') for i in (0, 2, 4, 6))
        res.append(r)
    return res

class Run:
    def __init__(self, snap, wd, game, trainers=('E',), shots=None):
        self.h = Nebulus(snapshot=snap, workdir=wd, game=Path(game))
        self.wd = wd; self.tag = 0
        time.sleep(1.0)
        if 'E' in trainers:
            self.h.debug('w $3792c $4e $75', 0.2); self.h.debug('w $3398c 0 0 0 0 0 0 0 0', 0.2)
        if 'T' in trainers: self.h.debug('w $3b0aa $60', 0.2)
        self.h.debug('b all', 0.2)
    def pokes(self, cmds, wait=0.4):
        self.n = getattr(self, 'n', 0) + 1
        p = Path(self.wd) / f'pk{self.n}.txt'; p.write_text('\n'.join(cmds) + '\n')
        self.h.debug(f'parse {p}', wait)
    def go(self, events, name='r', max_wait=60, tail=2.0, logflips=True):
        """arm the chain, wait for the last event (+tail s), return (flips, text)"""
        d = Path(self.wd) / f'{name}{self.tag}'; self.tag += 1
        write_chain(d, events)
        self.h.debug('b all', 0.2)
        n0 = len(self.h._logtext())
        if logflips: self.h.cmd(f'hatari-debug b pc = $3868e :trace :file {d}/flip.txt'); time.sleep(0.2)
        c0 = events[0].get("cond")
        for cc in (c0 if isinstance(c0, list) else [c0]):
            self.h.cmd(f'hatari-debug b pc = $3dcf4{cond_expr(cc)} :once :trace :file {d}/ev_0.txt'); time.sleep(0.1)
        t0 = time.time(); last = f'{d}/ev_{len(events)-1}.txt'
        while time.time() - t0 < max_wait and f"Reading debugger commands from '{last}'" not in self.h._logtext()[n0:]:
            time.sleep(0.3)
        ok = f"Reading debugger commands from '{last}'" in self.h._logtext()[n0:]
        time.sleep(tail)
        txt = self.h._logtext()[n0:]
        self.h.debug('b all', 0.2)
        return ok, parse(txt), txt
    def close(self): self.h.close()
