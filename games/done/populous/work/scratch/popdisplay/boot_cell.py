#!/usr/bin/env python3
"""Cold-boot cell for the display patches: boots build/PopDisplay/hd, reaches play, checks the sites and the payload in RAM,
then moves the real (host) mouse and looks at the pointer in screenshots.   python3 boot_cell.py NAME ste|st 1.62|1.04"""
import re
import sys
import time
from pathlib import Path

GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
sys.path.insert(0, str(GAME / "tools"))
from populous import Populous, HOME, CONQUEST_XY, START_XY  # noqa: E402
from stharness import TOS  # noqa: E402


def mem(h, addr, n):
    out = h.debug(f"m ${addr:x} {n}", 0.6)
    hx = re.findall(rf"{addr:08x}:\s+((?:[0-9a-f]{{2}} ?)+)", out, re.I)
    return hx[-1].strip().replace(" ", "") if hx else out.strip()


name, machine, tos = sys.argv[1], sys.argv[2], sys.argv[3]
mem_kb = int(sys.argv[4]) if len(sys.argv) > 4 else 1024
shots = GAME / "work" / "shots"
h = Populous(game_dir=GAME / "build/PopDisplay/hd", snapshot=None, memsize_kb=mem_kb, machine=machine, tos=TOS[tos])
try:
    time.sleep(16)
    h.key("space", 0.5)
    time.sleep(28)
    h.shot(str(shots / f"display_boot_{name}_menu.png"))
    h.goto(*CONQUEST_XY, home_xy=HOME)
    h.click(hold=0.4)
    time.sleep(9)
    h.goto(*START_XY, home_xy=HOME)
    h.click(hold=0.4)
    time.sleep(10)
    ok = h.in_play()
    res = dict(cell=name, in_play=ok, marker=bytes.fromhex(mem(h, 0xB3004, 4)).decode("latin1"), flags=mem(h, 0xB3008, 4),
              ee16=mem(h, 0xEE16, 2), site_16d80=mem(h, 0x16D80, 8), site_14a28=mem(h, 0x14A28, 8),
              blob_c2000=mem(h, 0xC2000, 8), blob_c2600=mem(h, 0xC2600, 8))
    print(res, flush=True)
    # the real IKBD path: move the host mouse over the map, grab a screenshot, wait, move again
    t1 = h.peekw(Populous.TURN)
    h.goto(400, 300, home_xy=HOME)
    time.sleep(2.0)
    h.shot(str(shots / f"display_boot_{name}_ptr1.png"))
    h.rel(120, 60)
    time.sleep(2.0)
    h.shot(str(shots / f"display_boot_{name}_ptr2.png"))
    t2 = h.peekw(Populous.TURN)
    # the pointer state words after the moves
    print(dict(turn_before=t1, turn_after=t2, pos=mem(h, 0x24786, 4), valid=mem(h, 0xC2400, 4), a4=mem(h, 0xC2408, 4),
               f12=mem(h, 0x16F12, 4)), flush=True)
finally:
    h.close()
