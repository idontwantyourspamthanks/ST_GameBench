"""Ride trace: restore a tower snapshot, optionally extend lift 1 (col 6) to END_ROW, walk Right to the slab, press Up,
log every pacer entry ($3822c) and flip ($3868e) with VBL, CycleCounter and the player block.  usage: ride.py SNAP TAG END_ROW [machine]"""
from lp import *
import threading
SNAP, TAG, END = sys.argv[1], sys.argv[2], int(sys.argv[3])
machine = sys.argv[4] if len(sys.argv) > 4 else 'ste'
D = Path('/tmp/lp/tr_' + TAG); D.mkdir(parents=True, exist_ok=True)
FL = D / 'flip.txt'; PC = D / 'pace.txt'
COL = 0x327f0 + 6 * 256
FL.write_text('e 7701\ne VBL\ne CycleCounter\nm $33a16 12\nm $3390a 2\nm $3ad98 6\n')
PC.write_text('e 7702\ne VBL\ne CycleCounter\n')
h = mk(game=ORIGIN if 'stock' in SNAP else '/tmp/lp/patched', workdir='/tmp/lp/w_' + TAG, machine=machine, snapshot=SNAP)
try:
    time.sleep(1.5)
    h.debug('w $3792c $4e $75', 0.2); h.debug('w $3398c 0 0 0 0 0 0 0 0', 0.2)   # no enemies (same as trainer E)
    if END > 4:
        pk = [f'w ${COL+4:x} 0'] + [f'w ${COL+r:x} 0' for r in range(5, END)] + [f'w ${COL+END:x} 8']
        for c in pk: h.debug(c, 0.1)
    for c in ('w $32af1 $81', 'w $32bf1 $81'): h.debug(c, 0.1)      # crumble ledge -> normal ledge so the frog can walk to the slab
    time.sleep(0.5)
    h.debug('b all', 0.2)
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {FL}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b pc = $3822c :trace :file {PC}'); time.sleep(0.2)
    n0 = len(h._logtext())
    h._xdo('keydown', '--window', h.win, 'Right')
    t0 = time.time()
    while time.time() - t0 < 12:
        log = h._logtext()[n0:]
        xs = re.findall(r'00033A16:\s+([0-9a-f]{2}) ([0-9a-f]{2})', log, re.I)
        if xs and int(xs[-1][0] + xs[-1][1], 16) >= 0x32: break
        time.sleep(0.15)
    h._xdo('keyup', '--window', h.win, 'Right')
    time.sleep(1.0)
    n1 = len(h._logtext())
    h._xdo('keydown', '--window', h.win, 'Up'); time.sleep(0.4); h._xdo('keyup', '--window', h.win, 'Up')
    # wait for ride end: state back to 0 after having been 6
    t0 = time.time(); seen6 = False
    while time.time() - t0 < 40:
        log = h._logtext()[n1:]
        st = re.findall(r'00033A16:\s+(?:[0-9a-f]{2} ){4}[0-9a-f]{2} [0-9a-f]{2} [0-9a-f]{2} [0-9a-f]{2} [0-9a-f]{2} ([0-9a-f]{2})', log, re.I)
        sts = re.findall(r'00033A16:\s+((?:[0-9a-f]{2} ){12})', log, re.I)
        if sts:
            s = int(''.join(sts[-1].split()[10:12]), 16)
            if s == 6: seen6 = True
            if seen6 and s != 6: break
        time.sleep(0.3)
    time.sleep(1.5)
    h.debug('b all', 0.3)
    txt = h._logtext()[n0:]
    (D / 'log.txt').write_text(txt)
finally:
    h.close()
print('log bytes', len(txt))
