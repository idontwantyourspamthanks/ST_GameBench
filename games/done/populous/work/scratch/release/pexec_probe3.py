"""PopRelease scratch: who writes the loader's PD +$3a (test scaffolding)"""
import argparse, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc
from mm import start, mem
ap = argparse.ArgumentParser()
ap.add_argument("cell"); ap.add_argument("path"); ap.add_argument("--watch", default="fba6"); ap.add_argument("--wait", type=int, default=60)
a = ap.parse_args()
h = start(a.cell, "floppy", a.path, extra=["--trace", "gemdos"])
try:
    (ox, oy), _ = pc.GEOM[(a.cell, "menu")]
    r = pc.wait_for_crop(h, pc.REF / ("tt_menu_buttons.png" if a.cell == "tt" else "falcon_menu_buttons.png"), (460 + ox, 310 + oy, 640 + ox, 395 + oy), 150)
    print("menu after", r, flush=True)
    print("PD+30..3f now:", mem(h, 0xfb6c + 0x30, 16))
    hit = h.R / "hit.txt"
    hit.write_text("r\nm $a7 48\n")
    h.cmd(f"hatari-debug b (${a.watch}).w ! (${a.watch}).w :trace :file {hit}")
    pc.goto_shot(h, a.cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    time.sleep(a.wait)
    log = h._logtext()
    i = log.find("Pexec(3, \"populous")
    print(log[log.find("CPU breakpoint condition"):][:5000])
    print("PD+30..3f after:", mem(h, 0xfb6c + 0x30, 16))
finally:
    h.close()
