"""boot the game with an ovl as the boot-time store, F10 -> Campaigns -> first campaign -> Play, snapshot at the level start"""
import sys; sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/example')
from xlib import *
ovlp = sys.argv[1]; wd = sys.argv[2]; snapout = sys.argv[3]; camp = int(sys.argv[4]) if len(sys.argv) > 4 else 0
gd = gamedir_with(ovlp, 'g_' + os.path.basename(wd))
h = Nebulus(workdir=wd, game=gd)
try:
    print('title', h.boot_to_title(timeout=120), flush=True); time.sleep(3)
    h.key('F10', hold=0.5); time.sleep(2)
    K(h, 'Down'); F(h, 1.0); h.shot(X + 'x01_camps.png')
    K(h, 'Down', camp); F(h, 1.0); h.shot(X + 'x01_camp.png'); F(h, 1.0)
    print('playing', wait_play(h), flush=True)
    print(frog(h))
    h.shot(X + 'x01_start.png')
    h.savemem(snapout)
    print('saved', snapout)
finally:
    h.close()
