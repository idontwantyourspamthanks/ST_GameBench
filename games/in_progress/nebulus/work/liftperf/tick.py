"""Tick ($382ba, timer-B chain end) and flip ($3868e) times per VBL: usage tick.py SNAP machine TAG"""
from lp import *
SNAP, machine, TAG = sys.argv[1:4]
D = Path('/tmp/lp/tk_' + TAG); D.mkdir(exist_ok=True)
(D / 't.txt').write_text('e 7711\ne VBL\ne FrameCycles\n'); (D / 'f.txt').write_text('e 7712\ne VBL\ne FrameCycles\n')
h = mk('/tmp/lp/patched', '/tmp/lp/w_tk' + TAG, machine, snapshot=SNAP)
try:
    time.sleep(2.0)
    h.debug('b all', 0.3)
    n0 = len(h._logtext())
    h.cmd(f'hatari-debug b pc = $382ba :trace :file {D}/t.txt'); time.sleep(0.2)
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {D}/f.txt'); time.sleep(6)
    h.debug('b all', 0.3)
    txt = h._logtext()[n0:]
finally:
    h.close()
ev = []; cur = None; n = 0
for line in txt.splitlines():
    m = re.match(r'> e (771[12])$', line)
    if m: cur = ['tick' if m.group(1) == '7711' else 'flip']; ev.append(cur); n = -1; continue
    m = re.match(r'= .*#(\d+) \(dec\)', line)
    if m and cur is not None:
        n += 1
        if n >= 1: cur.append(int(m.group(1)))
print(' '.join(f'{e[0][0]}{e[1]}.{e[2]}' for e in ev[:60] if len(e) >= 3))
