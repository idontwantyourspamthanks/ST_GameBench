import sys,re,time
from pathlib import Path
G=Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0]=[str(G/"tools"),"/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2
from stharness import TOS
kw=({"game_dir":G/sys.argv[1]} if sys.argv[1]!="stock" else {})
if len(sys.argv)>2: kw.update(machine=sys.argv[2],tos=TOS[sys.argv[3]])
h=Populous2(**kw)
try:
    ok=h.boot_to_game(); print("in_play",ok)
    for l in h._logtext().splitlines():
        if re.search(r"bus error|address error|exception",l,re.I): print(l)
finally: h.close()
