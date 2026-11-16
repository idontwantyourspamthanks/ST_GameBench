#!/usr/bin/env python3
"""Cold boot of the ORIGINAL HD build with PC breakpoints on the music API; logs hits + a polled state timeline + screenshots.
   usage: trace_hd.py OUTDIR [--machine ste] [--secs 120] [--keys]"""
import sys, time, re, os, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
secs = int(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 120
gd = Path(sys.argv[sys.argv.index("--game") + 1]) if "--game" in sys.argv else ROOT
machine = sys.argv[sys.argv.index("--machine") + 1] if "--machine" in sys.argv else "ste"
os.environ["SDL_AUDIODRIVER"] = "dummy"
BPS = {  # name: addr
    "start_tune": 0x321fe, "ym_start_c6c": 0xc6c, "ym_stop_c4c": 0xc4c, "stop_5032": 0x33870, "stop_restore_502c": 0x338c2,
    "fade_32296": 0x32296, "fadeout_start_3238e": 0x3238e, "fadeout_322d6": 0x322d6, "setvec_d0e_3225c": 0x3225c, "setvec_32288": 0x32288, "setvec_32322": 0x32322,
    "tick_restore_338c6": 0x338c6, "sfx_init_18e32": 0x18e32,
}
h = Hatari(snapshot=None, memsize_kb=1024, machine=machine, game_dir=gd)
t0 = time.time()
try:
    for name, a in BPS.items():
        f = h.R / f"bp_{name}.txt"
        f.write_text("e VBL\nr\nm a7 16\nm $7626 2\nm $b96 4\nm $757c 2\nm $700a 2\n")
        h.cmd(f"hatari-debug b pc = ${a:x} :trace :file {f}")
        time.sleep(0.2)
    n = 0
    keys = "--keys" in sys.argv
    ref = ROOT / "work" / "ref" / "mode_select.png"
    while time.time() - t0 < secs:
        time.sleep(2.0)
        s = h.debug("m $5138 4", 0.3)
        txt = h._logtext()
        n += 1
        if n % 5 == 0:
            try: h.shot(out / f"s{int(time.time()-t0):04d}.png")
            except Exception as e: print("shot", e)
        if keys and n % 6 == 0:
            h.cmd("hatari-event keypress 57")
    shutil.copy(h.logpath, out / "hatari_log.txt")
finally:
    h.close()
