"""Deterministic scripted input v2. Input = poke of the IKBD cell $38498 at the game's loop-top poll ($3dcf4, just before `jsr $3853a`),
keyed on the level timer words $3ad98/9a/9c (they tick once per game loop, so they are a loop counter independent of host timing).
Events are chained (each file arms the next), so only one conditional breakpoint is armed at a time.
Logged per flip (pc=$3868e): variable block $33900..$33a4f + timer words; chosen flips also dump both screens (savebin)."""
import sys, json, time, re
from pathlib import Path
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
W = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input')
SNAP = str(W / 'snap/own_tower.sav')
LIVE = {'none': [], 'jump': ['w $39ffa $60 $2a'], 'hop': ['w $3a024 $4e $71'], 'shoot': ['w $3a332 $4e $71'],
        'jumpshoot': ['w $39ffa $60 $2a', 'w $3a332 $4e $71'], 'jumphop': ['w $39ffa $60 $2a', 'w $3a024 $4e $71'], 'turn': ['w $39e2c $4e $71'], 'shootturn': ['w $3a332 $4e $71', 'w $39e2c $4e $71'], 'all': ['w $39ffa $60 $2a', 'w $3a332 $4e $71', 'w $39e2c $4e $71']}

def parse_flips(txt):
    """-> list of dict(timer=(a,b,c), blk=bytes(336)) per flip in log order."""
    out = []; cur = None; blk = bytearray(); ctx = None
    for line in txt.splitlines():
        if re.match(r'\d+\. CPU breakpoint condition', line):
            if cur is not None: out.append(cur)
            cur = {'blk': bytearray(), 'tm': bytearray(), 'n': line.split('.')[0]}; ctx = None; continue
        if cur is None: continue
        if line.startswith('> m $33900'): ctx = 'blk'; continue
        if line.startswith('> m $3ad98'): ctx = 'tm'; continue
        if line.startswith('> m $38758'): ctx = 'fb'; continue
        if line.startswith('> m $328f0'): ctx = 'g1'; continue
        if line.startswith('> m $329f0'): ctx = 'g2'; continue
        m = re.match(r'([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)', line)
        if m and ctx in ('blk', 'tm'):
            cur[ctx] += bytes.fromhex(m.group(2).replace(' ', ''))
        elif m and ctx in ('g1', 'g2'):
            cur.setdefault(ctx, bytearray()); cur[ctx] += bytes.fromhex(m.group(2).replace(' ', ''))
    if cur is not None: out.append(cur)
    res = []
    for c in out:
        if len(c['blk']) == 336 and len(c['tm']) == 6:
            b = bytes(c['blk']); t = bytes(c['tm'])
            res.append({'timer': tuple(int.from_bytes(t[i:i+2], 'big') for i in (0, 2, 4)), 'blk': b, 'g1': bytes(c.get('g1', b'')), 'g2': bytes(c.get('g2', b''))})
    return res

def write_chain(d, events, caps):
    """events: list of (timer_triple, cellvalue); caps: set of event indexes after whose poll the next flip is dumped."""
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    for k, (tr, val) in enumerate(events):
        extra_cmds = []
        if isinstance(val, tuple): val, extra_cmds = val
        L = ['e VBL', 'w $38498 $%02x' % val] + list(extra_cmds)
        if k in caps:
            L.append(f'b pc = $3868e :once :trace :file {d}/cap_{k}.txt')
            (d / f'cap_{k}.txt').write_text(f'savebin {d}/fb_{k}_a.bin $900 $7d00\nsavebin {d}/fb_{k}_b.bin $78000 $7d00\nm $38758 4\n')
        if k + 1 < len(events):
            a, b, c = events[k + 1][0]
            L.append(f'b pc = $3dcf4 && ($3ad98).w = ${a:x} && ($3ad9a).w = ${b:x} && ($3ad9c).w = ${c:x} :once :trace :file {d}/ev_{k+1}.txt')
        else:
            L.append('e VBL')
        (d / f'ev_{k}.txt').write_text('\n'.join(L) + '\n')
    (d / 'flip.txt').write_text('m $33900 336\nm $3ad98 6\nm $328f0 16\nm $329f0 16\n')

def run(tag, events, caps=(), live='none', duration=14.0, snap=SNAP, game=None, arm_delay=1.0, tail_s=4.0, max_wait=60):
    d = W / 'sc' / tag
    for f in (d.glob('*') if d.exists() else []): f.unlink()
    write_chain(d, events, set(caps))
    kw = {'game': Path(game)} if game else {}
    h = Nebulus(snapshot=snap, workdir='/tmp/strun-nin2s', **kw)
    try:
        time.sleep(arm_delay)
        for c in (LIVE[live] if isinstance(live, str) else live):
            h.debug(c, 0.2)
        h.debug('b all', 0.2)
        h.cmd(f'hatari-debug b pc = $3868e :trace :file {d}/flip.txt'); time.sleep(0.15)
        for pcx in ('$39fc8', '$39ffc', '$3a2f8'):
            h.cmd(f'hatari-debug b pc = {pcx} :trace'); time.sleep(0.15)
        if events:
            a, b, c = events[0][0]
            h.cmd(f'hatari-debug b pc = $3dcf4 && ($3ad98).w = ${a:x} && ($3ad9a).w = ${b:x} && ($3ad9c).w = ${c:x} :once :trace :file {d}/ev_0.txt')
        t0 = time.time()
        if events:
            last = f'{d}/ev_{len(events)-1}.txt'
            while time.time() - t0 < max_wait and f"Reading debugger commands from '{last}'" not in h._logtext():
                time.sleep(0.5)
            time.sleep(tail_s)
        else:
            time.sleep(duration)
        txt = h._logtext()
        (d / 'log.txt').write_text(txt)
    finally:
        h.close()
    return parse_flips(txt), txt

if __name__ == '__main__':
    fl, txt = run('s1', [], duration=9.0)
    print(len(fl), [f['timer'] for f in fl[:5]])
    states = [int.from_bytes(f['blk'][0x33a20-0x33900:][:2], 'big') for f in fl]
    print(states)


def tokens(txt):
    """ordered tokens: 'F' (flip) or the entry name JUMP/JUMPB/SHOOT"""
    names = {'$3868e': 'F', '$39fc8': 'JUMP', '$39ffc': 'JUMPB', '$3a2f8': 'SHOOT'}
    out = []; lines = txt.splitlines()
    for i, l in enumerate(lines):
        if re.match(r'\d+\. CPU breakpoint condition', l) and i + 1 < len(lines):
            m = re.match(r'\s*pc = (\$[0-9a-f]+)', lines[i + 1])
            if m and m.group(1) in names: out.append(names[m.group(1)])
    return out

def build_script(ref, spec):
    """ref: list of flip dicts of a reference run; spec: {flip_index: cell}. -> events [(timer, val)] sorted by flip idx"""
    i0 = next(i for i, f in enumerate(ref) if f['timer'] != (32, 0, 0))     # loop 0 = first flip with the timer ticking
    seen = {}
    for i, f in enumerate(ref):
        seen.setdefault(f['timer'], []).append(i)
    ev = []
    for j in sorted(spec):
        i = i0 + j
        while len(seen[ref[i]['timer']]) != 1:      # triple repeats around the timer's borrow steps: use the next unique loop
            i += 1
        if ev and ev[-1][0] == ref[i]['timer']: ev[-1] = (ev[-1][0], spec[j])
        else: ev.append((ref[i]['timer'], spec[j]))
    return ev
