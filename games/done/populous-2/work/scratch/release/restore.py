import re, shutil, sys, time
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
saved_turn = int(sys.argv[1])
d = Path("/tmp/p2gs"); shutil.rmtree(d, ignore_errors=True); shutil.copytree(G / "build/Pop2Release", d); shutil.copy("/tmp/GS00.TOS", d / "GS00.TOS")
h = Populous2(game_dir=d, autorun="C:\\GS00.TOS")
try:
    t0 = time.time()
    for i in range(30):
        time.sleep(6)
        try:
            if h.peekl(0x70) == 0x18FA: break
        except IndexError: pass
        h.key("space", 0.5)
    t = h.peekw(h.TURN); time.sleep(4); t2 = h.peekw(h.TURN)
    print(f"restore: {time.time()-t0:.0f}s, $70={h.peekl(0x70):#x} marker={h.marker()!r} turn at save {saved_turn} -> after restore {t} -> +4 s {t2} in_play={h.in_play()}")
    h.shot(str(G / "work/shots/rel_restore.png"))
    bad = [l for l in h._logtext().splitlines() if BAD.search(l)]
    print("bus/address errors:", len(bad)); print("\n".join(bad[:6]))
finally:
    shutil.copy(h.logpath, G / "work/gates/rel_restore.log"); h.close()
