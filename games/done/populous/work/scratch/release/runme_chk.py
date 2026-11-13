import sys, time, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "machines"), str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
from mm import start, mem
tb = int(sys.argv[2], 16)          # RUNME text base
h = start("ste", "gemdos", sys.argv[1], tos=sys.argv[3], mem=int(sys.argv[4]))
try:
    f = h.R / "r.txt"; f.write_text("r\n")
    h.cmd(f"hatari-debug b pc = ${tb + 0xaa:x} :trace :once :file {f}")
    time.sleep(10)
    l = h._logtext()
    i = l.find("> r\n"); print(l[i:i + 500])
finally:
    h.close()
