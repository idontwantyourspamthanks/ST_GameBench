from nt import *
h=boot()
try:
    time.sleep(3)
    h.shot(T+'shots/c0.png')
    h.debug("b ($38498).b ! ($38498).b :trace",0.5)
    h.key('Right',hold=0.5); time.sleep(0.5)
    h.key('Control_R',hold=1.0); time.sleep(1)
    h.debug("b all",0.3)
    print(h._logtext()[-900:])
    print(h.debug("m $338f0 4",0.5))
    h.shot(T+'shots/c1.png')
finally:
    h.close()
