"""Cold boot BUILD; at VBL>N dump regs, video regs, palette and RAM to work/credit/OUT_*"""
import sys, time, os
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
build, N, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
h = Moonshine(machine='ste', memsize_kb=1024, game_dir=GAME / build, tos=TOS['1.62'])
base = os.path.abspath('work/credit')
try:
    f = h.R / "cap.txt"
    f.write_text(f"r\nm $ff8200 16\nm $ff8240 32\nsavebin {base}/{tag}.bin 0 $100000\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {N} :trace :once :file {f}")
    t=time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:] or not os.path.exists(f"{base}/{tag}.bin"):
        time.sleep(0.5)
        if time.time()-t>200: break
    time.sleep(2)
    open(f"{base}/{tag}.log","w").write(h._logtext()[start:])
finally:
    h.close()
