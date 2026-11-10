"""diff.py ORIGTAG PATCHEDTAG: decoded displayed screen (base from TAG.base) of the unpatched vs the patched run."""
import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/midwinter/work/credit')
from scr import decode
D='/home/ryan/Code/AtariST/gamebench/games/midwinter/work/credit/'
def scr(tag):
    ram=open(D+tag+'_ram.bin','rb').read()
    return decode(ram,int(open(D+tag+'.base').read(),16))
a=scr(sys.argv[1]); b=scr(sys.argv[2])
d=[(x,y,a[y][x],b[y][x]) for y in range(200) for x in range(320) if a[y][x]!=b[y][x]]
xs=[p[0] for p in d]; ys=[p[1] for p in d]
print('pixels differ:',len(d),'bbox x',min(xs),max(xs),'y',min(ys),max(ys))
print('orig colours under text',sorted({p[2] for p in d}),'new colours',sorted({p[3] for p in d}))
inside=all(9<=x<=65 and 178<=y<=198 for x,y,_,_ in d)
print('all inside the text rect x9..65 y178..198:',inside)
for y in range(min(ys),max(ys)+1):
    print(y,''.join('#' if b[y][x]!=a[y][x] else '.' for x in range(0,80)))
