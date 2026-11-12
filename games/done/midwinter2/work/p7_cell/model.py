import struct
from an1 import *
def s16(v):
    v&=0xffff
    return v-0x10000 if v&0x8000 else v
def corner_view(m,c,dx,dy,h=None):
    """game's transform of vertex (dx,dy) of cell record c; returns (X,Y,W) with 16-bit wrap"""
    if h is None:
        ho = {(0,0):0,(1,0):0x10,(0,1):0x200,(1,1):0x210}[(dx,dy)]
        h=S(m,c+ho)
    cw=S(m,c+0xc)+8*dx; ew=S(m,c+0xe)+8*dy
    out=[]
    for i,ma in enumerate((0x18568,0x1856a,0x1856c)):
        mm=S(m,ma)
        prod=h*mm
        v=((prod<<2)>>16)  # asl.l #2 then swap: low16 of (prod<<2 >>16) -- careful with 32-bit wrap
        prod32=(prod*4)&0xffffffff
        v=s16(prod32>>16)
        v=s16(v+S(m,0x188f8+cw+2*i)+S(m,0x18a40+ew+2*i))
        out.append(v)
    return out
def outcode(X,Y,Wd):
    Y=s16(Y+Y+(Y>>2)) if False else s16(2*Y + (Y>>2))
    d3=0
    # follows $1f9b6
    if Wd<0: d3=0x1010
    elif Wd==0 and (X|Y)==0: return 0x1010 # approx
    def sub_neg(a,b): # cmp.w a,b -> b-a, bpl? returns True if N clear
        return not (s16(b-a)<0)
    d0,d1,d2=X,Y,Wd
    if not sub_neg(d0,d2): d3|=0x808
    if not sub_neg(d1,d2): d3|=0x202
    d2=s16(-d2)
    if not sub_neg(d2,d0): d3|=0x404
    if not sub_neg(d2,d1): d3|=0x101
    return d3
if __name__=='__main__':
    s,r,m=analyze('f_1ebda_0.bin')
    bad=0;tot=0
    for c,k,a,oc in r:
        for dx in (0,1):
            for dy in (0,1):
                ho={(0,0):0,(1,0):0x10,(0,1):0x200,(1,1):0x210}[(dx,dy)]
                so=W(m,c+ho+8)
                d=W(m,0x7c718+so)
                st=[S(m,0x7c718+d+6+2*i) for i in range(3)]
                mine=corner_view(m,c,dx,dy)
                oc_real=W(m,0x7c718+d+4)
                tot+=1
                if st!=mine or outcode(*mine)!=oc_real:
                    bad+=1
                    if bad<5: print(hex(c),dx,dy,st,mine,hex(oc_real),hex(outcode(*mine)))
    print('bad',bad,'of',tot)
