import sys
from nt import *
h=boot_tower()
def S(tag):
    print(tag,'x',w(h,0x33a16),'y',w(h,0x33a18),'st',w(h,0x33a20),'sub',w(h,0x33a1e),'33a46',w(h,0x33a46),'tower',w(h,0x3390c),'run',w(h,0x33938),'timer',words(grab(h,0x3ad98,6,'t')),'states',words(grab(h,0x3398c,8,'s')),flush=True)
try:
    t0=time.time()
    while time.time()-t0<40:
        time.sleep(0.3)
        if w(h,0x33938)==1 and w(h,0x33a20)==0: break
    S('ready')
    h.debug('w $3792c $4e $75',0.3); h.debug('w $3398c 0 0 0 0 0 0 0 0',0.3); h.debug('w $3b0aa $60',0.3)
    # emulate what the door code does ($39e00 / $3a116): level-end flag + player state 4
    h.debug('w $33a46 0 1',0.3); h.debug('w $33a20 0 4 0 0',0.3)  # 33a20=4, 33a22? careful: only 33a20 then 33a1e
    h.debug('w $33a1e 0 0',0.3)
    for i in range(16):
        time.sleep(1.0); S(f'e{i}')
        if i%3==0: h.shot(T+f'shots/end_{i:02d}.png')
finally:
    h.close()
