from lib import *
import collections
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2a')
try:
    time.sleep(1.5)
    print([hex(h.peekw(a)) for a in (0x3ad98,0x3ad9a,0x33a20,0x3390c,0x38498)])
    ev = window(h, ['VBL','POLL','FLIP','CONS'], 40)
    print(' '.join(ev))
    print(collections.Counter(ev))
    print([hex(h.peekw(a)) for a in (0x3ad98,0x3ad9a,0x33a20,0x3390c,0x38498)])
finally:
    h.close()
