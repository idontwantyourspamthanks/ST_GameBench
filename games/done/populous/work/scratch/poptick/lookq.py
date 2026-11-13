import sys, time, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/"machines"), str(HERE.parents[2]/"tools"), str(HERE.parents[4]/"tools")]
import pm_cells as pc
from mm import start, mem
cell, medium, path, tw = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
h = start(cell, medium, path)
try:
    (ox, oy), _ = pc.GEOM[(cell, "menu")]
    menu = pc.REF / ("tt_menu_buttons.png" if cell == "tt" else "falcon_menu_buttons.png")
    mbox = (460 + ox, 310 + oy, 640 + ox, 395 + oy)
    t = pc.wait_for_crop(h, menu, mbox, 150)
    pc.goto_shot(h, cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    time.sleep(tw)
    D = h.peekl(0xB3104)
    print("hdr", mem(h, 0xB3000, 16), "D", hex(D), flush=True)
    for a, n in [(0xb632,6),(0xb6f4,6),(0xb800,6),(0xb940,6),(0xbbf8,8),(0x1672a,6),(0x16d80,8),(0x14a28,8),(0xee16,2),(0x171a8,8),(0x18244,8),(0x20796,8)]:
        print(hex(a), mem(h, a + D, n), flush=True)
    print("pc/ txt at AD96+D", mem(h, 0xAD96 + D, 8))
    print("payload sites table", mem(h, 0xB3110, 32))
finally:
    h.close()
