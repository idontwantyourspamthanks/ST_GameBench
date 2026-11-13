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
    f = h.R / "r.txt"; f.write_text("e d0\ne a7\n")
    h.cmd(f"hatari-debug b pc = $fce6 :trace :file {f}")
    time.sleep(0.5)
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    time.sleep(tw)
    L = h._logtext().splitlines()
    idx = [k for k, l in enumerate(L) if "matched" in l]
    for k in idx[:8]:
        print("\n".join(l[:150] for l in L[k:k+7]))
        print("--")
finally:
    h.close()
