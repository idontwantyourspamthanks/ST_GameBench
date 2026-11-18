from nt import *
h=boot()
try:
    time.sleep(2)
    h.key('Control_R',hold=1.0); time.sleep(4)
    h.shot(T+'shots/tower0.png')
    h.dump(T+'dumps/tower_a.bin',0,0x100000)
    time.sleep(2)
    h.dump(T+'dumps/tower_b.bin',0,0x100000)
    time.sleep(2)
    h.shot(T+'shots/tower1.png')
    h.savemem(T+'snap/tower1mb.sav')
    h.dump(T+'dumps/tower_c.bin',0,0x100000)
finally:
    h.close()
