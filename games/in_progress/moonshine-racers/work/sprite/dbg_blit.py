import sys, re, struct
sys.path.insert(0,'work/sprite')
import unit, kb
from pathlib import Path
HERE=Path('work/sprite').resolve()
nib,cols,x,rows=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4])
out,syms=unit.assemble(HERE/'msb.s',[])
e=kb.pick(nib,cols)
scr=[]
for kind in ('stock','blit'):
    k=kb.FULL[(nib,cols)] if kind=='stock' else syms[f's_n{nib}c{cols}']
    f=kb.build([(k,x,80,rows,1,e['ptr'])],'dbg'+kind)
    tl,res,_=unit.run(HERE/'kb.s','race_start','ste',1024,None,['c8000:32000'],None,bins=[f'd0000:{f}',f'c2000:{out}'],timeout=120)
    txt=list(res.values())[0]
    bs=b''.join(bytes.fromhex(m.group(2).replace(' ','')) for m in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?){1,16})",txt,re.M))
    scr.append(bs[:32000])
a,b=scr
d=[i for i in range(32000) if a[i]!=b[i]]
print('bytes differing',len(d), 'entry',e)
rows_={}
for i in d: rows_.setdefault(i//160,[]).append((i%160,a[i],b[i]))
for r,l in sorted(rows_.items())[:40]: print(r,[(c,hex(x),hex(y)) for c,x,y in l][:16])
