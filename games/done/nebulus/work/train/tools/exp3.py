import sys
from nt import *
off=sys.argv[1]=='off'
y=int(sys.argv[2]) if len(sys.argv)>2 else 168
h=boot_tower()
def S(tag):
    print(tag,'x',w(h,0x33a16),'y',w(h,0x33a18),'st',w(h,0x33a20),'sub',w(h,0x33a1e),'33a46',w(h,0x33a46),'tower',w(h,0x3390c),'run',w(h,0x33938),'timer',words(grab(h,0x3ad98,6,'t')),'states',words(grab(h,0x3398c,8,'s')),flush=True)
try:
    t0=time.time()
    while time.time()-t0<40:
        time.sleep(0.3)
        if w(h,0x33938)==1 and w(h,0x33a20)==0: break
    S('ready')
    if off:
        h.debug('w $3792c $4e $75',0.3); h.debug('w $3398c 0 0 0 0 0 0 0 0',0.3)
    # gentle teleport: rotate to x=32 then climb in 4-unit steps (a single 164-unit jump hangs the game, see exp3 run 1)
    for x in range(4,33,4):
        h.debug(f'w $33a16 0 {x}',0.12)
    for yy in range(12,y+1,4):
        h.debug(f'w $33a18 0 {yy}',0.12)
    for i in range(5):
        time.sleep(0.4); S(f'tp{i}')
    h.shot(T+f'shots/door_{sys.argv[1]}_a.png')
    h.key('Up',hold=0.4)
    for i in range(8):
        time.sleep(0.8); S(f'up{i}')
        if i in (1,3,6): h.shot(T+f'shots/door_{sys.argv[1]}_{i}.png')
finally:
    h.close()
