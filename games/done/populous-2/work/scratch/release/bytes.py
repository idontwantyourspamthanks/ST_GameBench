import sys,time
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
d=sys.argv[1]; out=sys.argv[2]
h=Populous2(**({"game_dir":G/d} if d!="stock" else {}))
try:
    print("in_play",h.boot_to_game(),"marker",h.marker())
    h.dump(out,0x2a900,0x1a0); time.sleep(1); print(Path(out).stat().st_size)
finally: h.close()
