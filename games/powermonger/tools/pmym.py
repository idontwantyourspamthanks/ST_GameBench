#!/usr/bin/env python3
"""WAV capture of a cold boot from the very start (no keys pressed, so the emulation is deterministic and two runs are sample-aligned):
the title/intro music (stage 1's YM sound interrupt, the one fal_ym patches).  Used for the fal_ym A/B (regression.md).

    python3 tools/pmym.py --disk build/rc/floppy/powermonger.st --machine st --tos 1.04 --secs 80 --out /tmp/ym_a.wav
    python3 tools/pmsnd.py cmp A.wav B.wav          # onset / correlation, same tool as the snd.md YM A/B
"""
import argparse, os, shutil, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent.parent / "tools"), str(HERE)]
import pmsnd, pmpatch  # noqa: E402
from pm import TOS  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--disk", required=True); ap.add_argument("--machine", default="st"); ap.add_argument("--tos", default="1.04")
ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--secs", type=int, default=80); ap.add_argument("--out", required=True)
a = ap.parse_args()
tmp = Path(a.out).with_suffix(".d"); tmp.mkdir(exist_ok=True)
pmsnd.TMP, pmsnd.HOME, pmsnd.CAP = tmp, tmp / "home", tmp / "cap.wav"
pmsnd.setup_home()
os.environ["HOME"] = str(pmsnd.HOME); os.environ["SDL_AUDIODRIVER"] = "dummy"
h = pmpatch.make_pm(Path(a.disk), None, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=["--sound", "50066"])
try:
    h.cmd("hatari-shortcut recsound")
    time.sleep(a.secs)
    print("VBL at stop", h.vbl(), "MARKER", h.peekl(pmpatch.MARKER).to_bytes(4, "big"), flush=True)
    h.cmd("hatari-shortcut recsound"); time.sleep(1.5)
finally:
    h.close()
shutil.copy(pmsnd.CAP, a.out)
x, sr = pmsnd.load_wav(a.out)
import numpy as np
print(f"{a.out}: {len(x)/sr:.1f} s, rms {np.std(x):.1f}")
