"""Cold boot BUILD to the race (SPACE, no input), at the first $7b86 with $100e = N save both screen buffers (32000 B each) + state: race frame pixels.
   python3 pix_cold.py BUILD OUTPREFIX N [machine mem tos]"""
import sys, time, os
sys.path.insert(0, 'tools')
import msr
from msr import Moonshine, GAME
from stharness import TOS
build, out, N = sys.argv[1], os.path.abspath(sys.argv[2]), int(sys.argv[3])
machine, mem, tos = (sys.argv[4], int(sys.argv[5]), sys.argv[6]) if len(sys.argv) > 6 else ("ste", 1024, "1.62")
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / build, tos=TOS[tos])
try:
    ok = h.boot_to_race(log=lambda *a: None)
    h.keypress(57)
    t0 = time.time(); fc = []
    while time.time() - t0 < 120:
        time.sleep(3); fc.append(h.peekw(0x100e))
        if len(fc) > 3 and fc[-1] > 40: break
    f = h.R / "pix.txt"
    f.write_text(f"savebin {out}_70000.bin $70000 $7d00\nsavebin {out}_78000.bin $78000 $7d00\nm $ff8240 32\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7b86 && ($100e).w = {N} :trace :once :file {f}")
    t0 = time.time()
    while not os.path.exists(f"{out}_78000.bin") and time.time() - t0 < 300: time.sleep(1)
    time.sleep(2)
    print("saved", os.path.exists(f"{out}_78000.bin"), "counter", h.peekw(0x100e), "vbl", h.vbl())
    open(out + ".log", "w").write(h._logtext()[start:])
finally:
    h.close()
