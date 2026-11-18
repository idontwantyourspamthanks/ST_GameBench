import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
SNAP = '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/snapshots/1mb_tower.sav'

EV = {  # name -> condition
    'VBL':   'pc = $382d8',
    'POLL':  'pc = $3853a',
    'FLIP':  'pc = $3868e',
    'CONS':  'pc = $3e188',
    'ACIA':  'pc = $384fc',
    'STORE': 'pc = $38514',
}

def arm(h, names, extra=()):
    h.debug('b all', 0.3)
    order = []
    (h.R / 'r.txt').write_text('r\n')
    for n in names:
        f = f' :file {h.R / "r.txt"}' if n == 'STORE' else ''
        h.cmd(f'hatari-debug b {EV[n]} :trace{f}'); order.append(n); time.sleep(0.15)
    for n, cond in extra:
        h.cmd(f'hatari-debug b {cond} :trace'); order.append(n); time.sleep(0.15)
    return order

def parse(text, order):
    ev = []
    for m in re.finditer(r'(\d+)\. CPU breakpoint condition\(s\) matched (\d+) times\.', text):
        i = int(m.group(1)) - 1
        if 0 <= i < len(order):
            ev.append(order[i])
    return ev

def window(h, names, vbls, extra=()):
    """Trace the named events over `vbls` VBLs; return the event list."""
    order = arm(h, names, extra)
    time.sleep(0.2)
    start = h._arm_vbl(vbls)
    out = h._wait_removed(start)
    h.debug('b all', 0.3)
    return parse(out, order + ['__vblstop'])
