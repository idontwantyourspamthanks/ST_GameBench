"""PopRelease scratch: catch the first write that changes the loader PD +$3a during the loader (test scaffolding)"""
import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc
from mm import start, mem
cell, path = sys.argv[1], sys.argv[2]
COND = sys.argv[3] if len(sys.argv) > 3 else "($fba6).w < $19"
h = start(cell, "floppy", path, extra=["--trace", "gemdos"])
try:
    arm = h.R / "arm.txt"; hit = h.R / "hit.txt"
    arm.write_text(f"b {COND} :trace :once :file {hit}\n")
    hit.write_text("r\nm $fb6c 96\n")
    h.cmd(f"hatari-debug b pc = $fc6c :trace :once :file {arm}")
    t0 = time.time()
    while time.time() - t0 < 90:
        time.sleep(2)
        if h._logtext().count("> r\n") >= 1:
            time.sleep(3); break
    l = h._logtext(); i = l.find("CPU breakpoint condition")
    print(l[i:i + 4500])
finally:
    h.close()
