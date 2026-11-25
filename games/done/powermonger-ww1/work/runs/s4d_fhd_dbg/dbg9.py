import sys, time, shutil
from pathlib import Path
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1/tools")
import pmww, wwhd
hd = Path(sys.argv[1]); wd = sys.argv[2]; mode = sys.argv[3] if len(sys.argv) > 3 else "load"
h = wwhd.PMWHD(hd, workdir=wd, machine="falcon", tos=pmww.TOS["4.04"], memsize_kb=4096, extra=["--borders", "false"])
S = Path(wd) / "shots"
def st(n):
    h.shot(str(S / f"d_{n}.png"))
    print(f"[{n}] WINDOW_OPEN={h.peekw(pmww.WINDOW_OPEN):#x} wtext={h.wtext().strip()[:70]!r} ticking={h.ticking(1.0)}", flush=True)
dbg0 = h.debug
h.debug = lambda s, wait=0.8: "" if s.strip() == "b all" else dbg0(s, wait)
try:
    h.boot_to_options(log=print)
    time.sleep(2)
    h.options_to_map(noprot=True, swap=False, log=print)
    time.sleep(2); st("map")
    for k, a, c, sc in (("ent", 0x1cac4, "", "e VBL\nm $e662 2\n"), ("rd", 0x1cb2a, "", "e VBL\n"), ("sec", 0x7740c, "", "e VBL\nr\n"),
                        ("btn", 0xef4, " && ($1d2af).b > 0", "e VBL\nm $1d2af 1\nm $2edb2 4\nm $74c0 2\n")):
        (h.R / f"tr_{k}.txt").write_text(sc)
        h.cmd(f"hatari-debug b pc = ${a:x}{c} :trace :file {h.R / f'tr_{k}.txt'}")
    if mode == "load":
        try:
            r = h.saveload_hd(log=print); print(r, flush=True)
        except RuntimeError as e:
            print("EXC", e, flush=True)
            print("ticking", h.ticking(2.0), "WINDOW_OPEN", hex(h.peekw(pmww.WINDOW_OPEN)), flush=True)
            sd = h.host_savedisk(); rm = bytes(h.ram(0x1c860, 0x200))
            print("disk flag@104", sd[0x104], "len", len(sd), "sector0 on disk == RAM block:", sd[:512] == rm, "ram flag", rm[0x104], flush=True)
            print("disk sector0:", sd[:512].hex()[:64], "ram:", rm.hex()[:64], flush=True)
            h.debug("r", 1.0)
            h.debug("b", 1.0); h.debug("m $c2000 64", 1.0); h.debug("m $1cb20 16", 1.0)
            time.sleep(1)
            print("".join(open(Path(wd)/"log.txt").read().splitlines(True)[-25:]), flush=True)
            raise
        time.sleep(3); st("afterload")
    h.click_st(*pmww.OPTION_XY, wait=2.5); st("opt")
    h.click_st(*pmww.GAME_BTN_XY, wait=2.5); st("game")
    h.click_st(*pmww.RETIRE_BTN_XY, wait=3.0); st("retire")
    time.sleep(10); st("retire10")
finally:
    h.close() if hasattr(h, "close") else None
