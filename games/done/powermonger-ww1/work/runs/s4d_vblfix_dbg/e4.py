# STE HD: the cell's flow up to the forced-win Retire, with the CPU history switched on at the win breakpoint and dumped at the first address / bus error.
import sys, time, re
from pathlib import Path
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1/tools")
import pmww, wwhd
hd, wd = Path(sys.argv[1]), sys.argv[2]
h = wwhd.PMWHD(hd, workdir=wd, machine="ste", tos=pmww.TOS["1.62"], memsize_kb=1024)
try:
    h.boot_to_options(log=print); time.sleep(2)
    h.options_to_map(noprot=True, swap=False, log=print); time.sleep(2)
    print(h.saveload_hd(log=print), flush=True)
    h.retire(win=False, log=print); time.sleep(14)
    h.click_st(160, 100, wait=4); print("options:", h.wait_text("Welcome to the World", timeout=20), flush=True)
    h.click_st(*pmww.START_NEW_XY, wait=3.0); h.chart_to_map(log=print, noprot=True)
    print("2nd land ticking", h.ticking(2.0), flush=True)
    (h.R / "exc.txt").write_text("e VBL\nr\nm a7 96\nhistory 600\n")
    cmd0 = h.cmd
    def cmd(s):
        if "pc = $d6c8" in s:
            (h.R / "win.txt").write_text(f"w ${pmww.RETIRE_STATE:x} $00 $04\nhistory cpu 2000\n")
            cmd0(f"hatari-debug b pc = ($c).l :trace :once :file {h.R / 'exc.txt'}"); time.sleep(0.2)
            cmd0(f"hatari-debug b pc = ($8).l :trace :once :file {h.R / 'exc.txt'}"); time.sleep(0.2)
        return cmd0(s)
    h.cmd = cmd
    mark = len(h._logtext())
    h.retire(win=True, log=print)
    time.sleep(20)
    h.shot(str(Path(wd) / "shots" / "after_win.png"))
    txt = h._logtext()[mark:]
    print("cursor", hex(h.peekl(pmww.CACHE_CURSOR)), "exceptions:", re.findall(r"(?:Address|Bus) Error[^\n]*", txt)[:4], flush=True)
    (Path(wd) / "win_log.txt").write_text(txt)
finally:
    h.close()
