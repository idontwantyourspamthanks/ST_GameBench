"""Unicorn A/B: base live image vs base+extra, per-pass RAM+screen equality.  python3 emucmp.py BASE.live EXTRA.live DUMP NPASS KIND [pokes a=v,...] """
import os
import sys, json, struct
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
A,B,dump,npass,kind=sys.argv[1:6]; npass=int(npass)
pokes=[(int(x.split('=')[0],16),int(x.split('=')[1],16)) for x in sys.argv[6].split(',')] if len(sys.argv)>6 and sys.argv[6] else []
MASK=[(0x100c,0x100e),(0x12000,0x16000),(0x77d00,0x78000),(0x7fd00,0x80000)]
for L in (A,B):
    MASK+=[(x['addr'],x['addr']+len(x['new'])//2) for x in json.load(open(L+'.json'))['sites']]
def run(live,pk):
    e=Emu(dump); apply_live_p(e,live)
    for a,v in pk: e.setb(a,v)
    S=[]
    for p in range(npass):
        v=schedule(p,kind)
        if v is not None: e.setb(0x6105,v)
        e.run(0x7a88,0x7b74); flip(e)
        S.append(e.read(0,0x80000)); e.run(0x7b7a,0x7a88)
    return e,S
ea,SA=run(A,[]); eb,SB=run(B,pokes)
bad={}
for p in range(npass):
    a,b=SA[p],SB[p]
    if a==b: continue
    for i in np.nonzero(np.frombuffer(a,np.uint8)!=np.frombuffer(b,np.uint8))[0]:
        i=int(i)
        if any(lo<=i<hi for lo,hi in MASK): continue
        if os.environ.get('LOGIC_ONLY') and i>=0x70000: continue
        bad.setdefault(i,[]).append(p)
print(dump.split('/')[-1],kind,npass,'passes: differing unmasked addresses',len(bad))
for s,t in region_runs(sorted(bad))[:20]: print('   $%05x-$%05x first pass %d'%(s,t,min(bad[s])))
print('INIT',eb.b(0xBF000),'NENT',eb.w(0xBF008),'POOLP',hex(eb.l(0xBF004)))
if bad and len(sys.argv)>7:
    for a in sorted(bad)[:int(sys.argv[7])]:
        if a>=0x70000:
            o=a-0x70000; b=o//0x8000; o%=0x8000
            print('addr %x buf %d row %d byte %d (col %d plane %d) passes %s  A=%02x B=%02x'%(a,b,o//160,o%160,(o%160)//8,((o%160)%8)//2,bad[a][:3],SA[bad[a][0]][a],SB[bad[a][0]][a]))
