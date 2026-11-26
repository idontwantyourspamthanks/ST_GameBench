"""Lift-ride performance harness (NebLiftPerf).  Helpers shared by the experiment scripts."""
import sys, time, re, json
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus, TOS, ORIGIN
HERE = Path(__file__).resolve().parent
NEB = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus')

def mk(game, workdir, machine='ste', snapshot=None):
    kw = dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096) if machine == 'megaste' else {}
    return Nebulus(game=Path(game), workdir=workdir, snapshot=snapshot, **kw)

def boot_tower(h, machine='ste'):
    if machine != 'megaste':
        return h.boot_to_game()
    t0 = time.time(); ok = False
    while time.time() - t0 < 300:
        time.sleep(2)
        if h._marker_present(): ok = True; break
        if time.time() - t0 > 25: h.keypress(57)
    if not ok: return False
    time.sleep(2.0); h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(4.0)
    return bool(h.peekw(h.TIMER))

def spawn_restore(game):
    """bytes to write back at $3792c: the jsr of nt_trainers when the build has that hook, else the original move.w"""
    import json
    try: d = json.load(open(str(game).rstrip('/') + '.json'))
    except Exception: return '$30 $39'
    return '$4e $b9' if any(s['addr'] == 0x3792c for s in d['sites']) else '$30 $39'

def rd(h, a, n):
    out = h.debug(f'm ${a:x} {n}', 0.6)
    rows = re.findall(r'^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} ?)+)', out, re.M | re.I)
    b = bytearray()
    for ad, hx in rows: b += bytes.fromhex(hx.replace(' ', ''))
    return bytes(b[:n])
def w16(h, a): return int.from_bytes(rd(h, a, 2), 'big')

def live_cmds(only):
    """`w` debugger commands (chunked to 24 bytes) for the named patches of tools/nepatch.py (live patching of a restored snapshot)."""
    import subprocess
    out = []
    for c in subprocess.run(['python3', str(NEB / 'tools/nepatch.py'), 'live', '--only'] + only.split(), capture_output=True, text=True).stdout.splitlines():
        if not c.startswith('w '): continue
        p = c.split(); a = int(p[1][1:], 16); bs = p[2:]
        for i in range(0, len(bs), 24):
            out.append(f'w ${a+i:x} ' + ' '.join(bs[i:i+24]))
    out.sort(key=lambda c: -int(c.split()[1][1:], 16))      # blobs (high RAM) before the hook sites that jump into them
    return out
