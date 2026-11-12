"""One fresh restore of the cold-booted Lobos state per pad key (jag_ste_lobos.sav, J mode), breakpoints on the game's consumers.
usage: t_consumers2.py key[,key...]   (tap 250 ms; P taps twice)"""
import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
BP = {1: 0x30f92, 2: 0x1ab2c, 3: 0x1ab54, 4: 0x1b384, 5: 0x1b446, 6: 0x1ab8e}
names_ = {1: 'F-key dispatch $30f92', 2: 'icon prev $1ab2c', 3: 'icon next $1ab54', 4: 'pause loop $1b384', 5: 'Esc consumed $1b446', 6: 'select/fire $1ab8e'}
for key in sys.argv[1].split(','):
    h = Hatari(snapshot=str(G / 'work/snapshots/jag_ste_lobos.sav'), memsize_kb=1024, game_dir=G / 'build/jag_a', extra=PADX)
    try:
        time.sleep(3); jmode(h); time.sleep(2)
        h.debug('b all', 0.3)
        for i, a in BP.items():
            h.cmd(f'hatari-debug b pc = ${a:x} :trace'); time.sleep(0.4)
        n0 = len(h._logtext())
        taps = 2 if key == 'p' else 1
        for _ in range(taps):
            h._xdo('keydown', '--window', h.win, key); time.sleep(0.25); h._xdo('keyup', '--window', h.win, key); time.sleep(2.0)
        t = h._logtext()[n0:]
        c = {names_[i]: len(re.findall(rf'^{i}\. CPU breakpoint', t, re.M)) for i in BP}
        print(f'pad {key}:', {k: v for k, v in c.items() if v}, 'type', w(h, 0x6220), flush=True)
    finally:
        h.close()
