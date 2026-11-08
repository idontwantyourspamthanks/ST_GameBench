import sys,json,time,re
sys.path.insert(0,'/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
from pathlib import Path
which=sys.argv[1]
R=Path('/home/ryan/Code/AtariST/midwinter2')
h=Hatari(snapshot=None,memsize_kb=1024,game_dir=R/('build/p3b_default' if which=='B' else 'build/p3b_A'))
def peekl(a):
    out=h.debug(f"m ${a:x} 4",0.6)
    m=re.findall(rf"{a:08x}:\s+((?:[0-9a-f]{{2}} ?){{4}})",out,re.I)[-1]
    return int(m.replace(' ',''),16)
def sw(x): return x-65536 if x>=32768 else x
def rate(vbls=500):
    v0=h.vbl(); d0=h.peekw(0x6888); x0=peekl(0x66e6); y0=peekl(0x66ea)
    f=h.fps(vbls)
    v1=h.vbl(); d1=h.peekw(0x6888); x1=peekl(0x66e6); y1=peekl(0x66ea)
    dt=(v1-v0)/50.0
    f['rate_6888']=(d0-d1)/dt
    f['dX_per_s']=((x1-x0)+0.0)/dt; f['dY_per_s']=(y1-y0)/dt
    f['speed']=h.peekw(0x6772)
    return f
try:
    h.boot_to_game('M')
    print(which,'booted; type',hex(h.peekw(0x6220)),flush=True)
    time.sleep(5)
    def go(hd):
        for a in (0x6742,0x6294,0x764a):
            h.debug('w $%x $%02x $%02x'%(a,hd>>8,hd&255),0.3)
        h.debug('w $6fba $01 $42 $00 $00',0.3)
    heads=[768,256,768,256]
    k=0
    for mhz in (8,16):
        if mhz==16: h.set_cpuclock(16); time.sleep(5)
        for i in range(4):
            go(heads[k%4]); k+=1
            time.sleep(1)
            t0=h.peekw(0x6220); s0=h.peekw(0x6772)
            r=rate(400)
            r['type0']=t0; r['speed0']=s0; r['type1']=h.peekw(0x6220); r['head']=h.peekw(0x6742)
            print(which,mhz,'MHz',r,flush=True)
    h.shot('/tmp/p3b/t2_%s.png'%which)
finally:
    h.close()
