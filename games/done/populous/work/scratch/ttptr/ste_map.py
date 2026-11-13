"""STE (8 MHz, stock game, snapshot genesis_start): with the pointer over the map, how many VBLs have a drawn pointer ($16f12 != 0)?  Over the panel for comparison."""
import sys, time
from pathlib import Path
GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path[:0] = [str(GAME / "tools"), str(GAME / "work/scratch/ttptr")]
import ttp
from populous import Populous, HOME
h = Populous(snapshot=Populous.SNAP / "genesis_start.sav")
try:
    time.sleep(2)
    for name, (x, y) in (("map", (300, 250)), ("left panel", (150, 340))):
        h.goto(x + 96 - 0, y + 58 - 0, home_xy=HOME) if False else h.goto(x // 2 * 1 + 96 + x // 2, y // 2 + 58 + y // 2, home_xy=HOME)
        time.sleep(1.5)
        recs = None
        st, recs = ttp.measure(h, 0, secs=5, name="ste")
        nz = sum(r["f12"] != 0 for r in recs)
        print(name, "VBL entries", len(recs), "with a drawn pointer (f12 != 0):", nz, "flips", st["flips"], flush=True)
        h.shot(str(GAME / f"work/shots/ttptr/ste_{name.replace(' ', '_')}.png"))
finally:
    h.close()
