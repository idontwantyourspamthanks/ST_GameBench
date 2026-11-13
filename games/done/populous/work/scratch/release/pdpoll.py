import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc
from mm import start, mem
cell, path = sys.argv[1], sys.argv[2]
h = start(cell, "floppy", path, extra=["--trace", "gemdos"])
try:
    t0 = time.time(); last = None
    clicked = False
    (ox, oy), _ = pc.GEOM[(cell, "menu")]
    ref = pc.REF / "falcon_menu_buttons.png"
    while time.time() - t0 < 75:
        v = mem(h, 0xfb9c, 16)
        if v != last:
            print(f"{time.time()-t0:5.1f} VBL {h.vbl()}: {v}", flush=True); last = v
        if not clicked and time.time() - t0 > 18 and pc.crop_ok(h, ref, (460 + ox, 310 + oy, 640 + ox, 395 + oy)):
            print("menu; click", flush=True)
            pc.goto_shot(h, cell, "menu", *pc.CONQUEST); h.click(hold=0.4); clicked = True
        time.sleep(0.3)
finally:
    h.close()
