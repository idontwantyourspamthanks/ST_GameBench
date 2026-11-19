import sys,time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
h=Nebulus(snapshot=G+'work/snapshots/hiscores.sav',workdir='/tmp/strun-nt1')
try:
    time.sleep(2); h.shot(G+'work/train/shots/t0.png')
    print(h.vbl())
    # hold right ctrl (fire) via xdotool
    h.key('Control_R',hold=1.0); time.sleep(3); h.shot(G+'work/train/shots/t1.png')
    h.key('KP_0',hold=1.0); time.sleep(3); h.shot(G+'work/train/shots/t2.png')
    h.key('Alt_R',hold=1.0); time.sleep(3); h.shot(G+'work/train/shots/t3.png')
finally:
    h.close()
