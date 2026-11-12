"""Each pad button's effect inside the game: breakpoints on the game's own consumer routines (cold-booted state, jag_ste_jeep.sav, J mode).
1 $30f92 F-key dispatch (range-checked F1-F10)  2 $1ab2c icon-bar previous (key '-')  3 $1ab54 icon-bar next (key '+')  4 $1b384 pause loop
5 $1b446 Esc consumed  6 $1ab8e select/fire event consumed ($6872, J mode)"""
import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
snap = sys.argv[1] if len(sys.argv) > 1 else 'jag_ste_jeep.sav'
h = Hatari(snapshot=str(G / 'work/snapshots' / snap), memsize_kb=1024, game_dir=G / 'build/jag_a', extra=PADX)
BP = {1: 0x30f92, 2: 0x1ab2c, 3: 0x1ab54, 4: 0x1b384, 5: 0x1b446, 6: 0x1ab8e}
def counts(t):
    return {i: len(re.findall(rf'^{i}\. CPU breakpoint', t, re.M)) for i in BP}
try:
    time.sleep(3)
    print('marker', memb(h, 0xb2ff8, 4), 'type', w(h, 0x6220))
    jmode(h); time.sleep(2)
    h.debug('b all', 0.3)
    for i, a in BP.items():
        h.cmd(f'hatari-debug b pc = ${a:x} :trace'); time.sleep(0.4)
    def tap(key, ms=250, gap=1.2):
        n0 = len(h._logtext())
        h._xdo('keydown', '--window', h.win, key); time.sleep(ms / 1000.0); h._xdo('keyup', '--window', h.win, key); time.sleep(gap)
        c = counts(h._logtext()[n0:])
        return {i: n for i, n in c.items() if n}
    for k, name in [('x', 'B fire'), ('x', 'B fire'), ('q', '* (prev weapon)'), ('q', '* (prev weapon)'), ('w', '# (next weapon)'), ('w', '# (next weapon)')]:
        print(f'{name:18s} ->', tap(k), flush=True)
    for k in '1234567890':
        print(f'pad {k} (F{(int(k) or 10)}) ->', tap(k, 250, 2.0), flush=True)
    print('P (pause)         ->', tap('p', 300, 1.0), flush=True)
    print('P (resume)        ->', tap('p', 300, 1.5), flush=True)
    print('Option (Esc)      ->', tap('o', 150, 1.5), flush=True)
    print('final type', w(h, 0x6220), 'vbl', h.vbl())
finally:
    h.close()
