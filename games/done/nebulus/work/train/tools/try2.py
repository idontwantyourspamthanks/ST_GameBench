import sys,time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
h=Nebulus(snapshot=G+'work/snapshots/hiscores.sav',workdir='/tmp/strun-nt1')
try:
    time.sleep(1)
    h.debug("b ($38498).b ! ($38498).b :trace",0.5)
    h.key('Control_R',hold=1.0); time.sleep(1)
    h.debug("b all",0.3)
    print(h._logtext()[-1500:])
    print(h.debug("m $38498 4",0.5), h.debug("m $338f0 4",0.5))
finally:
    h.close()
