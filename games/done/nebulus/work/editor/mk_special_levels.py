import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
import ovl
def blank():
    g=[[0]*48 for _ in range(16)]
    for a in range(16): g[a][1]=0x81
    for a in (3,4,5): g[a][43]=0x81
    for r in (44,45,46): g[4][r]=0xc3
    return g
# A: crumble at cols 3,4 on the ring (row 1), nothing below (sea); B: cols 8,9 crumble with a lower ledge row 0 below
g=blank()
g[3][1]=0x91; g[4][1]=0x91
g[9][1]=0x91; g[10][1]=0x91; g[9][0]=0x81; g[10][0]=0x81
# conveyors for the record: col 6 left, col 7 right
g[6][1]=0xa1; g[7][1]=0xb1
lv=ovl.level(1,0,48,g,time=0x0450,name='CRUMBLE')
open('/tmp/nlg/x/crumble.ovl','wb').write(ovl.build([lv],[ovl.camp('CRUMBLE',[0])]))
print(ovl.validate(open('/tmp/nlg/x/crumble.ovl','rb').read()))
# showcase level: every tile kind in the editor
g=blank()
cells=[(1,3,0x80),(2,3,0x82),(3,3,0x83),(3,4,0x83),(3,5,0x83),(5,3,0x91),(6,3,0x81),(7,3,0x85),(7,2,0x81),(7,8,0x08),(8,3,0x0c)]
for a,r,v in cells: g[a][r]=v
for i,v in enumerate([0x10,0x20,0x30,0x40,0x50,0x60,0x70]): g[i+1][6]=v; g[i+1][5]=0x81 if v<0x40 else 0
for a in range(9,16): g[a][10]=0x81
g[10][11]=0x91; g[11][11]=0xa1; g[12][11]=0xb1; g[13][12]=0x80; g[14][12]=0x82
lv2=ovl.level(1,0,48,g,time=0x0450,name='SHOWCASE')
open('/tmp/nlg/x/showcase.ovl','wb').write(ovl.build([lv2],[ovl.camp('SHOW',[0])]))
