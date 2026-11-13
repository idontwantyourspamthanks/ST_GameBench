import sys, time, tempfile, shutil, re
from pathlib import Path
ROOT = Path("/home/ryan/Code/AtariST/gamebench")
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "games/in_progress/populous/tools")]
import test_hd_image as t
from populous import Populous
from stharness import TOS
TAG = sys.argv[5] if len(sys.argv) > 5 else "x"
img = Path(sys.argv[1]); machine = sys.argv[2]; tos = sys.argv[3]; mem = int(sys.argv[4])
R = Path(tempfile.mkdtemp(prefix="strun-"))
SRC = t.test_image(img, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "pop")
shutil.copy(SRC, R / "hd.img")
h = Populous(workdir=str(R), files=[], autorun="", extra=t.hd_args(R) + ["--trace", "gemdos"], machine=machine, tos=TOS[tos], memsize_kb=mem)
try:
    t.wait_drive_c(h)
    time.sleep(15); h.key("space", 0.5)
    for i in range(10):
        time.sleep(5); h.shot(f"/tmp/imgpop_{TAG}_{i}.png")
    lg = open(h.logpath).read()
    print("\n".join(l[:150] for l in lg.splitlines() if "Crawio" not in l and "repeats" not in l and "PNG" not in l)[-3500:])
finally:
    h.close()
