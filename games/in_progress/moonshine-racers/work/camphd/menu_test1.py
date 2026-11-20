#!/usr/bin/env python3
"""First menu test: restore the STE 2 MB title snapshot, load the campaign blobs live, F10, screenshots."""
import sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cplib import *
camp = HERE / "camp"
gd = HERE / "run_gd"; shutil.rmtree(gd, ignore_errors=True); shutil.copytree(HERE / "b2", gd)
shutil.copy(camp / "c3.trk", gd / "FILES" / "MSTRACKS.TRK")
h = start(HERE / "snap/ste2m_title.sav", gd)
try:
    time.sleep(2)
    apply_live(h)
    log("applied; vbl", h.vbl(), "$74fe", mem(h, 0x74fe, 6).hex())
    h.keypress(0x44)
    time.sleep(4)
    h.shot(str(HERE / "snap/menu1_main.png"))
    log("menu1 shot; $102c", mem(h, 0x102c, 2).hex(), "CPV", mem(h, 0xb8e00, 16).hex(), "PC info:", h.debug("r", 1.0)[-400:])
finally:
    h.close()
