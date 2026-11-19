"""Shared helpers for the input-stall investigation (NebInputStall). Own workdirs only (/tmp/strun-ikbd-*)."""
import sys, time, re, os
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus, TOS
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus')
B = G/'work/ikbd/build'

def boot(variant, tag, extra=None, snapshot=None, **kw):
    return Nebulus(game=B/variant, workdir=(f'/tmp/strun-ikbd-{tag}' if tag else '/tmp/strun-ikbd'), extra=extra, snapshot=snapshot, **kw)

def wait_log(h, pat, start=0, timeout=120, step=0.01):
    """Poll the Hatari log for regex `pat` (from offset `start`); return (match, log_len_at_hit)."""
    t0 = time.time()
    rx = re.compile(pat)
    while time.time() - t0 < timeout:
        txt = h.logpath.read_text(errors='replace')
        m = rx.search(txt, start)
        if m:
            return m, len(txt)
        time.sleep(step)
    return None, len(txt)

def rd(h, a, n, wait=0.5):
    out = h.debug(f'm ${a:x} {n}', wait)
    rows = re.findall(rf'^{a:08x}:\s+((?:[0-9a-f]{{2}} ?)+)', out, re.I | re.M)
    return bytes.fromhex(''.join(rows[-1].split())) if rows else None

def tap(h, keysym='space', hold=0.08):
    if keysym == 'MOUSE':          # a few relative mouse moves (3-byte IKBD packets each)
        for dx, dy in ((14, 9), (-14, -9), (10, 0), (-10, 0)):
            h._xdo('mousemove_relative', '--', str(dx), str(dy)); time.sleep(0.03)
        return
    h._xdo('keydown', '--window', h.win, keysym); time.sleep(hold); h._xdo('keyup', '--window', h.win, keysym)

def acia(h):
    b = rd(h, 0xfffc00, 2)
    return b[0] if b else None

def probe(h, keysym='a', hold=0.3):
    """Is the game's IKBD handler ($384fc) still being invoked? Press+release KEYSYM and count ISR entries via a trace breakpoint.
    (The debugger's `m $fffc00` shows the LAST SR value a CPU read stored in IoMem, NOT the live ACIA status: do not use it.)"""
    h.debug('b all', 0.3)
    n0 = len(h._logtext())
    h.cmd('hatari-debug b pc = $384fc :trace')
    time.sleep(0.3)
    h._xdo('keydown', '--window', h.win, keysym); time.sleep(hold)
    h._xdo('keyup', '--window', h.win, keysym); time.sleep(0.5)
    h.debug('b all', 0.3)
    txt = h._logtext()[n0:]
    return len(re.findall(r'pc = \$384fc', txt)) // 1 if False else len(re.findall(r'CPU breakpoint condition\(s\) matched', txt))
