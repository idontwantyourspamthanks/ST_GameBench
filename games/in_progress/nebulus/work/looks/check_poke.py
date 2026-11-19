"""Compare the poked level starts against the natural ones (campaign dumps lvl*.bin) region by region."""
import sys,hashlib
C='/tmp/looks/camp'; P=sys.argv[1]
def rd(p): return open(p,'rb').read()
nat=[rd(f'{C}/lvl{i}.bin') for i in range(8)]
R={'palette $351ac':(0x351ac,32),'raster4 $40398':(0x40398,8),'eye buffers $24be0-$2fae0':(0x24be0,0x2fae0-0x24be0),'body buffer $100e0-$110e0':(0x100e0,0x1000),'grid':(0x327f0,4096)}
def same(a,b,r): s,n=R[r]; return a[s:s+n]==b[s:s+n]
def row(tag,d,expect):
    print(f'{tag}: tower-in-RAM {int.from_bytes(d[0x3390c:0x3390e],"big")}')
    for r in R:
        m=[f'T{i+1}' for i in range(8) if same(d,nat[i],r)]
        print(f'   {r:28s} == natural level start of: {",".join(m) or "none"}')
import os
for tag in ('pA','pB','pC'):
    f=f'{P}/{tag}.bin'
    if os.path.exists(f): row(tag,rd(f),None)
