import sys
from pathlib import Path
a,b=Path(sys.argv[1]),Path(sys.argv[2]); n=int(sys.argv[3]) if len(sys.argv)>3 else 99
tot=0
for k in range(1,n+1):
    row=[]
    for w in ('60000','70000'):
        fa,fb=a/f'f{k:02d}_{w}.bin',b/f'f{k:02d}_{w}.bin'
        if not fa.exists() or not fb.exists(): continue
        x,y=fa.read_bytes(),fb.read_bytes()
        d=sum(1 for i in range(32000) if x[i]!=y[i]); row.append(d); tot+=d
    yaw=(a/f'f{k:02d}_yaw.bin').read_bytes().hex()+'/'+(b/f'f{k:02d}_yaw.bin').read_bytes().hex()
    print(f'f{k:02d} diffbytes 60000/70000 = {row} yaw {yaw}')
print('TOTAL', tot)
