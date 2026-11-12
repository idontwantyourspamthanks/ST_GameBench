#!/usr/bin/env python3
"""Cold-boot gate for the build/p5ctl set (pp_nofade + pp_bigram_cache + p5_ctl_turn + p5_ctl_buggy).

  coldboot.py ste1m|megaste4m [out.log]

Boots to the Skiing view (control M), then: MWPO marker $B2FF8, site bytes $12fe2/$13618, blob $B3800,
a walk (left click), and a mouse turn (rel -150 px) with the heading logged.
"""
import sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools']
from pathlib import Path
from mw1 import MW1, TOS

cfg = {'ste1m': dict(machine='ste', tos=TOS['1.62'], memsize_kb=1024),
       'megaste4m': dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)}[sys.argv[1]]
BUILD = '/home/ryan/Code/AtariST/gamebench/games/done/midwinter/build/p5ctl'
log = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    log.append(s)


h = MW1(snapshot=None, game_dir=BUILD, **cfg)
try:
    P('config', sys.argv[1], cfg['machine'], cfg['tos'].name, cfg['memsize_kb'], 'KB')
    t = time.time()
    h.boot_to_game('M')
    P(f'boot_to_game ok in {time.time() - t:.0f} s; control mode', h.control_mode(), 'gstate', h.gstate())
    P('MWPO marker $b2ff8:', h.peek(0xB2FF8, 4), '(want b"MWPO")')
    P('$12fe2:', h.peek(0x12FE2, 6).hex(), '(want 4ef9000b3800)')
    P('$13618:', h.peek(0x13618, 6).hex(), '(want 303900015110)')
    P('$b3800:', h.peek(0xB3800, 8).hex(), '(want 2f0220390002 4faa)')
    # mouse turn: rel(-150) -> heading changes then stops
    h.center(); time.sleep(0.5)
    hd0 = h.heading()
    h.rel(-150, 0)
    rows = []
    for i in range(10):
        time.sleep(0.5)
        rows.append((h.vbl(), h.heading(), h.peekw(0x15110)))
    P('mouse rel(-150,0): start heading', hd0)
    P('VBL heading rate15110 :', rows)
    # walk
    p0 = h.gstate()
    h.walk(); time.sleep(8)
    p1 = h.gstate()
    P('walk: before', p0, 'after 8 s', p1)
    P('MWPO after walk:', h.peek(0xB2FF8, 4))
    h.shot(f'/tmp/coldboot_{sys.argv[1]}.png')
    P('screenshot /tmp/coldboot_%s.png' % sys.argv[1])
finally:
    h.close()
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / f'coldboot_{sys.argv[1]}.log'
out.write_text('\n'.join(log) + '\n')
