"""RAM dump (1 MB savebin) at the first race-loop pass $7a88 with the car moving after the restart of level L (poke $102c, up held at every pass).
python3 dumplevel.py L OUT.bin"""
import sys
from mxlib import *
L, out = int(sys.argv[1]), Path(sys.argv[2]).resolve()
h = open_snap("ste1m_race_drive.sav", 8)
try:
    (h.R / "hold.txt").write_text("w $6105 $01\n")
    (h.R / "dump.txt").write_text(f"savebin {out} 0 $100000\n")
    apply_names(h, None, "A", pokes=[(0x102c, bytes([L >> 8, L & 255])), (0x6105, b"\x01")])
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = $7a88 :trace :file {h.R}/hold.txt")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b ($130c).w > 6 && ($100e).w > 40 && ($100e).w < 900 && pc = $7a88 :trace :once :file {h.R}/dump.txt")
    t0 = time.time()
    while not out.exists():
        if time.time() - t0 > 400: raise TimeoutError
        time.sleep(1)
    time.sleep(2)
    print("level", L, "dump", out.stat().st_size, "pass", h.peekw(0x100e), "$102c", h.peekw(0x102c))
finally:
    h.close()
