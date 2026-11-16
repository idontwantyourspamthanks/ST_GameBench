#!/usr/bin/env python3
"""cold_tt.py: cold boot build/game on a TT (4 MB, TOS 3.06, --mmu true) with the Hatari named by $HATARI (default: the patched per-scanline-palette build of dist/hatari.local),
Raids map -> snap/ttp_map.sav, Panao (Crawler) -> snap/ttp_crawler.sav."""
import sys, os, time
from cs import *
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
import mw2raids
from stharness import MACHINE_TOS
h = Hatari(snapshot=None, machine='tt', tos=MACHINE_TOS['tt'], memsize_kb=4096, game_dir=GAME / 'build/game', extra=['--mmu', 'true', '--joy1', 'none'])
try:
    t0 = time.time()
    time.sleep(70)
    ref = GAME / 'work/ref/mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45)
    mw2raids._enter_raids_from_hall(h)
    print('map after %.0f s' % (time.time() - t0), flush=True)
    h.savemem(str(HERE / 'snap/ttp_map.sav'))
    r = mw2raids.enter_raid(h, 126, 159)
    print('entered', r, flush=True)
    time.sleep(5)
    print('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.savemem(str(HERE / 'snap/ttp_crawler.sav'))
    h.shot(str(HERE / 'snap/ttp_crawler.png'))
    print('saved', flush=True)
finally:
    h.close()
