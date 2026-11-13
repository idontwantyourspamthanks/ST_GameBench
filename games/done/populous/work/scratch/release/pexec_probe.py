"""PopRelease scratch: Falcon/TT/STE floppy, catch Pexec(3,"populous.tos") result + Malloc(-1) (test scaffolding)."""
import argparse, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc
from mm import start, mem

ap = argparse.ArgumentParser()
ap.add_argument("cell"); ap.add_argument("path"); ap.add_argument("--mem", type=int); ap.add_argument("--tos")
ap.add_argument("--bp", default="fce4", help="address after the Pexec trap")
ap.add_argument("--bp-load", type=int, default=1)
a = ap.parse_args()
h = start(a.cell, "floppy", a.path, extra=["--trace", "gemdos"], mem=a.mem, tos=a.tos)
try:
    r = pc.wait_for_crop(h, pc.REF / ("tt_menu_buttons.png" if a.cell == "tt" else "falcon_menu_buttons.png"),
        (460 + pc.GEOM[(a.cell, "menu")][0][0], 310 + pc.GEOM[(a.cell, "menu")][0][1], 640 + pc.GEOM[(a.cell, "menu")][0][0], 395 + pc.GEOM[(a.cell, "menu")][0][1]), 150)
    print("menu after", r, flush=True)
    # base page of the loader: from the trace "Mshrink(0x....., 0x2D6)"
    log = h._logtext()
    m = re.search(r"Mshrink\(0x([0-9A-F]+), 0x2[DE][46]\)", log)
    bpg = int(m.group(1), 16); print("loader base page", hex(bpg))
    code = bpg + 0x80
    bytes_ = "2f 3c ff ff ff ff 3f 3c 00 48 4e 41 5c 8f 4e 71".split()
    f1 = h.R / "after.txt"
    f1.write_text("r\n" + "m $432 8\n" + "m $42e 4\n" + "m $%x 64\n" % (bpg) +
                  "w $%x %s\n" % (code, " ".join("$" + b for b in bytes_)) + "r pc=$%x\n" % code)
    f2 = h.R / "malloc.txt"
    f2.write_text("r\n")
    h.cmd(f"hatari-debug b pc = ${a.bp} :trace :file {f1}")
    h.cmd(f"hatari-debug b pc = ${code + 14:x} :trace :file {f2}")
    pc.goto_shot(h, a.cell, "menu", *pc.CONQUEST)
    h.click(hold=0.4)
    t0 = time.time()
    while time.time() - t0 < 200:
        time.sleep(3)
        if "Removed" in h._logtext() and False: break
        if h._logtext().count("D0 ") >= 3 and h._logtext().count("D0 ") > 0 and "malloc" in "": break
        if h._logtext().count("D0 ") >= 3: break
    log = h._logtext()
    i = log.find("Pexec(3, \"populous")
    j = log.find("> r\n", i)
    print(log[j:j + 2600] if j >= 0 else log[-3000:])
finally:
    h.close()
