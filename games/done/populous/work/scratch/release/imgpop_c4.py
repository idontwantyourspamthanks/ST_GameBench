import sys, time, tempfile, shutil, re
from pathlib import Path
ROOT = Path("/home/ryan/Code/AtariST/gamebench")
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "games/in_progress/populous/tools"), str(ROOT / "games/in_progress/populous/work/scratch/machines")]
import test_hd_image as t
from populous import Populous
from stharness import TOS
from mm import mem
img = Path(sys.argv[1])
R = Path(tempfile.mkdtemp(prefix="strun-"))
SRC = t.test_image(img, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "pop")
shutil.copy(SRC, R / "hd.img")
h = Populous(workdir=str(R), files=[], autorun="", extra=t.hd_args(R) + ["--trace", "gemdos"], machine="ste", tos=TOS["1.62"], memsize_kb=1024)
try:
    t.wait_drive_c(h); time.sleep(15); h.key("space", 0.5)
    # break when D15RH has just been read (HAGA Fclose at $FAB80 returns)
    f = h.R / "c4.txt"; f.write_text("m $b8fc0 160\nm $b1d40 32\nm $f8000 32\nr\n")
    h.cmd(f"hatari-debug b pc = $fab80 :trace :once :file {f}")
    time.sleep(35)
    lg = open(h.logpath).read(); i = lg.find("> m $b8fc0")
    print(lg[i:i + 2500])
finally:
    h.close()
