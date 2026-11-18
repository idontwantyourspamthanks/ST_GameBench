from lib import *
h = Nebulus(workdir='/tmp/strun-nin2snap')
try:
    ok = h.boot_to_game()
    print('in tower', ok)
    for i in range(6):
        time.sleep(2)
        print(i, hex(h.peekw(0x3ad98)), hex(h.peekw(0x3ad9a)), hex(h.peekw(0x33a20)), hex(h.peekw(0x3390c)))
    h.shot('s/snap_a.png')
    h.savemem('snap/own_tower.sav')
    print('saved')
    time.sleep(1)
    h.shot('s/snap_b.png')
finally:
    h.close()
