"""Hatari profile of the ride (state 6 .. frog at the top) or of an equal-length standing window.
usage: prof_ride.py SNAP TAG END_ROW EN mode(ride|stand) [machine]   -> /tmp/lp/prof_TAG.txt, ram_TAG.bin"""
import os
from lp import *
SNAP, TAG, END, EN, MODE = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
machine = sys.argv[6] if len(sys.argv) > 6 else 'ste'
game = '/tmp/lp/patched' if 'stock' not in SNAP else str(ORIGIN)
if os.environ.get('GAME'): game = os.environ['GAME']
D = Path('/tmp/lp'); prof = D / f'prof_{TAG}.txt'
if prof.exists(): prof.unlink()
(D / f'on_{TAG}.cmd').write_text('profile on\n'); (D / f'save_{TAG}.cmd').write_text(f'profile save {prof}\n')
h = mk(game=game, workdir='/tmp/lp/w_p' + TAG, machine=machine, snapshot=SNAP)
COL = 0x327f0
try:
    time.sleep(2.0)
    if not EN:
        pass
    if os.environ.get('LIVE'):
        for c in live_cmds(os.environ['LIVE']): h.debug(c, 0.1)
    h.debug(f'w ${COL+1:x} $85', 0.1)
    for r in range(2, END): h.debug(f'w ${COL+r:x} 0', 0.1)
    h.debug(f'w ${COL+END:x} 8', 0.1)
    h.dump(str(D / f'ram_{TAG}.bin'), 0, 0x100000)
    if EN: h.debug('w $3792c ' + ('$30 $39' if 'stock' in str(game) or game == str(ORIGIN) else '$4e $b9'), 0.2)
    time.sleep(0.1)
    if MODE == 'ride':
        Y0, Y1 = os.environ.get('Y0'), os.environ.get('Y1')
        if Y0:
            h.cmd(f'hatari-debug b pc = $3dcf4 && ($33a20).w = 6 && ($33a18).w = {Y0} :once :file {D}/on_{TAG}.cmd'); time.sleep(0.2)
            h.cmd(f'hatari-debug b pc = $3dcf4 && ($33a20).w = 6 && ($33a18).w = {Y1} :once :file {D}/save_{TAG}.cmd'); time.sleep(0.2)
        else:
            h.cmd(f'hatari-debug b pc = $3dcf4 && ($33a20).w = 6 :once :file {D}/on_{TAG}.cmd'); time.sleep(0.2)
            h.cmd(f'hatari-debug b pc = $3dcf4 && ($33a20).w = 0 && ($33a18).w > {4*END-5} :once :file {D}/save_{TAG}.cmd'); time.sleep(0.2)
        h._xdo('keydown', '--window', h.win, 'Up'); time.sleep(0.4); h._xdo('keyup', '--window', h.win, 'Up')
    else:
        start = h._arm_vbl(int(os.environ.get('NV','90')), f' :file {D}/save_{TAG}.cmd'); time.sleep(0.2)
        h.cmd('hatari-debug profile on')
    t0 = time.time()
    while not prof.exists() and time.time() - t0 < 120: time.sleep(1)
    time.sleep(1)
    print('saved', prof.exists(), prof.stat().st_size if prof.exists() else 0)
finally:
    h.close()
