"""Held fire across death -> game over -> title: does a new game start by itself (and how many times)? usage: holdfire.py <build dir> <tag>"""
import sys, time, json, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus
def main(build, tag, secs=75):
    h = Nebulus(game=Path(build), workdir=f'/tmp/strun-nin2g{tag}')
    rows = []
    try:
        print('in tower', h.boot_to_game())
        h._xdo('keydown', '--window', h.win, 'Control_R')       # fire held from now on
        t0 = time.time()
        while time.time() - t0 < secs:
            time.sleep(1.5)
            a, b, c, st, lv = (h.peekw(x) for x in (0x3ad98, 0x3ad9a, 0x3ad9c, 0x33a20, 0x3390c))
            title = 'Higl' if 'High' else ''
            rows.append((round(time.time() - t0, 1), (a, b, c), st, lv))
            print(rows[-1], flush=True)
        h._xdo('keyup', '--window', h.win, 'Control_R')
        h.shot(str(Path(build).parent / f'hold_{tag}.png'))
    finally:
        h.close()
    json.dump(rows, open(f'hold_{tag}.json', 'w'))
main(sys.argv[1], sys.argv[2])
