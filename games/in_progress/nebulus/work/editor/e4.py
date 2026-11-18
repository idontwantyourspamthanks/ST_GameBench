from ed import *
import sys
SET=sys.argv[1]
kinds={'A':[0x10,0x20,0x30,0x40],'B':[0x50,0x60,0x70,0x20]}[SET]
def spawn(h,slot,v,x,y,sp=None):
    k,sp0=None,None
    if v==0x10: sp0,k=1,2
    elif v in(0x20,): sp0,k=1,1
    elif v==0x30: sp0,k=0,1
    elif v in(0x40,0x50): sp0,k=(2 if v&0x10 else 1),8
    else: sp0,k=(2 if v&0x10 else 1),9
    def pw(base,val): poke(h,base+2*slot,struct.pack('>H',val))
    pw(0x33944,x&0x7f); pw(0x33944+0xc,y); pw(0x33944+0x48,6); pw(0x33944+0x3c,0); pw(0x33944+0x54,sp0); pw(0x33944+0x6c,k); pw(0x33944+0x60,0)
h=snap('/tmp/ned4'+SET)
try:
    time.sleep(1.5)
    poke(h,0x3792c,bytes([0x4e,0x75]))
    poke(h,0x3398c,bytes(8))
    while W(h,0x33a20)!=0: time.sleep(0.3)
    fx,fy=4,8; print('frog',fx,fy,'scroll',W(h,0x338fe),'state',W(h,0x33a20))
    offs=[24,40,56,72]
    for i,v in enumerate(kinds):
        spawn(h,i,v,fx+offs[i],fy+ (8 if v>=0x40 else 0))
    time.sleep(0.3)
    for n in range(16):
        d=struct.unpack('>60H',grab(h,0x33944,0x78,'s'))
        out=[]
        for s in range(4):
            sp=d[0x54//2+s]; sp=sp-65536 if sp>32767 else sp
            out.append(f"s{s} x{d[s]:3d} y{d[6+s]:3d} st{d[0x48//2+s]} sp{sp:2d} k{d[0x6c//2+s]}")
        print(f"{n} frog {W(h,0x33a16)} {W(h,0x33a18)} st{W(h,0x33a20)} | "+" | ".join(out),flush=True)
        if n in (1,4,8,13): h.shot(E+f'en_{SET}{n}.png')
        time.sleep(0.25)
finally: h.close()
