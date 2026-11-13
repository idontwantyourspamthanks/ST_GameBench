"""The IKBD-cut test: a SAVE entered while the game's IKBD parser is mid-reply ($2022 = 5: header $f7 consumed, five data bytes still to come, exactly what a
call that starts inside a mouse reply leaves; the call masks the MFP, so the five bytes are lost).  Without the parser reset after the call, the next reply's
header $f7 is stored as the button byte -> $2023 = $f7 -> the VBL handler's `move.b $2023,d0 / ext.w d0 / jmp $1936(pc,d0.w)` jumps through index -9.
python3 cell_ikbd.py --tag X --build DIR"""
import argparse, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--build", required=True)
a = ap.parse_args()
P = lambda *x: print(*x, flush=True)
h, info = make("hd", a.build, "ste", None, 2048, a.tag)
try:
    ok = h.boot_to_game(); P(f"CELL {a.tag}: build={a.build} in_play={ok} marker={h.marker()!r} turn={turn(h)} $2022={h.peekw(0x2022)>>8:#x}")
    time.sleep(5)
    cf = SD / f"cmd_ikbd_{a.tag}.txt"
    cf.write_text("w $2022 $05\nm $2022 2\n")
    h.cmd(f"hatari-debug b pc = $80300 && d0 = 1 :trace :once :file {cf}")
    time.sleep(0.5)
    n0 = len(h._logtext())
    assert open_req(h); choose(h, "save"); name(h, "t1"); confirm(h)
    t0 = time.time()
    while time.time() - t0 < 60:
        time.sleep(3)
        try:
            P("t+%2d turn=%s $2022=%#x $2023=%#x $70=%#x" % (time.time() - t0, turn(h), h.peekw(0x2022) >> 8, h.peekw(0x2022 + 1) >> 8 if False else (h.peekw(0x2022) & 0xff), h.peekl(0x70)))
        except Exception as e:
            P("debugger not answering", repr(e)); break
        errs = [l for l in logbad(h)]
        if any("Address Error" in l for l in errs):
            break
    L = h._logtext()[n0:]
    P("poke applied:", "0000202" in L and "w $2022" in L)
    bad = logbad(h)
    P("LOG errors:", len(bad)); [P("  ", l) for l in bad[:6]]
    running_ = False
    try:
        running_ = running(h, 2)
    except Exception:
        pass
    P(f"RESULT {a.tag}: game running after the cut-reply save = {running_}")
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}.log")
    h.close()
