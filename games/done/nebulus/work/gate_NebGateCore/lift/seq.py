"""Deterministic scripted ride with per-loop captures (loop = flip index counted by Hatari breakpoint hit counts, no host timing involved).
stage0 (host): arm  b pc=$3dcf4 :1  -> stage1.cmd (executed AT a loop top): lift pokes (+ LIVE patch pokes, + creature spawn on/off), Up at loop UP, release at REL,
and one capture bp per loop  b pc=$3868e :k :once  -> cap_k.cmd:  savebin of both screen buffers, the displayed-buffer pointer $38758, the variable block $33900..$33a4f,
the timer words and the lift column.   usage: seq.py SNAP TAG END EN LIVE|- NLOOPS [machine] [game]"""
import os
from lp import *
SNAP, TAG, END, EN, LIVE, NL = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], int(sys.argv[6])
machine = sys.argv[7] if len(sys.argv) > 7 else 'ste'
game = sys.argv[8] if len(sys.argv) > 8 else '/tmp/gcore_lp/patched'
D = Path('/tmp/gcore_lp/sq_' + TAG)
if D.exists():
    for f in D.glob('*'): f.unlink()
D.mkdir(parents=True, exist_ok=True)
COL = 0x327f0
UP, REL = 3, 7
L = ['w $3ad98 $00 $20 $00 $00 $00 $00', 'w $3b0aa $60', 'w $338fc $00 $00']      # fixed level timer, frozen: the HUD digits must not differ between runs
if LIVE != '-': L += live_cmds(LIVE)
if END: L += [f'w ${COL+1:x} $85'] + [f'w ${COL+r:x} 0' for r in range(2, END)] + [f'w ${COL+END:x} 8']
if EN: L.append('w $3792c ' + ('$30 $39' if game == str(ORIGIN) else '$4e $b9'))
EV = os.environ.get('EV')     # e.g. "3:08,45:00,60:88" = IKBD byte poked at the top of loop N (default: Up at 3, released at 7)
evs = [(int(a), int(b, 16)) for a, b in (x.split(':') for x in EV.split(','))] if EV else [(UP, 1), (REL, 0)]
for i, (lp_, byte) in enumerate(evs):
    L.append(f'b pc = $3dcf4 ' + (f':{lp_} ' if lp_ > 1 else '') + f':once :file {D}/ev{i}.cmd')
    (D / f'ev{i}.cmd').write_text(f'w $38498 ${byte:02x}\n')
if os.environ.get('POKES'):      # extra `w` commands executed at stage1 (separated by ;)
    L += [c.strip() for c in os.environ['POKES'].split(';')]
for k in range(1, NL + 1):
    nxt = f'b pc = $3868e :2 :once :file {D}/cap_{k+1}.cmd\n' if k < NL else ''
    (D / f'cap_{k}.cmd').write_text(f'e {7700+k}\nsavebin {D}/a_{k}.bin $900 $7d00\nsavebin {D}/b_{k}.bin $78000 $7d00\nm $38758 4\nm $33900 336\nm $3ad98 6\nm ${COL:x} 64\ne VBL\n' + nxt)
L.append(f'b pc = $3868e :once :file {D}/cap_1.cmd')
(D / 'stage1.cmd').write_text('\n'.join(L) + '\n')
h = mk(game=game, workdir='/tmp/gcore_lp/w_sq' + TAG, machine=machine, snapshot=SNAP)
try:
    time.sleep(2.0)
    h.debug('b all', 0.3)
    n0 = len(h._logtext())
    h.cmd(f'hatari-debug b pc = $3dcf4 :once :file {D}/stage1.cmd')
    t0 = time.time()
    while time.time() - t0 < 120:
        if (D / f'b_{NL}.bin').exists(): break
        time.sleep(1.0)
    time.sleep(1.5)
    (D / 'log.txt').write_text(h._logtext()[n0:])
finally:
    h.close()
print('caps', len(list(D.glob('b_*.bin'))))
