import sys,time,os,pathlib
sys.path.insert(0,'..')
import hh
hh.SHOTS=pathlib.Path('.').resolve()
from hh import H
name,machine,tos,mem,mon=sys.argv[1:6]
extra=os.environ.get("EXTRA","").split()
h=H(name,machine,tos,int(mem),mon,'v.img',extra)
try:
    time.sleep(float(os.environ.get("BOOT","30")))
    print(h.geom()); print(h.shot("desktop"))
    W=[int(v) for v in os.environ.get("PIN","830,580").split(",")]; h.move(*W); time.sleep(0.5); h.move(W[0]-1,W[1]-1); time.sleep(0.5); h.shot("pin"); h.move(*[int(v) for v in os.environ["ABS"].split(",")]); time.sleep(0.5); print(h.shot("p0"))
    dx,dy=os.environ["REL"].split(",")
    pass; time.sleep(0.6); print(h.shot("p1"))
    h.dblclick(); time.sleep(4); print(h.shot("cwin"))
    print(open(h.R/'log.txt').read()[-800:])
finally: h.close()
