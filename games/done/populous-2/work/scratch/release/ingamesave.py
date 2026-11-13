import re, shutil, sys, time
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
which = sys.argv[1]
h = Populous2(**({"game_dir": G / "build/Pop2Release"} if which == "ours" else {}))
try:
    ok = h.boot_to_game(); print(which, "in_play", ok, "marker", repr(h.marker()), flush=True)
    time.sleep(3)
    h.goto(HOME[0] + 2 * 301, HOME[1] + 2 * 156, HOME); h.click(hold=0.3); time.sleep(3)
    h.shot(str(G / f"work/shots/rel_save_{which}_req.png"))
    h.goto(498, 178, HOME); h.click(hold=0.4); time.sleep(6)
    try: h.shot(str(G / f"work/shots/rel_save_{which}_after.png")); alive = True
    except Exception: alive = False
    try: pc = f"$70={h.peekl(0x70):#x}"
    except Exception: pc = "debugger not answering (machine halted/crashed)"
    print(which, "after SAVE GAME click:", pc, "| screenshot ok:", alive)
    for l in [l for l in h._logtext().splitlines() if BAD.search(l)]: print("  ", l)
finally:
    h.close()
