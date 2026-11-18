from nt import *
h=boot_tower()
try:
    t0=time.time()
    while time.time()-t0<30:
        time.sleep(0.4)
        if w(h,0x33938)==1 and w(h,0x33a20)==0: break
    print('play state', w(h,0x33938), w(h,0x33a20), w(h,0x3390c), words(grab(h,0x3ad98,6,'t')), 'vbl',h.vbl())
    h.shot(T+'shots/play0.png')
    h.savemem(T+'snap/play1mb.sav')
    print('saved')
finally:
    h.close()
