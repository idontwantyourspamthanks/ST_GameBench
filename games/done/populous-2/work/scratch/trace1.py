import sys, time, re
sys.path.insert(0,'tools')
from populous2 import Populous2
h = Populous2(snapshot=Populous2.SNAP/"busy1.sav")
try:
    R=h.R
    (R/"c.txt").write_text("r\n")
    (R/"end.txt").write_text("b all\ne VBL\n")
    time.sleep(1)
    v=h.vbl()
    start=len(h._logtext())
    h.cmd(f"hatari-debug b pc = $213b0 :trace :file {R/'c.txt'}")
    h.cmd(f"hatari-debug b pc = $212b4 :trace :file {R/'c.txt'}")
    h.cmd(f"hatari-debug b VBL > {v+300} :trace :once :file {R/'end.txt'}")
    h.cmd("hatari-option --fast-forward on")
    t=time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:] and time.time()-t<200: time.sleep(0.5)
    time.sleep(1)
    open('work/scratch/trace1.log','w').write(h._logtext()[start:])
finally:
    h.close()
