#!/usr/bin/env python3
"""Render the creature sprite source blocks of NEBEXE (RAM image) with a tower palette.
src block = 16 lines x 2 groups x (mask,p0,p1,p2,p3) words (320 B); frames 0..11 at $53bba, 12..19 at $54aba+(tower&3)*$a00."""
import struct, sys
from PIL import Image
RAM = open('work/dumps/tower_1mb.bin','rb').read()
def pal(t):
    w = struct.unpack('>16H', RAM[0x35250+32*t:0x35250+32*t+32])
    out=[]
    for v in w:
        r,g,b=(v>>8)&15,(v>>4)&15,v&15
        f=lambda x:(((x&7)<<1)|(x>>3))*17
        out.append((f(r),f(g),f(b)))
    return out
def sprite(addr, p):
    im = Image.new('RGBA',(32,16),(255,0,255,255))
    px = im.load()
    for y in range(16):
        for g in range(2):
            o = addr + y*20 + g*10
            m,p0,p1,p2,p3 = struct.unpack('>5H', RAM[o:o+10])
            for x in range(16):
                b = 15-x
                c = ((p0>>b)&1)|(((p1>>b)&1)<<1)|(((p2>>b)&1)<<2)|(((p3>>b)&1)<<3)
                mk = (m>>b)&1   # mask bit 1 = transparent? (and.l mask then or)
                px[g*16+x,y] = (255,0,255,255) if mk else p[c]+(255,)
    return im
def sheet(t, var, scale=3):
    p = pal(t)
    W = 10
    im = Image.new('RGBA',(W*34*scale, 2*18*scale),(40,40,40,255))
    frames=[0x53bba+i*320 for i in range(12)]+[0x54aba+var*0xa00+i*320 for i in range(8)]
    for i,a in enumerate(frames):
        s = sprite(a,p).resize((32*scale,16*scale),Image.NEAREST)
        im.paste(s,((i%W)*34*scale,(i//W)*18*scale))
    return im
if __name__=='__main__':
    t=int(sys.argv[1]); v=int(sys.argv[2]); sheet(t,v).convert('RGB').save(sys.argv[3])
