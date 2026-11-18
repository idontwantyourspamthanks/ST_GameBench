import sys,time,re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
T=G+'work/train/'
def boot(workdir='/tmp/strun-nt1', **kw):
    h=Nebulus(workdir=workdir, **kw)
    t0=time.time()
    # wait until game data is in RAM (title strings)
    while time.time()-t0<90:
        time.sleep(2)
        out=h.debug("m $3d00f 4",0.5)
        if '48 69 67 68' in out or 'Higl' in out or re.search(r'3D00F:\s+48 69 67 68',out,re.I): break
        h.keypress(57)
    return h
def hexm(h,a,n):
    out=h.debug(f"m ${a:x} {n}",0.6)
    return out

import struct
def snapshot_open(path=T+'snap/tower1mb.sav', workdir='/tmp/strun-nt2'):
    return Nebulus(snapshot=path, workdir=workdir)
def grab(h, a, n, name):
    p=f'/tmp/nt_{name}.bin'
    h.debug(f"savebin {p} ${a:x} ${n:x}",0.6)
    import os
    for _ in range(20):
        if os.path.exists(p) and os.path.getsize(p)==n: break
        time.sleep(0.2)
    d=open(p,'rb').read(); os.remove(p); return d
def words(d): return struct.unpack('>%dH'%(len(d)//2),d)

def boot_tower(workdir='/tmp/strun-nt3', **kw):
    """Proven recipe: cold boot, ONE space after 16 s (ends HW-detect), 24 s attract, hold Right Ctrl 1 s."""
    h=Nebulus(workdir=workdir, **kw)
    time.sleep(16); h.keypress(57); time.sleep(24)
    h.key('Right',hold=0.5); time.sleep(0.5)
    h.key('Control_R',hold=1.0)
    return h
def w(h,a): return words(grab(h,a,2,'w'))[0]
