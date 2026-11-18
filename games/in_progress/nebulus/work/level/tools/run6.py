from nl2 import *
h=Nebulus(workdir='/tmp/strun-nl2')
try:
    ok=h.boot_to_title(); print('title',ok,flush=True)
    time.sleep(2)
    h.shot(L+'shots/n_title.png')
    print('33910',hex(h.peekw(0x33910)),'3390c',hex(h.peekw(0x3390c)),flush=True)
    cheat(h); time.sleep(1)
    print('cheatflag 33a40',hex(h.peekw(0x33a40)),flush=True)
    h.shot(L+'shots/n_cheat.png')
    h.key('F2',hold=0.6)
    for i in range(30):
        time.sleep(1)
        if h.peekw(0x3ad98): break
    time.sleep(3)
    print('timer',[hex(h.peekw(0x3ad98+2*i)) for i in range(3)],'tower',hex(h.peekw(0x3390c)),'m',hex(h.peekw(0x33910)),flush=True)
    h.shot(L+'shots/n_f2.png')
    d=grab(h,0,0x80000,'f2'); open(L+'dumps/f2.bin','wb').write(d)
finally:
    h.close()
