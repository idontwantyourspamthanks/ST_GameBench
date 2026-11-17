"""Race steering through real host keys (Hatari joy1 keys) with the final default: python3 joy2.py SNAP OUT.txt
Presses cursor Up / Up+Left / Up+Right / releases and prints $6105 (joystick byte), $130c (speed), $1318 (lateral) after each; then the same on the walk to the menus is in menus.py."""
import sys, time
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2")
from mxlib_fin import *
snap, out = sys.argv[1], sys.argv[2]
h = Moonshine(snapshot=str(SNAPDIR / snap), extra=['--joy1', 'keys'])
L = []
def rec(lbl):
    L.append(f"{lbl:16s} $6105={h.peekb(0x6105):02x} $130c={h.peekw(0x130c):04x} $1318={h.peekw(0x1318):04x} $100e={h.peekw(0x100e)}")
    print(L[-1], flush=True)
try:
    time.sleep(2)
    apply_names(h, SETS["X"], "X")
    time.sleep(1)
    rec("idle")
    h._xdo("keydown","--window",h.win,"Up"); time.sleep(4); rec("Up held")
    h._xdo("keydown","--window",h.win,"Left"); time.sleep(3); rec("Up+Left")
    h._xdo("keyup","--window",h.win,"Left"); time.sleep(2.5); rec("Up")
    h._xdo("keydown","--window",h.win,"Right"); time.sleep(3); rec("Up+Right")
    h._xdo("keyup","--window",h.win,"Right"); h._xdo("keyup","--window",h.win,"Up"); time.sleep(2.5); rec("released")
finally:
    h.close()
open(out, "w").write("\n".join(L) + "\n")
