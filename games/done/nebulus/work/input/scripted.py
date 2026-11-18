"""Deterministic scripted-input runs. Input = poke of the IKBD cell $38498 at the entry of the game's poll (sub_03853a) as a pure function of the
poll index (game-loop index); anchored at the first poll with player state 0 and timer $3ad98 = $20 (level start).  Breakpoints come from a
--parse file so they are armed before the restored emulation runs (no host-timing dependence).
Per flip (pc=$3868e) the game variable block $33900..$33a4f and the timer words are logged; chosen flips also dump both screens."""
import sys, json, time, re
from pathlib import Path
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
W = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input')
LIVE = {   # live equivalents of the .nep sites (bytes for the debugger `w`)
    'none': [],
    'jump': ['w $39ffa $60 $2a', 'w $3a024 $4e $71'],
    'shoot': ['w $3a332 $4e $71'],
}
def write_files(d, script, caps, nloops, live):
    """script: {loop_index: cellvalue}; caps: set of loop indexes whose following flip is dumped. Returns parse-file path."""
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    idx = sorted(set(script) | set(caps) | {0, nloops})
    for n, i in enumerate(idx):
        lines = [f'e VBL', 'e FrameCycles']
        if i in script: lines.append('w $38498 $%02x' % script[i])
        if i in caps:
            lines.append(f'b pc = $3868e :once :trace :file {d}/cap_{i}.txt')
            (d / f'cap_{i}.txt').write_text(f'savebin {d}/fb_{i}_a.bin $900 $7d00\nsavebin {d}/fb_{i}_b.bin $78000 $7d00\nm $38758 4\ne VBL\n')
        if n + 1 < len(idx):
            lines.append(f'b pc = $3853a :{idx[n+1]-i} :once :trace :file {d}/ev_{idx[n+1]}.txt')
        else:
            lines.append('b VBL > 0 && pc = $3868e :once :trace :file %s/stop.txt' % d)
        (d / f'ev_{i}.txt').write_text('\n'.join(lines) + '\n')
    (d / 'stop.txt').write_text('e VBL\n')
    (d / 'flip.txt').write_text('m $33900 336\nm $3ad98 6\n')
    (d / 'poll.txt').write_text('e VBL\n')
    parse = d / 'start.txt'
    cmds = list(live) + [
        f'b pc = $3868e :trace :file {d}/flip.txt',
        f'b pc = $3853a && ($33a20).w = 0 && ($3ad98).w = $20 :once :trace :file {d}/ev_0.txt',
    ]
    parse.write_text('\n'.join(cmds) + '\n')
    return parse

def run(tag, snap, script, caps, nloops, live='none', machine_extra=None, timeout=150, game=None):
    d = W / 'sc' / tag
    for f in (d.glob('*') if d.exists() else []): f.unlink()
    write_files(d, script, caps, nloops, [])
    kw = {'game': Path(game)} if game else {}
    h = Nebulus(snapshot=snap, workdir='/tmp/strun-nin2s', extra=machine_extra, **kw)
    try:
        time.sleep(1.0)
        for c in (LIVE[live] if isinstance(live, str) else live):
            h.debug(c, 0.3)
        h.debug('b all', 0.3)
        h.cmd(f'hatari-debug b pc = $3868e :trace :file {d}/flip.txt'); time.sleep(0.2)
        h.cmd(f'hatari-debug b pc = $3853a && ($33a20).w = 0 && ($3ad98).w = $20 :once :trace :file {d}/ev_0.txt'); time.sleep(0.3)
        h.key('Right', hold=0.5); time.sleep(0.3); h.key('Control_R', hold=0.6)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if (d / 'stop_seen').exists(): break
            t = h._logtext()
            if f'{d}/stop.txt' in t and t.count('Reading debugger commands from') and re.search(r'stop\.txt\' file on hit', t) and 'Removed CPU breakpoint' in t[t.rfind(f'{d}/stop.txt'):]:
                break
            time.sleep(1)
        time.sleep(1.0)
        txt = h._logtext()
        (d / 'log.txt').write_text(txt)
    finally:
        h.close()
    return txt

if __name__ == '__main__':
    # smoke: no input, 12 loops
    txt = run('smoke', '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/snapshots/hiscores.sav', {}, {3}, 12)
    print(txt[-1500:])
