import sys, time, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
import pm_cells as pc
from mm import start, mem
cell, medium, path, tmax = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
h = start(cell, medium, path)
try:
    (ox, oy), _ = pc.GEOM[(cell, "menu")]
    menu = pc.REF / ("tt_menu_buttons.png" if cell == "tt" else "falcon_menu_buttons.png")
    mbox = (460 + ox, 310 + oy, 640 + ox, 395 + oy)
    t = pc.wait_for_crop(h, menu, mbox, 150)
    print("menu after", t, flush=True)
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    t0 = time.time()
    while time.time() - t0 < tmax:
        time.sleep(20)
        try:
            print(int(time.time() - t0), mem(h, 0xB3004, 4), flush=True)
        except Exception as e:
            print("fail", e); break
finally:
    h.close()
