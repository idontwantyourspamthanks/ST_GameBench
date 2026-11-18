import sys, re, struct
sys.path.insert(0,'work/sprite')
import unit, kb
from pathlib import Path
HERE=Path('work/sprite').resolve()
nib,cols,x,rows=7,2,100,4
out,syms=unit.assemble(HERE/'msb.s',[])
e=kb.pick(nib,cols)
f=kb.build([(syms['s_n7c2'],x,80,rows,1,e['ptr'])],'dbgm')
tl,res,_=unit.run(HERE/'kb.s','race_start','ste',1024,None,['e1000:64','c8000:16'],None,bins=[f'd0000:{f}',f'c2000:{out}'],timeout=120)
for k,v in res.items(): print(v)
D=open('work/dumps/ram_race_start.bin','rb').read()
a=e['ptr']
print('source rows (12 words/row? cols*3):')
for r in range(rows):
    ws=struct.unpack('>6H',D[a+r*12:a+r*12+12]); print(' '.join('%04x'%w for w in ws), ' mask cols:', '%04x %04x'%(ws[0]|ws[1]|ws[2], ws[3]|ws[4]|ws[5]))
