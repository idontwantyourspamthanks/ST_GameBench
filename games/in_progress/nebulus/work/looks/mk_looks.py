#!/usr/bin/env python3
"""Experiment OVL: identical grid (ledge ring + enemies of every kind near the frog start + exit), differing ONLY in the record's mission/tower bytes.
levels: 0..7 = mission 1 tower 0..7 ; 8 = mission 2 tower 0 ; 9 = mission 2 tower 3.  One campaign 'LOOKS' = all of them.
usage: mk_looks.py OUT.ovl [even]   (even: one extra cell so every record has an EVEN size; odd-size records crash the game's loader, see looks.md)"""
import sys
sys.path.insert(0,'work/editor')
import ovl
ROWS=48
def grid(even=False):
    g=[[0]*ROWS for _ in range(16)]
    for a in range(16): g[a][1]=0x81            # ledge ring = frog start ring
    for a in range(16): g[a][ROWS-3]=0x81
    for r in (ROWS-5,ROWS-4,ROWS-3): g[4][r]=0xc3   # exit stack
    g[6][2]=0x10                                # stone ball (4+ columns right of the frog, rolls on the ring)
    g[12][2]=0x20                               # red ball (left of the frog)
    g[3][8]=0x40; g[3][5]=0x80; g[3][12]=0x80   # eye up/down between two pillars, column 3
    g[13][8]=0x40; g[13][5]=0x80; g[13][12]=0x80 # second one, column 13 (left of the frog)
    g[8][16]=0x60                               # eye left/right (behind the tower first)
    if even:
        n=sum(1 for a in range(16) for r in range(ROWS) if g[a][r])
        if n%2: g[10][30]=0x81
    return g
def main(out, even):
    specs=[(1,t) for t in range(8)]+[(2,0),(2,3)]
    lv=[ovl.level(m,t,ROWS,grid(even),time=0x0600,name=f"M{m}T{t+1}") for m,t in specs]
    c=ovl.camp("LOOKS",list(range(len(lv))))
    open(out,'wb').write(ovl.build(lv,[c]))
main(sys.argv[1], len(sys.argv)>2 and sys.argv[2]=='even')
