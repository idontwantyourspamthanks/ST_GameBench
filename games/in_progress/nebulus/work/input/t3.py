from lib import *
h = Nebulus(snapshot='snap/own_tower.sav', workdir='/tmp/strun-nin2a')
try:
    time.sleep(3)
    h.shot('s/a0.png')
    print([hex(h.peekw(a)) for a in (0x3ad98,0x33a20,0x3390c,0x38498)])
    h.key('Control_R', hold=0.5)
    for i in range(4):
        time.sleep(1.5); h.shot(f's/a{i+1}.png')
        print(i, [hex(h.peekw(a)) for a in (0x3ad98,0x3ad9a,0x33a20,0x3390c,0x38498)])
finally:
    h.close()
