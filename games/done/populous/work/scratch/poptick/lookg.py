import sys, time, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
import pm_cells as pc
from mm import start, mem
cell, medium, path = sys.argv[1:4]
h = start(cell, medium, path, extra=["--trace", "gemdos"])
try:
    (ox, oy), _ = pc.GEOM[(cell, "menu")]
    menu = pc.REF / ("tt_menu_buttons.png" if cell == "tt" else "falcon_menu_buttons.png")
    mbox = (460 + ox, 310 + oy, 640 + ox, 395 + oy)
    t = pc.wait_for_crop(h, menu, mbox, 150)
    print("menu after", t, flush=True)
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    time.sleep(75)
    try:
        h.shot('/tmp/pt/lkg_end.png'); print('marker', mem(h,0xB3004,4), 'hdr', mem(h,0xB3000,16), 'D?', mem(h,0xB3104,4), flush=True)
    except Exception as e:
        print('SHOT FAILED', e)
        print('\n'.join(h._logtext().splitlines()[-25:]))
    L = h._logtext().splitlines()
    sel = [l for l in L if re.search("Mshrink|Malloc|Mfree|Pexec|Fopen|Fread|Fseek|Fclose", l)]
    print(len(L), len(sel))
    for l in sel[:14]: print(l[:200])
finally:
    h.close()
