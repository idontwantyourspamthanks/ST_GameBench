import sys, time, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
import pm_cells as pc
from mm import start, mem
cell, medium, path, tw = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
h = start(cell, medium, path, extra=["--trace", "gemdos"])
try:
    (ox, oy), _ = pc.GEOM[(cell, "menu")]
    menu = pc.REF / ("tt_menu_buttons.png" if cell == "tt" else "falcon_menu_buttons.png")
    mbox = (460 + ox, 310 + oy, 640 + ox, 395 + oy)
    t = pc.wait_for_crop(h, menu, mbox, 150)
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    time.sleep(tw)
    for i in range(3):
        out = h.debug("r", 1.0)
        print([l for l in out.splitlines() if "PC" in l or "PC:" in l or "SR" in l][:3], flush=True)
        time.sleep(1)
    L = h._logtext().splitlines()
    sel = [l for l in L if re.search("Mshrink|Malloc|Mfree|Pexec|Fopen|Fread|Fseek|Fclose|Fsfirst", l)]
    print(len(sel))
    for l in sel[-12:]: print(l[:160])
finally:
    h.close()
