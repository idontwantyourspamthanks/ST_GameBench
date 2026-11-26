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
    for i,(x,y) in enumerate(zip(sys.argv[6::2],sys.argv[7::2])):
        h.move(int(x),int(y)) if int(x)>=0 else (h.xdo('mousemove_relative','--','-60','-50'),time.sleep(0.5)); print(h.shot(f"m{i}"))
finally: h.close()
