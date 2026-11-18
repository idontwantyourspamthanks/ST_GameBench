import sys
from nt import *
off=sys.argv[1]=='off'
y=int(sys.argv[2]) if len(sys.argv)>2 else 168
h=snapshot_open(T+'snap/play1mb.sav',workdir='/tmp/strun-nt2')
def S(tag):
    p=words(grab(h,0x33a16,0x32,'p'))   # 33a16..
    lv=words(grab(h,0x33a46,2,'l'))
    print(tag,'x',p[0],'y',p[1],'state33a20',p[2],'sub33a1e',p[2-1+0] if False else words(grab(h,0x33a1e,2,'q'))[0],'33a46',lv[0],'tower',words(grab(h,0x3390c,2,'z'))[0],'timer',words(grab(h,0x3ad98,6,'t')),flush=True)
try:
    time.sleep(1.5)
    if off:
        h.debug('w $3792c $4e $75',0.4); h.debug('w $3398c 0 0 0 0 0 0 0 0',0.4)
    S('start')
    h.debug(f'w $33a16 0 32 0 {y}',0.5)  # x=32,y
    for i in range(4):
        time.sleep(0.5); S(f'tp{i}')
    h.shot(T+f'shots/door_{sys.argv[1]}_0.png')
    h.key('Up',hold=0.4)
    for i in range(6):
        time.sleep(0.7); S(f'up{i}')
        if i in (1,3,5): h.shot(T+f'shots/door_{sys.argv[1]}_{i}.png')
finally:
    h.close()
