import sys, time, tempfile, shutil, re
from pathlib import Path
ROOT = Path("/home/ryan/Code/AtariST/gamebench")
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "games/in_progress/populous/tools"), str(ROOT / "games/in_progress/populous/work/scratch/machines")]
import test_hd_image as t
from populous import Populous
from stharness import TOS
from mm import mem
img = Path(sys.argv[1]); machine = sys.argv[2]; tos = sys.argv[3]; m = int(sys.argv[4])
R = Path(tempfile.mkdtemp(prefix="strun-"))
SRC = t.test_image(img, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "pop")
shutil.copy(SRC, R / "hd.img")
h = Populous(workdir=str(R), files=[], autorun="", extra=t.hd_args(R), machine=machine, tos=TOS[tos], memsize_kb=m)
try:
    t.wait_drive_c(h); time.sleep(12)
    print("membot/memtop", mem(h, 0x432, 8), "phystop", mem(h, 0x42e, 4), "_v_bas_ad", mem(h, 0x44e, 4), "resvalid/resvector", mem(h,0x426,8), "memcntlr", mem(h, 0x424, 2))
    for a in (0xb2000, 0xb3000, 0xb4000, 0xbf000, 0xb5000, 0xb9000, 0xbd000, 0xcf000, 0xd0000, 0xe0000, 0xf0000, 0xf8000):
        print(hex(a), mem(h, a, 16))
finally:
    h.close()
