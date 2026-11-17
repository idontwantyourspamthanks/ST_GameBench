import sys, time, os
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
build = sys.argv[1]
h = Moonshine(machine='ste', memsize_kb=1024, game_dir=GAME / build, tos=TOS['1.62'])
try:
    f = h.R / "pw.txt"; f.write_text("r\n")
    h.cmd(f"hatari-debug b ($ff8242).w ! ($ff8242).w :trace :file {f}")
    time.sleep(70)
    h.debug("b all", 0.5)
    open('work/credit/palwatch.log','w').write(h._logtext())
finally:
    h.close()
