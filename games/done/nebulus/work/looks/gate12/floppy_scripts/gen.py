import sys, random
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
import ovl
def blank(rows):
    g=[[0]*rows for _ in range(16)]
    for c in range(16): g[c][1]=0x81
    return g
def mk(rows, name, tower, cols, ene, extra, time=0x0300):
    g=blank(rows)
    for (c,r,v) in extra: g[c][r]=v
    return ovl.level(1,tower,rows,g,time,name,cols,ene)
# file1: all new cells, colours+enemies set, odd-size record possible
f1=ovl.build([mk(48,'CONVEY',2,0,3,[(2,1,0xa1),(3,1,0xa1),(5,1,0xb1),(6,1,0xb1),(7,1,0x91),(9,1,0x91),(12,5,0x81),(13,5,0xa1)])],
             [ovl.camp('C1',[0])])
# file2: doors: opening $83 pair at col and col^8, exit $c3 unpaired; tower byte 5 (colours pick), flags enemies 4
f2=ovl.build([mk(40,'DOORS',5,0,4,[(1,3,0x83),(9,3,0x83),(4,30,0x83),(12,30,0x83),(6,39,0xc3),(6,38,0xc3),(6,37,0xc3)]),
              mk(33,'ODDLEN',7,0,1,[(3,10,0x91),(4,11,0x91),(5,12,0xa1)],0x0120)],
             [ovl.camp('C2',[0,1,ovl.orig(1,3)])])
# file3: legacy colour nibble (flags high nibble 6) + enemy 2, tower 0; mix of all new cells in one level, 120 rows
rnd=random.Random(5)
ex=[(rnd.randrange(16),rnd.randrange(2,119),rnd.choice([0x91,0xa1,0xb1,0x81,0x83,0xc3,0x80,0x82,0x10,0x20,0x40,0x70,0x85,0x08])) for _ in range(120)]
f3=ovl.build([mk(120,'MIXED',0,6,2,ex),mk(16,'TINY',3,8,0,[(0,5,0xb1)])],[ovl.camp('C3',[0,1])])
for i,f in enumerate((f1,f2,f3),1): open(f'/tmp/ng12fl/x/t{i}.ovl','wb').write(f)
print([ (l['name'],l['rows'],hex(l['flags']),l['tower'],l['size']) for f in (f1,f2,f3) for l in ovl.parse(f)[0]])
