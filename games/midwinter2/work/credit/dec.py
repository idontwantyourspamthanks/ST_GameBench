import sys
from PIL import Image
def pal_from(s):
    return None
def decode(buf, off, pal):
    im=Image.new('RGB',(320,200))
    px=im.load()
    for y in range(200):
        for g in range(20):
            o=off+y*160+g*8
            w=[(buf[o+2*p]<<8)|buf[o+2*p+1] for p in range(4)]
            for b in range(16):
                c=sum(((w[p]>>(15-b))&1)<<p for p in range(4))
                px[g*16+b,y]=pal[c]
    return im
def stpal(words):
    out=[]
    for w in words:
        r=((w>>8)&7)*36; g=((w>>4)&7)*36; b=(w&7)*36
        out.append((r,g,b))
    return out
if __name__=='__main__':
    log=open(sys.argv[1],errors='replace').read()
