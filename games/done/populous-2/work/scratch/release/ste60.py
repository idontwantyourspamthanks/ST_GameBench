import re, shutil, sys, time
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME
from stharness import TOS
import p2tick as TK
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
h = Populous2(game_dir=G / "build/Pop2Release", machine="ste", tos=TOS["2.06"], memsize_kb=2048)
try:
    ok = h.boot_to_game()
    sync = TK.rdb(h, 0xFF820A, 1)[0]
    print(f"STE TOS 2.06 2 MB: in_play={ok} marker={h.marker()!r} sync=${sync:02x} ({TK.sync_hz(sync)} Hz) turn={h.peekw(h.TURN)} $70={h.peekl(0x70):#x}", flush=True)
    t0 = h.peekw(h.TURN)
    # bottom edge: push the pointer down (and sweep left-right) for ~20 s
    for i in range(6):
        h.rel(0, 600, 20); time.sleep(0.5)
        h.rel(-300 if i % 2 else 300, 0, 10); time.sleep(0.5)
        h.rel(0, 600, 20)
        print(f"  pass {i}: pointer {h.peekw(0x393FA)},{h.peekw(0x393FC)} turn {h.peekw(h.TURN)}", flush=True)
        time.sleep(1.5)
    h.shot(str(G / "work/shots/rel_ste60_bottom.png"))
    time.sleep(3)
    print("turn", t0, "->", h.peekw(h.TURN), "in_play", h.in_play())
    bad = [l for l in h._logtext().splitlines() if BAD.search(l)]
    print("bus/address errors:", len(bad)); print("\n".join(bad[:6]))
finally:
    shutil.copy(h.logpath, G / "work/gates/rel_ste60.log"); h.close()
