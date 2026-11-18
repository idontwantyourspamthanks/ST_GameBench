from nl2 import *
from pathlib import Path
h=Nebulus(workdir='/tmp/strun-nl2', game=Path(G+'work/level/patched_time'))
try:
    ok=h.boot_to_game(shots=None); print('in tower',ok,flush=True)
    print('timer words',[hex(h.peekw(0x3ad98+2*i)) for i in range(3)],'table',grab(h,0x3ad9e,4,'t').hex(),flush=True)
    h.shot(L+'shots/patched_time.png')
finally:
    h.close()
