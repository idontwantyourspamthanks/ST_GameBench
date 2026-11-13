"""PopRelease: Populous from the all-games image (ACSI+HDDRIVER): who fails the verify.  python3 imgpop_diag.py IMG [machine tos mem]"""
import sys, time, tempfile, shutil
from pathlib import Path
ROOT = Path("/home/ryan/Code/AtariST/gamebench")
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "games/in_progress/populous/tools")]
import test_hd_image as t
from populous import Populous
from stharness import TOS
img = Path(sys.argv[1]); machine = sys.argv[2] if len(sys.argv) > 2 else "ste"; tos = sys.argv[3] if len(sys.argv) > 3 else "1.62"; mem = int(sys.argv[4]) if len(sys.argv) > 4 else 1024
hexa = "%x" % (0xfaeb2 + (mem * 1024 - 0x100000))
R = Path(tempfile.mkdtemp(prefix="strun-"))
SRC = t.test_image(img, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "pop")
shutil.copy(SRC, R / "hd.img")
h = Populous(workdir=str(R), files=[], autorun="", extra=t.hd_args(R) + ["--trace", "gemdos"], machine=machine, tos=TOS[tos], memsize_kb=mem)
try:
    f = h.R / "pf.txt"; f.write_text("r\nm $b3000 16\nm $b3100 16\n")
    h.cmd(f"hatari-debug b pc = $b3070 :trace :once :file {f}")
    g = h.R / "ap.txt"; g.write_text("r\n")
    h.cmd(f"hatari-debug b pc = $b3010 :trace :file {g}")
    t.wait_drive_c(h)
    h.boot_to_game(); time.sleep(3)
    lg = h._logtext()
    import re
    i = lg.find("CPU breakpoint condition")
    print(lg[i:i + 6000])
finally:
    h.close()
