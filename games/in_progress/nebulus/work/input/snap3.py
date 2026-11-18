from lib import *
h = Nebulus(snapshot='snap/own_tower.sav', workdir='/tmp/strun-nin2a')
try:
    t0=time.time()
    while time.time()-t0<20:
        if h.peekw(0x3ad98)==0x20 and h.peekw(0x3ad9a)==0x0: break
    print('at', time.time()-t0, hex(h.peekw(0x33a20)), hex(h.peekw(0x3390c)))
    h.savemem('snap/play_enemy.sav'); print('saved')
finally:
    h.close()
