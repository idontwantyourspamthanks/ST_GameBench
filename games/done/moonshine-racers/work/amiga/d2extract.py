import sys,struct,hashlib,re,os
sys.path.insert(0,'work/amiga')
from iceunpack import unpack
D='alt/amiga/Moonshine Racers Disk 2.adf'
d=open(D,'rb').read()
os.makedirs('work/amiga/d2',exist_ok=True)
rows=[]
for s in range(1760):
    o=s*512
    if d[o:o+4]==b'Ice!':
        ps,osz=struct.unpack('>II',d[o+4:o+12])
        if osz>200000 or ps>200000: continue
        try: out=unpack(d[o:o+ps+12] if False else d[o:o+ps])
        except Exception as e: print('fail',s,e); continue
        open(f'work/amiga/d2/s{s:04d}.bin','wb').write(out)
        rows.append((s,ps,osz,hashlib.md5(out).hexdigest()[:8],out[:8].hex(),b'M.K.' in out,))
for r in rows: print(*r)
print(len(rows))
