import sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
import pm_cells as pc
from mm import start, mem
cell, medium, path = sys.argv[1:4]
h = start(cell, medium, path)
try:
    (ox, oy), _ = pc.GEOM[(cell, "menu")]
    menu = pc.REF / ("tt_menu_buttons.png" if cell == "tt" else "falcon_menu_buttons.png")
    mbox = (460 + ox, 310 + oy, 640 + ox, 395 + oy)
    t = pc.wait_for_crop(h, menu, mbox, 150)
    print("menu after", t, flush=True)
    h.shot("/tmp/pt/lkf_menu.png")
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    for i in range(10):
        time.sleep(10)
        h.shot(f"/tmp/pt/lkf_{i:02d}.png"); print(i, mem(h,0xB3004,4), flush=True)
    import re
    print("LOG:", [l for l in h._logtext().splitlines() if re.search("rror|xception|ombs|alt|Bus|Address", l)][:12])
finally:
    h.close()
