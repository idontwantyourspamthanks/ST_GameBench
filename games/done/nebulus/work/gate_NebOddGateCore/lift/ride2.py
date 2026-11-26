import os
"""Ride in column 0 straight from the tower start (frog stands at x=4,y=8 on the row-1 ledge): poke the row-1 cell to the lift slab $85,
clear the shaft, put the end marker $08 at END; hold Up 0.4 s; log pacer entry/flip.  usage: ride2.py SNAP TAG END_ROW [en=0|1] [machine] [game]"""
from lp import *
SNAP, TAG, END = sys.argv[1], sys.argv[2], int(sys.argv[3])
EN = int(sys.argv[4]) if len(sys.argv) > 4 else 0
machine = sys.argv[5] if len(sys.argv) > 5 else 'ste'
game = sys.argv[6] if len(sys.argv) > 6 else ('/tmp/oddcore/lp/patched' if 'stock' not in SNAP else str(ORIGIN))
D = Path('/tmp/oddcore/lp/tr_' + TAG); D.mkdir(parents=True, exist_ok=True)
FL = D / 'flip.txt'; PC = D / 'pace.txt'
COL = 0x327f0
FL.write_text('e 7701\ne VBL\ne CycleCounter\nm $33a16 12\nm $3390a 2\nm $3ad98 6\nm $338fe 2\n')
PC.write_text('e 7702\ne VBL\ne CycleCounter\n')
h = mk(game=game, workdir='/tmp/oddcore/lp/w_' + TAG, machine=machine, snapshot=SNAP)
try:
    time.sleep(1.5)
    if os.environ.get('LIVE'):
        for c in live_cmds(os.environ['LIVE']): h.debug(c, 0.1)
    if END:
        h.debug(f'w ${COL+1:x} $85', 0.1)
        for r in range(2, END): h.debug(f'w ${COL+r:x} 0', 0.1)
        h.debug(f'w ${COL+END:x} 8', 0.1)
    h.debug('b all', 0.2)
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {FL}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b pc = $3822c :trace :file {PC}'); time.sleep(0.2)
    if EN:
        h.debug('w $3792c ' + ('$30 $39' if 'stock' in str(game) or game == str(ORIGIN) else '$4e $b9'), 0.2)   # undo the snapshot's spawn-rts
    if os.environ.get('NOSTEM'):
        # when the frog has arrived at the top (state 0, y > 95) clear the stem cells (shaft rows 2..END-1) in ONE debugger command file; the 3 loops marker `e 7703` shows where
        pk = D / 'nostem.cmd'
        pk.write_text('e 7703\n' + ''.join(f'w ${COL+r:x} 0\n' for r in range(2, END)))
        h.cmd(f'hatari-debug b pc = $3dcf4 && ($33a20).w = 0 && ($33a18).w > {4*END-5} :once :file {pk}'); time.sleep(0.2)
    n0 = len(h._logtext())
    time.sleep(float(os.environ.get('PRE','2.5')))
    n1 = len(h._logtext())
    if END:
        h._xdo('keydown', '--window', h.win, 'Up'); time.sleep(0.4); h._xdo('keyup', '--window', h.win, 'Up')
    t0 = time.time(); seen6 = False
    while time.time() - t0 < 60:
        log = h._logtext()[n1:]
        sts = re.findall(r'00033A16:\s+((?:[0-9a-f]{2} ){12})', log, re.I)
        if sts:
            s = int(''.join(sts[-1].split()[10:12]), 16)
            if s == 6: seen6 = True
            if seen6 and s != 6: break
        if not END and time.time() - t0 > 8: break
        time.sleep(0.3)
    time.sleep(2.0)
    h.debug('b all', 0.3)
    txt = h._logtext()[n0:]
    (D / 'log.txt').write_text(txt)
finally:
    h.close()
print('log bytes', len(txt))
