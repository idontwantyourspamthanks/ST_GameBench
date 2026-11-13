#!/usr/bin/env python3
"""PopRelease: STE floppy cold boot, in-game SAVE to Populous_save.st and LOAD from it, with the disk swaps (test scaffolding).
    python3 flsave.py BOOT.st SAVE.st"""
import re, shutil, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import pm_cells as pc                                   # noqa: E402
from mm import start, mem                               # noqa: E402
from populous import HOME, CONQUEST_XY, START_XY, Populous  # noqa: E402

BOX = (550, 360, 735, 455)
SH = GAME / "work" / "shots"


def clk(h, x, y, hold=0.4, wait=2.0):
    h.goto(x, y, home_xy=HOME)
    h.click(hold=hold)
    time.sleep(wait)


def turn(h):
    for _ in range(6):
        try:
            return h.peekw(Populous.TURN)
        except Exception:
            time.sleep(0.5)


def main():
    boot, save = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    td = Path(tempfile.mkdtemp(prefix="flsave-"))
    sv = td / "save.st"; shutil.copy(save, sv)
    bt = td / "boot.st"; shutil.copy(boot, bt)           # the swap target; start() copies its own for the first insert
    h = start("ste", "floppy", str(bt))
    out = {}
    try:
        from PIL import Image
        refp = HERE.parent / "poptick" / "menu_buttons_ref.png"
        time.sleep(16); h.key("space", 0.5); time.sleep(80); h.key("space", 0.5)
        out["menu"] = h.wait_for(refp, BOX, timeout=240, poll=2)
        h.goto(*CONQUEST_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(40)
        h.goto(*START_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(14)
        t0 = turn(h); time.sleep(2); out["turn_run"] = (t0, turn(h)); out["marker"] = mem(h, 0xB3000, 12)
        clk(h, 706, 410); clk(h, 350, 308); clk(h, 400, 385)
        for k in "tst":
            h.key(k, 0.4); time.sleep(0.5)
        h.cmd(f"hatari-option --disk-a {sv}"); time.sleep(3)
        clk(h, 320, 424, wait=25)
        h.shot(str(SH / "release_fl_save_prompt.png"))
        h.cmd(f"hatari-option --disk-a {bt}"); time.sleep(3)
        clk(h, 240, 256, wait=6)                         # OK of "INSERT THE ORIGINAL POPULOUS DISK IN A:"
        h.shot(str(SH / "release_fl_save_after_ok.png"))
        out["turn_saved"] = turn(h)
        # the save disk's root directory
        d = sv.read_bytes()
        names = [d[o:o + 11].decode("latin1") for o in range(512 * 7, 512 * 7 + 32 * 112, 32) if d[o] not in (0, 0xE5)]
        sizes = [int.from_bytes(d[o + 28:o + 32], "little") for o in range(512 * 7, 512 * 7 + 32 * 112, 32) if d[o] not in (0, 0xE5)]
        out["save_disk_root"] = list(zip(names, sizes))
        h.cmd(f"hatari-option --disk-a {sv}"); time.sleep(3)
        clk(h, 706, 410); clk(h, 350, 328, wait=10)
        h.shot(str(SH / "release_fl_load_list.png"))
        clk(h, 290, 134, wait=2)
        h.shot(str(SH / "release_fl_load_sel.png"))
        clk(h, 320, 424, wait=25)
        h.shot(str(SH / "release_fl_load_prompt.png"))
        h.cmd(f"hatari-option --disk-a {bt}"); time.sleep(3)
        clk(h, 432, 256, wait=8)                         # the LOAD prompt has one OK, at the right
        smp = []
        for _ in range(4):
            smp.append((h.vbl(), turn(h))); time.sleep(5)
        out["(VBL, turn) after the load"] = smp
        out["turns per VBL (expect 0.100 at 50 Hz)"] = round(((smp[-1][1] - smp[0][1]) & 0xFFFF) / (smp[-1][0] - smp[0][0]), 4)
        lg = h._logtext()
        out["bus/address errors in log"] = [l[:120] for l in lg.splitlines() if re.search("Bus Error|Address Error|double bus|halted", l)]
        h.shot(str(SH / "release_fl_load_done.png"))
        out["payload"] = mem(h, 0xB3000, 12); out["ee16"] = mem(h, 0xEE16, 2); out["b632"] = mem(h, 0xB632, 6)
    finally:
        print(out, flush=True)
        keep = td
        print("workdir", td, "hatari log", h.logpath)
        h.close()
main()
