"""Cycle-timestamped event tracer for the Nebulus input path (Hatari debugger traces).
Events carry (vbl, FrameCycles). Time axis: T = vbl*FPC + FrameCycles (FPC = cycles per frame at the CPU clock)."""
import sys, json, random, statistics, time, re
from lib import Nebulus, SNAP
EV = {'VBL': 'pc = $382d8', 'TICK': 'pc = $382c0', 'WAIT': 'pc = $3868a', 'FLIP': 'pc = $3868e',
      'POLL': 'pc = $3853a', 'CONS': 'pc = $3e188', 'ACIA': 'pc = $384fc', 'STORE': 'pc = $38514'}
EXTRA_CMD = {'STORE': 'r\n', 'FLIP': 'm $33a16 14\nm $33994 2\n'}
NAMES = ['VBL', 'TICK', 'WAIT', 'POLL', 'CONS', 'ACIA', 'STORE', 'FLIP']
FPC8 = 160256

def arm(h, names, extra=()):
    h.debug('b all', 0.3)
    order = []
    for n in names:
        f = h.R / f'ev_{n}.txt'
        f.write_text('e VBL\ne FrameCycles\n' + EXTRA_CMD.get(n, ''))
        h.cmd(f'hatari-debug b {EV[n]} :trace :file {f}'); order.append(n); time.sleep(0.15)
    for n, c in extra:
        f = h.R / f'ev_{n}.txt'; f.write_text('e VBL\ne FrameCycles\n')
        h.cmd(f'hatari-debug b {c} :trace :file {f}'); order.append(n); time.sleep(0.15)
    time.sleep(0.2)
    return order

def marker(h):
    h.cmd('hatari-debug e VBL + 0'); h.cmd('hatari-debug e FrameCycles + 0')

def parse(txt, order, fpc):
    evs = []; cur = None; ctx = None
    for line in txt.splitlines():
        m = re.match(r'(\d+)\. CPU breakpoint condition', line)
        if m:
            i = int(m.group(1)) - 1
            cur = {'n': order[i] if i < len(order) else '?'}; evs.append(cur); ctx = None; continue
        if line.startswith('> '):
            c = line[2:].strip()
            if c == 'e VBL + 0':
                cur = {'n': 'M'}; evs.append(cur); ctx = 'vbl'
            elif c == 'e FrameCycles + 0':
                ctx = 'fc'        # applies to the most recent marker
                cur = next((e for e in reversed(evs) if e['n'] == 'M'), None)
            elif c == 'e VBL': ctx = 'vbl'
            elif c == 'e FrameCycles': ctx = 'fc'
            elif c == 'r': ctx = 'r'
            elif c.startswith('m '): ctx = 'm'
            else: ctx = None
            continue
        if line.startswith('= '):
            v = int(re.search(r'#(\d+) \(dec\)', line).group(1))
            if ctx == 'vbl' and cur is not None and 'vbl' not in cur: cur['vbl'] = v
            elif ctx == 'fc' and cur is not None and 'fc' not in cur: cur['fc'] = v
            continue
        if ctx == 'r' and line.lstrip().startswith('D0 ') and cur is not None:
            cur['d0'] = int(line.split()[1], 16) & 0xff
        if ctx == 'm' and cur is not None:
            m2 = re.match(r'00033994:\s+([0-9a-f]{2}) ([0-9a-f]{2})', line, re.I)
            if m2 and 'st' in cur: cur['st']['shot'] = int(m2.group(1) + m2.group(2), 16)
            mm = re.match(r'00033A16:\s+((?:[0-9a-f]{2} )+)', line, re.I)
            if mm:
                b = bytes.fromhex(mm.group(1).replace(' ', ''))
                w = [int.from_bytes(b[i:i + 2], 'big') for i in range(0, 14, 2)]
                cur['st'] = dict(x=w[0], y=w[1], face=w[3], step=w[4], state=w[5], pose=w[6])
    return [e for e in evs if 'vbl' in e and 'fc' in e]

def capture(h, actions, names=NAMES, extra=(), tail=0.9, fpc=FPC8):
    """actions: list of (host_sleep, 'down'|'up', key). Markers: before each action and after (M0 start, then after each)."""
    order = arm(h, names, extra)
    n0 = len(h._logtext())
    marker(h)
    for dt, op, key in actions:
        time.sleep(dt)
        h._xdo('key' + op, '--window', h.win, key)
        marker(h)
    time.sleep(tail)
    marker(h); time.sleep(0.4)
    txt = h._logtext()[n0:]
    h.debug('b all', 0.3)
    return parse(txt, order, fpc)
