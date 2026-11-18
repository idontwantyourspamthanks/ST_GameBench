import sys
from nt import *
h=boot_tower()
def S(tag):
    print(tag,'frz',hex(w(h,0x76c02)),'noen',hex(w(h,0x76c04)),'prev',hex(words(grab(h,0x76c00,2,'p'))[0]>>8),'st',w(h,0x33a20),'run',w(h,0x33938),'timer',words(grab(h,0x3ad98,6,'t')),'enemy states',words(grab(h,0x3398c,8,'s')),'vbl',h.vbl(),flush=True)
try:
    t0=time.time()
    while time.time()-t0<40:
        time.sleep(0.3)
        if w(h,0x33938)==1 and w(h,0x33a20)==0: break
    h.debug('loadbin /tmp/ntb.bin $76c00',0.6)
    h.debug('w $3dcf4 $4e $b9 $00 $07 $6c $08',0.3)
    h.debug('w $3b0a4 $4e $b9 $00 $07 $6c $40',0.3)
    h.debug('w $3792c $4e $b9 $00 $07 $6c $58',0.3)
    print('blob',h.debug('m $76c08 8',0.5)[-60:])
    S('hooked')
    h.key('e',hold=0.25); time.sleep(0.4); S('after E')
    for i in range(3):
        time.sleep(2.5); S(f'E on +{i}')
    h.shot(T+'shots/hook_noen.png')
    h.key('t',hold=0.25); time.sleep(0.4); S('after T')
    for i in range(3):
        time.sleep(2.5); S(f'T on +{i}')
    h.shot(T+'shots/hook_frz.png')
    h.key('t',hold=0.25); time.sleep(0.4); S('after T again')
    time.sleep(3); S('unfrozen+3s')
    h.key('e',hold=0.25); time.sleep(0.4); S('after E again')
    time.sleep(4); S('enemies back?')
    h.shot(T+'shots/hook_en_back.png')
finally:
    h.close()
