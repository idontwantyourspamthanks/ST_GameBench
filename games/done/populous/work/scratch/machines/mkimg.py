"""Build a one-game ACSI HD image for tests: python3 mkimg.py OUT.img SRC_DIR [autorun]"""
import sys, os
from pathlib import Path
BENCH = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(BENCH / "tools"))
import make_hd_image as mhi
import test_hd_image as thi
out, src = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
auto = sys.argv[3] if len(sys.argv) > 3 else "C:\\POPULOUS\\RUNME.TOS"
mhi.STAGE = Path(os.environ.get("TMPDIR", "/tmp")) / f"pmimg_{os.getpid()}"
mhi.STAGE.mkdir(parents=True, exist_ok=True)
mhi.VERSIONS = {k: "x" for k in ("MIDWINTR","MIDWINT2","HUNTER","POWERMON","POPULOUS")}
files = {"DESKTOP.INF": thi.autorun_inf(auto).decode()} if auto != "none" else {}
files = {k: v.encode() if isinstance(v, str) else v for k, v in files.items()}
tgt, total, psz = mhi.build_image(out, {"POPULOUS": src}, 16000, "2026-11-11", files)
print(out, total, psz)
import shutil; shutil.rmtree(mhi.STAGE, ignore_errors=True)
