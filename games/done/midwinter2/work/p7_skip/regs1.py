import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
h = Hatari(snapshot='/home/ryan/Code/AtariST/midwinter2/work/snapshots/1mb_ingame_foot.sav', memsize_kb=1024)
try:
    f=h.R/'r.txt'; f.write_text("r\n")
    h.debug("b all",0.3)
    n0=len(h._logtext())
    h.cmd(f"hatari-debug b pc = $315a4 :trace :file {f}")
    h.cmd(f"hatari-debug b pc = $315a8 :trace :file {f}")
    time.sleep(6)
    h.debug("b all",0.3)
    t=h._logtext()[n0:]
    import re
    blocks=re.findall(r'(D0 .*?\n.*?\n.*?A7 [0-9A-F]+)',t,re.S)
    for b in blocks[:4]: print(b.replace('\n',' | '))
finally:
    h.close()
