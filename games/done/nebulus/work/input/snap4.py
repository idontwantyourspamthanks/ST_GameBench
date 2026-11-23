from lib import *
h = Nebulus(snapshot='snap/own_tower.sav', workdir='/tmp/strun-nin2a')
try:
    t0=time.time()
    while time.time()-t0<20:
        if h.peekw(0x3ad98)==0x20 and h.peekw(0x3ad9a)==0x0 and h.peekw(0x33a20)==0: break
    print('play at', round(time.time()-t0,2), hex(h.peekw(0x33a20)))
    h.cmd('hatari-debug b pc = $38618 :trace')
    h.key('p', hold=0.2)
    time.sleep(1.0)
    n=len(h._logtext()); time.sleep(0.5)
    t=h._logtext()[n:]
    print('pause loop hits in 0.5s:', t.count('matched'))
    h.debug('b all',0.3)
    print(hex(h.peekw(0x3ad98)), hex(h.peekw(0x33a20)))
    h.savemem('snap/play_pause.sav'); h.shot('s/pause.png'); print('saved')
finally:
    h.close()
