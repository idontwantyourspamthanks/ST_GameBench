#!/usr/bin/env python3
"""Cold boot of the ORIGINAL floppy images (FILES/FFA..) with breakpoints on the music API + polled VBL/tick. usage: trace_fl.py OUTDIR [secs]"""
import sys, time, re, os, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
secs = int(sys.argv[2]) if len(sys.argv) > 2 else 240
os.environ["SDL_AUDIODRIVER"] = "dummy"
scratch = Path("/tmp/fl/music_fl"); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
shutil.copy(ROOT/"FILES/FFA", scratch/"A.st"); shutil.copy(ROOT/"FILES/FFB", scratch/"B.st"); shutil.copy(ROOT/"work/disk_overlay/FILES/FFD", scratch/"D.st")
empty = scratch/"empty"; empty.mkdir()
h = Hatari(snapshot=None, memsize_kb=1024, machine="ste", game_dir=empty, extra=["--disk-a", str(scratch/"A.st"), "--disk-b", str(scratch/"D.st")])
BPS = {"ym_start_c6c": 0xc6c, "ym_stop_c4c": 0xc4c, "stop_5032": 0x33870, "stop_restore_502c": 0x338c2, "start_tune": 0x321fe, "setvec_3225c": 0x3225c,
       "fadeout_322d6": 0x322d6, "stub_tune_4dac8": 0x4dac8, "stub_jmp_4daa0": 0x4daa0, "game_entry_3104": 0x3104}
t0 = time.time()
try:
    for name, a in BPS.items():
        f = h.R / f"bp_{name}.txt"
        f.write_text("e VBL\nr\nm a7 16\nm $7626 2\nm $b96 4\nm $5138 4\n")
        h.cmd(f"hatari-debug b pc = ${a:x} :trace :file {f}"); time.sleep(0.2)
    tl = open(out/"timeline.txt", "w"); n = 0
    while time.time() - t0 < secs:
        time.sleep(4)
        n0 = len(h._logtext())
        h.cmd("hatari-debug e VBL"); h.cmd("hatari-debug m $5138 4"); time.sleep(1.5)
        txt = h._logtext()[n0:]
        v = re.search(r"#(\d+) \(dec\)", txt); mm = re.search(r"^00005138:\s+((?:[0-9a-f]{2} )+)", txt, re.M)
        tl.write(f"t={time.time()-t0:6.1f} VBL={v.group(1) if v else '?'} 5138={''.join(mm.group(1).split()) if mm else '?'}\n"); tl.flush()
        n += 1
        if n % 5 == 0: shutil.copy(h.shot(), out / f"s{int(time.time()-t0):04d}.png")
    shutil.copy(h.logpath, out / "hatari_log.txt")
finally:
    h.close()
