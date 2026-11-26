import sys,time,shutil,os
sys.path.insert(0,'..')
import hh
hh.SHOTS=__import__('pathlib').Path('.').resolve()
from hh import H
name,machine,tos,mem,mon=sys.argv[1:6]
h=H(name,machine,tos,int(mem),mon,'v.img')
try:
    time.sleep(float(os.environ.get("BOOT","30"))); print(h.shot("desktop"))
    if len(sys.argv)>7:
        h.move(int(sys.argv[6])*2,int(sys.argv[7])*2); h.dblclick(); time.sleep(3); print(h.shot("cwin"))
    print(open(h.R/'log.txt').read()[-1500:])
finally: h.close()
