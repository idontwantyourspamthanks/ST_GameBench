"""boot once per level: F10 -> Campaigns -> camp k -> Play, snapshot at the level start. usage: x04_snaps.py OVL CAMPIDX OUT.sav WD"""
import sys; sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/example')
from xlib import *
ovlp, camp, out, wd = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
gd = gamedir_with(ovlp, 'g_' + os.path.basename(wd))
h = Nebulus(workdir=wd, game=gd)
try:
    print('title', h.boot_to_title(timeout=120), flush=True); time.sleep(3)
    h.key('F10', hold=0.5); time.sleep(2)
    K(h, 'Down'); F(h, 1.0)
    K(h, 'Down', camp); F(h, 1.0); F(h, 1.0)
    # enter the tower and save as early as possible (the frog dies by itself without input): poll the intro
    t0 = time.time()
    while time.time() - t0 < 60:
        if W(h, 0x33a20) == 0 and W(h, 0x33938) == 1: break
        time.sleep(0.3)
    print(frog(h)); h.shot(out.replace('.sav', '.png')); h.savemem(out)
finally: h.close()
