# master Powermonger HD (released set, build/dist_build/hd copy) on the Falcon, GEMDOS folder: save / load through the menu, then the "left button held" latch and the next click
import sys, time, os, re
from pathlib import Path
M = Path("/home/ryan/Code/AtariST/gamebench/games/done/powermonger")
sys.path.insert(0, str(M / "tools"))
import pm, pmpatch
machine = sys.argv[1] if len(sys.argv) > 1 else "falcon"
trace = len(sys.argv) > 2 and sys.argv[2] == "trace"
tos, mem = {"falcon": ("4.04", 4096), "ste": ("1.62", 1024)}[machine]
h = pmpatch.make_pm(None, Path("/tmp/pmww1fhd2/master_hd"), acsi=False, machine=machine, tos=pm.TOS[tos], memsize_kb=mem)
HELD, LATCH, WIN, BTN = 0x2DF9C, 0x2DF96, 0x7A36, 0x1C48F
def st(tag):
    print(f"[{tag}] vbl {h.vbl()} held($2df9c)={h.peekw(HELD)} latch($2df96)={h.peekw(LATCH)} btn($1c48f)={h.peekw(BTN-1)&0xff:02x} window($7a36)={h.peekw(WIN):#x} in_game={h.in_game()}", flush=True)
def optclick(tag):
    h.click_st(72, 138, wait=2.0)
    op = h.peekw(WIN) != 0
    print(f"[{tag}] OPTION click -> window {'OPEN' if op else 'NOT OPEN (click lost)'}", flush=True)
    if op:
        h.click_st(250, 60, hold=0.6, wait=2.0)       # close it again (click outside)
        if h.peekw(WIN) != 0:
            h.click_st(250, 60, hold=0.6, wait=2.0)
    return op
try:
    h.boot_to_game()
    print("LOG", h.R, flush=True)
    time.sleep(2); st("map")
    if trace:
        (h.R / "t_vbl.txt").write_text("e VBL\ne HBL\nm $1c48f 1\nm $2df9c 2\n")
        (h.R / "t_pkt.txt").write_text("e VBL\ne HBL\nm $1c491 1\n")
        h.cmd(f"hatari-debug b pc = $129a && ($1c48f).b > 0 :trace :file {h.R / 't_vbl.txt'}")
        h.cmd(f"hatari-debug b pc = $1942 && ($1c491).b > 0 :trace :file {h.R / 't_pkt.txt'}")
    for rnd in range(3):
        ok = pmpatch.run_saveload(h, False)
        print(f"[round {rnd}] run_saveload -> {ok}", flush=True)
        time.sleep(3); st(f"round {rnd} after load, button up")
        optclick(f"round {rnd} 1st click after load")
        st(f"round {rnd} after 1st click")
        optclick(f"round {rnd} 2nd click after load")
finally:
    h.close()
