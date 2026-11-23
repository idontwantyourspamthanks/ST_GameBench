import sys,time,re,os,struct
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/done/nebulus/tools')
from nebulus import Nebulus
G='/home/ryan/Code/AtariST/gamebench/games/done/nebulus/'
E=G+'work/editor/'
def grab(h,a,n,name='x'):
    p=f'/tmp/ned_{os.getpid()}_{name}.bin'
    for attempt in range(5):
        if os.path.exists(p): os.remove(p)
        h.debug(f"savebin {p} ${a:x} ${n:x}",0.4)
        for _ in range(30):
            if os.path.exists(p) and os.path.getsize(p)==n:
                time.sleep(0.05)
                d=open(p,'rb').read(); os.remove(p); return d
            time.sleep(0.1)
    raise RuntimeError('grab failed')
def L(h,a): return struct.unpack('>L',grab(h,a,4))[0]
def W(h,a): return struct.unpack('>H',grab(h,a,2))[0]
def poke(h,a,data):
    for i in range(0,len(data),8):
        c=data[i:i+8]
        h.debug(f"w ${a+i:x} "+" ".join(f"${b:02x}" for b in c),0.15)
def snap(workdir,path=G+'work/snapshots/1mb_tower.sav',**kw):
    return Nebulus(snapshot=path,workdir=workdir,**kw)
