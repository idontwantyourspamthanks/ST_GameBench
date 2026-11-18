from nl2 import *
from pathlib import Path
h=Nebulus(workdir='/tmp/strun-nl2', game=Path(G+'work/level/patched'))
try:
    t=time.time(); ok=h.boot_to_game(shots=None); print('in tower',ok,round(time.time()-t,1),flush=True)
    print('timer',[hex(h.peekw(0x3ad98+2*i)) for i in range(3)],'tower',hex(h.peekw(0x3390c)),flush=True)
    print('RAM 43c15..43c1c', grab(h,0x43c15,8,'p').hex(),flush=True)
    print('grid row h1', grab(h,0x327f0+0x100*0+1,1,'q').hex(), flush=True)
    for k in (5,6,7,8,9):
        print('grid ang',k,'h1 =',grab(h,0x327f0+0x100*k+1,1,'g').hex(),flush=True)
    time.sleep(1)
    h.shot(L+'shots/patched_boot.png')
finally:
    h.close()
