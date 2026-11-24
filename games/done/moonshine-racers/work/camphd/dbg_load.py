import sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cplib import *
camp = HERE / "camp"
gd = HERE / "run_dbg"; shutil.rmtree(gd, ignore_errors=True); shutil.copytree(HERE / "b2", gd)
shutil.copy(camp / "c3.trk", gd / "FILES" / "MSTRACKS.TRK")
h = start(HERE / "snap/ste2m_title.sav", gd)
try:
    time.sleep(2); apply_live(h)
    # breakpoint at validate entry: find label address from the listing: use the blob assembly with a symbol listing? approximate: break after trk_read returns -> simply dump
    h.keypress(0x44); time.sleep(3); h.keypress(0x50); time.sleep(0.6); h.keypress(0x1c); time.sleep(8)
    f = (camp / "c3.trk").read_bytes()
    got = mem(h, 0x110000, 64)
    log("store head", got.hex()); log("file head ", f[:64].hex())
    log("CPV", mem(h, 0xb8e00, 16).hex(), "msg ptr", mem(h, 0x10040a, 4).hex())
    log("full compare", mem(h, 0x110000, len(f)) == f)
finally:
    h.close()
