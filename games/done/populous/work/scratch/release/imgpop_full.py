"""PopRelease: patient cold boot of Populous from the all-games image to play.  python3 imgpop_full.py IMG machine tos mem [cpuclock]
Prints RESULT with marker / flags / hook / turn rate / bus errors."""
import sys, time, tempfile, shutil, re
from pathlib import Path
ROOT = Path("/home/ryan/Code/AtariST/gamebench")
GP = ROOT / "games/in_progress/populous"
sys.path[:0] = [str(ROOT / "tools"), str(GP / "tools"), str(GP / "work/scratch/machines")]
import test_hd_image as t
from populous import Populous, HOME, CONQUEST_XY, START_XY
from stharness import TOS
from mm import mem as rd
img = Path(sys.argv[1]); machine, tos, m = sys.argv[2], sys.argv[3], int(sys.argv[4]); cpu = int(sys.argv[5]) if len(sys.argv) > 5 else 0
R = Path(tempfile.mkdtemp(prefix="strun-"))
SRC = t.test_image(img, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "pop")
shutil.copy(SRC, R / "hd.img")
h = Populous(workdir=str(R), files=[], autorun="", extra=t.hd_args(R), machine=machine, tos=TOS[tos], memsize_kb=m)
BOX = (550, 360, 735, 455)
out = {}
try:
    t0 = time.time()
    t.wait_drive_c(h); time.sleep(10)
    if cpu:
        h.set_cpuclock(cpu)
        if machine == "megaste" and cpu >= 16:
            h.debug("w $ff8e21 $03", 0.5)
    h.key("space", 0.5)
    refp = GP / "work/scratch/poptick/menu_buttons_ref.png"
    out["menu"] = bool(h.wait_for(refp, BOX, timeout=400, poll=3))
    out["t_menu"] = round(time.time() - t0)
    h.goto(*CONQUEST_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(12)
    play = False
    for k in range(8):
        h.goto(*START_XY, home_xy=HOME); h.click(hold=0.4)
        for _ in range(12):
            time.sleep(5)
            try:
                if rd(h, 0xB632, 6).replace(" ", "") == "4ef9000ba000":
                    play = True; break
            except Exception:
                pass
        if play: break
    out["hook"] = rd(h, 0xB632, 6)
    out["marker"] = rd(h, 0xB3000, 12)
    out["t_play"] = round(time.time() - t0)
    if play:
        time.sleep(8)
        a = h.peekw(Populous.TURN); v0 = h.vbl(); time.sleep(10); b = h.peekw(Populous.TURN); v1 = h.vbl()
        out["turns/emulated s"] = round(((b - a) & 0xFFFF) / ((v1 - v0) / 50), 3)
        out["ee16"] = rd(h, 0xEE16, 2)
    lg = h._logtext()
    out["errors"] = [l[:100] for l in lg.splitlines() if re.search("Bus Error|Address Error|double bus|halted", l)]
    h.shot(f"/tmp/imgfull_{machine}_{tos}_{m}.png")
finally:
    print("RESULT", machine, tos, m, out, flush=True)
    h.close()
