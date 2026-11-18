import sys,time,re,os,struct
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
L=G+'work/level/'
def boot(workdir='/tmp/strun-nl1', **kw):
    h=Nebulus(workdir=workdir, **kw)
    h.boot_to_game(shots=None)
    return h
def cheat(h):
    for c in 'helloiamjmp':
        h.key(c,hold=0.4); time.sleep(0.15)
def grab(h,a,n,name='x'):
    p=f'/tmp/nl_{name}.bin'
    if os.path.exists(p): os.remove(p)
    h.debug(f"savebin {p} ${a:x} ${n:x}",0.8)
    for _ in range(40):
        if os.path.exists(p) and os.path.getsize(p)==n: break
        time.sleep(0.2)
    time.sleep(0.2)
    d=open(p,'rb').read(); os.remove(p); return d
def words(d): return struct.unpack('>%dH'%(len(d)//2),d)
