import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
from pathlib import Path
which,nth=sys.argv[1],int(sys.argv[2])
R=Path('/home/ryan/Code/AtariST/midwinter2')
h=Hatari(snapshot=str(R/'work/snapshots/1mb_ingame_walking.sav'))
try:
    h.capture_frames(f'/tmp/p3b/cap/{which}{nth}',live=f'/tmp/p3b/live/{which}',at_vbl=21600,nth_flip=nth)
finally: h.close()
