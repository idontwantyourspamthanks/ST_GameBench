"""Python copy of the game's icon hit test (click path $13506-$1356a): icon(x,y) -> icon id 1..23 or -1.  See work/notes/tooltip.md 1.1.
   `python3 tools/pmtt_grid.py` (needs /tmp/pmtt_a.png, a screenshot) prints each cell bbox."""
import struct
from pathlib import Path
d=(Path(__file__).resolve().parent.parent/'work'/'dumps'/'get_men.bin').read_bytes()
sw=lambda a:struct.unpack('>h',d[a:a+2])[0]
def tab(base):
    a=base; out=[]
    while True:
        r=[sw(a+2*i) for i in range(4)]
        if r[0]==0: break
        out.append(r); a+=8
    return out
T1=tab(0x12e6a); T2=tab(0x12ee4)
def s16(v):
    v&=0xffff
    return v-0x10000 if v&0x8000 else v
def line(x,y,r):
    x0,y0,x1,y1=r
    d0=x-x0; d1=y-y0; d4=x1-x0; d5=y1-y0
    p=s16(d0)*s16(d5)
    # divs.w d4,p
    q=int(p/d4) if d4 else None
    if q is None or q<-32768 or q>32767:
        d0=p  # overflow: unchanged
    else:
        d0=q
    return s16(d1),s16(d0)
def code(x,y):
    d6=0
    for r in T1:
        d6+=1
        d1,d0=line(x,y,r)
        if not (d1<d0): break
    else:
        pass
    for r in T2:
        d6+=0x10
        d1,d0=line(x,y,r)
        if not (d1>d0): break
    return d6
T=[]
a=0x19bde
while True:
    v=struct.unpack('>H',d[a:a+2])[0]
    if v>=0x8000: break
    T.append(v); a+=2
def icon(x,y):
    c=code(x,y)
    for i,v in enumerate(T):
        if v==c: return i
    return -1
if __name__=='__main__':
    from PIL import Image, ImageDraw
    im=Image.open('/tmp/pmtt_a.png').convert('RGB')
    S=2
    cols=[(255,0,0),(0,255,0),(0,128,255),(255,255,0),(255,0,255),(0,255,255),(255,128,0),(128,255,0),(255,255,255)]
    ov=im.copy()
    px=ov.load()
    grid={}
    for y in range(6,200):
        for x in range(0,320):
            i=icon(x,y); grid[(x,y)]=i
    for y in range(6,200):
        for x in range(0,320):
            i=grid[(x,y)]
            edge = any(grid.get((x+dx,y+dy),-1)!=i for dx,dy in((1,0),(0,1)))
            if edge and i>=0:
                for sx in range(S):
                    for sy in range(S):
                        px[96+x*S+sx,58+y*S+sy]=cols[i%len(cols)]
    dr=ImageDraw.Draw(ov)
    # label
    for i in range(len(T)):
        pts=[k for k,v in grid.items() if v==i]
        if pts:
            cx=sum(p[0] for p in pts)//len(pts); cy=sum(p[1] for p in pts)//len(pts)
            dr.text((96+cx*S-6,58+cy*S-5),str(i),fill=(255,255,255))
    ov.crop((96,58+80*2,96+640,58+400)).resize((1280,640),Image.NEAREST).save('/tmp/pmtt/gridov.png')
    for i in range(len(T)):
        pts=[k for k,v in grid.items() if v==i]
        if pts:
            xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            print(i,hex(T[i]),len(pts),'bbox',min(xs),min(ys),max(xs),max(ys))
