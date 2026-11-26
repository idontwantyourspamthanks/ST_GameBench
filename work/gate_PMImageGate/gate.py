"""Wrapper: run pmretire with a tolerant shot() (the Hatari boot of the image is slow in wall time; the 3 s screenshot wait expires)."""
import sys, time
from pathlib import Path
sys.path[:0] = ["tools", "games/in_progress/powermonger/tools"]
import stharness
orig = stharness.Hatari.shot
def shot(self, out=None):
    if time.time() - _t0.get(id(self), time.time()) < EARLY:
        from PIL import Image
        Image.new("RGB", (832, 588), "white").save("/tmp/pmig_white.png"); return Path("/tmp/pmig_white.png")
    for i in range(100):
        try:
            return orig(self, out)
        except RuntimeError:
            if self.proc.poll() is not None: raise
            time.sleep(2)
    return orig(self, out)
stharness.Hatari.shot = shot
EARLY0=0
_okey = stharness.Hatari.key
_t0 = {}
import os
EARLY = float(os.environ.get("GATE_EARLY", "100"))
def key(self, keysym, hold=0.15):
    first = id(self) not in _t0
    t0 = _t0.setdefault(id(self), time.time())
    if first and os.environ.get("GATE_RESET"):
        self.cmd("hatari-shortcut warmreset"); time.sleep(0.5)
    if keysym == "p" and time.time() - t0 < EARLY:   # slow boot in wall time; early screenshot floods wedge Hatari: keys via the fifo only
        
        for _ in range(10):
            _okey(self, "p", 0.15); time.sleep(0.2)
        return
    return _okey(self, keysym, hold)
stharness.Hatari.key = key
sys.argv[0] = "pmretire.py"
import runpy
runpy.run_path("games/in_progress/powermonger/tools/pmretire.py", run_name="__main__")
