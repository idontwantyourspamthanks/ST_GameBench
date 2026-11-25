# STE HD: boot to the idle map of the 2nd land (after save/load, Retire lose, START NEW), snapshot, then N x (forced-win Retire with random click holds; exception + bad-packet capture;
# restore the snapshot).  IKBD traffic traced to <wd>/ikbd.trace.
import sys, time, re, os, random
from pathlib import Path
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1/tools")
import pmww, wwhd
hd, wd, N = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
random.seed(int(sys.argv[4]) if len(sys.argv) > 4 else 1)
Path(wd).mkdir(parents=True, exist_ok=True)
import subprocess
TR = wd + "/acia.trace"
if not os.path.exists(wd + "/acia.fifo"): os.mkfifo(wd + "/acia.fifo")
flt = subprocess.Popen(f"grep --line-buffered -a 'read fffc02\\|write fffc02\\|overrun' < {wd}/acia.fifo >> {TR}", shell=True)
h = wwhd.PMWHD(hd, workdir=wd, machine="ste", tos=pmww.TOS["1.62"], memsize_kb=1024, extra=["--trace", "acia", "--trace-file", wd + "/acia.fifo"])
try:
    h.boot_to_options(log=print); time.sleep(2)
    h.options_to_map(noprot=True, swap=False, log=print); time.sleep(2)
    print(h.saveload_hd(log=print), flush=True)
    h.retire(win=False, log=print); time.sleep(14)
    h.click_st(160, 100, wait=4); print("options:", h.wait_text("Welcome to the World", timeout=20), flush=True)
    h.click_st(*pmww.START_NEW_XY, wait=3.0); h.chart_to_map(log=print, noprot=True)
    print("2nd land ticking", h.ticking(2.0), flush=True)
    snap = h.R / "snap.sav"
    h.debug(f"statesave {snap}", 4.0)
    print("snapshot", snap.exists() and snap.stat().st_size, flush=True)
    dump = "e VBL\ne HBL\nr\nm a7 96\nm $1d2ae 8\nm $2edb0 16\nm $c2000 48\nm $c2100 64\n"
    (h.R / "exc.txt").write_text(dump)
    (h.R / "bad.txt").write_text(dump)
    cmd0 = h.cmd
    def cmd(s):
        if "pc = $d6c8" in s:
            (h.R / "win.txt").write_text(f"w ${pmww.RETIRE_STATE:x} $00 $04\ne VBL\ne HBL\n")
            cmd0(f"hatari-debug b pc = ($c).l :trace :once :file {h.R / 'exc.txt'}"); time.sleep(0.2)
            cmd0(f"hatari-debug b pc = ($8).l :trace :once :file {h.R / 'exc.txt'}"); time.sleep(0.2)
            cmd0(f"hatari-debug b pc = $75c00 && ($1d2b1).b > $f :trace :file {h.R / 'bad.txt'}"); time.sleep(0.2)
        return cmd0(s)
    h.cmd = cmd
    bad = 0
    for t in range(N):
        hold = random.choice([0.08, 0.12, 0.16, 0.2, 0.2, 0.25, 0.3])
        os.environ["WW_CLICK_HOLD"] = str(hold)
        time.sleep(random.random() * 0.6)
        open(TR, "w").close()
        mark = len(h._logtext())
        h.retire(win=True, log=print)
        time.sleep(7)
        txt = h._logtext()[mark:]
        exc = re.findall(r"(?:Address|Bus) Error[^\n]*", txt)
        badpk = txt.count("bad.txt'...")
        cur = h.peekl(pmww.CACHE_CURSOR)
        print(f"trial {t} hold {hold}: vbl {h.vbl()} cursor ${cur:x} bp hit {'w $5a830' in txt} bad-button packets {badpk} exceptions {exc[:2]}", flush=True)
        if exc or badpk:
            bad += 1
            (Path(wd) / f"crash_{t}.txt").write_text(txt)
            import shutil; shutil.copy(TR, wd + f"/crash_{t}_acia.trace")
            h.shot(str(Path(wd) / "shots" / f"crash_{t}.png"))
        h.debug("b all", 0.3)
        h.debug(f"stateload {snap}", 3.0)
        time.sleep(1.0)
    print(f"DONE {N} trials, {bad} with exceptions / bad packets", flush=True)
finally:
    h.close()
