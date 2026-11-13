"""PopRelease scratch: where does d0 become -35 inside Pexec(3,"populous.tos")?  (test scaffolding)"""
import argparse, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc
from mm import start, mem
ap = argparse.ArgumentParser()
ap.add_argument("cell"); ap.add_argument("path"); ap.add_argument("--arm", default="fd98"); ap.add_argument("--cond", default="d0 = $ffffffdd")
a = ap.parse_args()
h = start(a.cell, "floppy", a.path, extra=["--trace", "gemdos"])
try:
    (ox, oy), _ = pc.GEOM[(a.cell, "menu")]
    r = pc.wait_for_crop(h, pc.REF / ("tt_menu_buttons.png" if a.cell == "tt" else "falcon_menu_buttons.png"), (460 + ox, 310 + oy, 640 + ox, 395 + oy), 150)
    print("menu after", r, flush=True)
    arm = h.R / "arm.txt"; hit = h.R / "hit.txt"
    arm.write_text(f"b {a.cond} :trace :file {hit}\n")
    hit.write_text("r\nm $a7 64\nm $fb9c 16\n")
    if a.arm == "now":
        h.cmd(f"hatari-debug b {a.cond} :trace :once :file {hit}")
    else:
        h.cmd(f"hatari-debug b pc = ${a.arm} :trace :once :file {arm}")
    pc.goto_shot(h, a.cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    t0 = time.time()
    while time.time() - t0 < 200:
        time.sleep(3)
        l = h._logtext(); k = l.find("Mfree(0xB3000)")
        if l.count("> r\n") >= 1:
            time.sleep(3); break
    log = h._logtext()
    i = max(0, log.find("CPU breakpoint condition"))
    print(log[i:i + 6000])
finally:
    h.close()
