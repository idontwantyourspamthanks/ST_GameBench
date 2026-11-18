from lib import *
h = Nebulus(snapshot='snap/own_tower.sav', workdir='/tmp/strun-nin2a')
try:
    t0=time.time()
    while time.time()-t0<20:
        v=h.peekw(0x3ad98)
        if v==0x20 and h.peekw(0x3ad9a)==0x0:
            break
    print('play at', time.time()-t0, hex(h.peekw(0x33a20)))
    h.debug('w $3792c $4e $75'); h.debug('w $3398c 0 0 0 0 0 0 0 0')
    print(h.debug('m $3792c 4'), h.debug('m $3398c 8'))
    time.sleep(1.0)
    print([hex(h.peekw(a)) for a in (0x3ad98,0x3ad9a,0x33a20,0x3390c,0x38498)])
    h.savemem('snap/play_noenemy.sav')
    h.shot('s/p0.png')
    print('saved')
finally:
    h.close()
