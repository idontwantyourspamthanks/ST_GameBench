from nl2 import *
h=Nebulus(workdir='/tmp/strun-nl2')
def state(tag):
    return (tag,'timer',[hex(h.peekw(0x3ad98+2*i)) for i in range(3)],'tower',hex(h.peekw(0x3390c)),'mission',hex(h.peekw(0x33910)),'ncols',hex(h.peekw(0x33912)))
try:
    ok=h.boot_to_title(); print('title',ok,flush=True)
    time.sleep(2)
    cheat(h); time.sleep(1)
    print('cheatflag 33a40',hex(h.peekw(0x33a40)),flush=True)
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(4)
    print(state('start'),flush=True)
    h.shot(L+'shots/m1_t1.png')
    d=grab(h,0,0x80000,'t1'); open(L+'dumps/m1_t1.bin','wb').write(d)
    for k,name in (('F2','t2'),('F5','t5')):
        h.key(k,hold=0.6); time.sleep(5)
        print(state(k),flush=True)
        h.shot(L+f'shots/m1_{name}.png')
        d=grab(h,0,0x80000,name); open(L+f'dumps/m1_{name}.bin','wb').write(d)
finally:
    h.close()
