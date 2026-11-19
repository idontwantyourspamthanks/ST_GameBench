from nl import *
h=boot()
try:
    h.shot(L+'shots/r1_title.png')
    cheat(h); time.sleep(1)
    h.shot(L+'shots/r1_cheat.png')
    h.key('F1',hold=0.6); time.sleep(3)
    h.shot(L+'shots/r1_f1a.png')
    time.sleep(5)
    h.shot(L+'shots/r1_f1b.png')
    print([hex(x) for x in words(grab(h,0x3390c,2))])
    d=grab(h,0,0x80000,'f1'); open(L+'dumps/f1_a.bin','wb').write(d)
finally:
    h.close()
