"""Reach measurement: ring (row 1) + a poked test ledge; walk right, jump (fire+right) at x0; per-flip trajectory.  usage: x03_reach.py set1|set2"""
import sys; sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/example')
from drv import *
CB = 10
def cell(c, row, v): return 'w $%x $%02x' % (0x327f0 + c * 256 + row, v)
def clear(cb): return [f'w $%x %s' % (0x327f0 + c * 256, ' '.join(['0'] * 12)) for c in range(cb - 3, cb + 7)]   # rows 0..11 of the columns
def tele(x): return ['w $38498 0', 'w $33a16 %d %d' % (x >> 8, x & 255), 'w $33a18 0 8', 'w $33a20 0 0', 'w $33a1e 0 0']
r = Run('/tmp/neb_ex/old_start.sav', '/tmp/neb_ex/wd3', '/tmp/neb_ex/g_wd1', trainers=('E', 'T'))
out = open(X + 'reach_log.txt', 'a')
def trial(tag, scene, x0, jumpkey=0x88):
    r.pokes(['w $38498 0'] + scene + tele(x0 - 3))
    ok, fl, txt = r.go([dict(cell=0x08), dict(cond='x>=%d&st=0' % x0, cell=jumpkey), dict(cond=['st=0&stp=0&x>%d' % (x0 + 2), 'st>=7'], cell=0x00)], max_wait=25, tail=0.3)
    i0 = next((i for i, f in enumerate(fl) if f['st'] == 1), None)
    path = [(f['x'], f['y'], f['st']) for f in fl[i0 - 1:i0 + 22]] if i0 else []
    last = fl[-1] if fl else None
    line = f"{tag} x0={x0} ok={ok} final={(last['x'], last['y'], last['st']) if last else None} path={path}"
    print(line, flush=True); out.write(line + '\n'); out.flush()
def trial_hold(tag, scene, x0, ycond):
    r.pokes(['w $38498 0'] + scene + tele(x0))
    ok, fl, txt = r.go([dict(cell=0x88), dict(cond=ycond, cell=0x00)], max_wait=40, tail=0.3)
    ys = [(f['x'], f['y'], f['st']) for f in fl]
    line = f"{tag} x0={x0} ok={ok} nflips={len(fl)} final={ys[-1] if ys else None} path={ys[::3]}"
    print(line, flush=True); out.write(line + '\n'); out.flush()
try:
    ring = [cell(c, 1, 0x81) for c in range(16)]
    if sys.argv[1] == 'set1':       # height: ring row 1 + ledge B (4 wide) at row 1+h, left column 10 (supports x 81..112)
        for h in (1, 2, 3):
            for x0 in range(64, 82, 2):
                trial(f'S1 h={h}', clear(CB) + ring + [cell(c, 1 + h, 0x81) for c in range(CB, CB + 4)], x0)
    if sys.argv[1] == 'set1b':      # human style: hold right+fire from afar (and from the wall) until standing on the ledge
        for h in (1, 2):
            for x0 in (40, 60, 70, 77):
                trial_hold(f'S1b h={h}', clear(CB) + ring + [cell(c, 1 + h, 0x81) for c in range(CB, CB + 4)], x0, 'st=0&y>=%d' % (4 * h + 8))
    if sys.argv[1] == 'set3':       # fire pressed at the wall (state 0, x = 77): h=2 and h=3
        for h in (2, 3):
            for k in range(3):
                trial(f'S3 wall h={h} try{k}', clear(CB) + ring + [cell(c, 1 + h, 0x81) for c in range(CB, CB + 4)], 77 if k == 0 else 70 + 3 * k)
    if sys.argv[1] == 'set2':       # gap: A = ring up to column 9, B = ledge ring row 1+h at columns 11..14, column 10 empty, catch ledge at row 0
        for h in (0, 1, 2):
            for x0 in range(66, 80, 1):
                scene = clear(CB) + ring + [cell(CB, 1, 0), cell(CB, 0, 0x81)] + [cell(c, 1 + h, 0x81) for c in range(CB + 1, CB + 5)]
                if h: scene += [cell(c, 1, 0) for c in range(CB + 1, CB + 5)]
                trial(f'S2 h={h}', scene, x0)
finally: r.close()
