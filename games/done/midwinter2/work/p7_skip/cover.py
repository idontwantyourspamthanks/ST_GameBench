"""cover.py trace... : every byte the render reads (before writing it) AND some non-render code (logic/ISR/HUD/flip) writes,
over all traced loop iterations, must be inside the p7_skip signature.  Prints the uncovered ones."""
import sys
sys.path.insert(0,'.')
import rdset
rdset.NEXTPC=False
ENTRY = {0x263de, 0x26298, 0x26882}   # $26a50 is a bare `rte` (timer C and the exit of $26882)
SC = [(0x6220,2),(0x66e0,2),(0x66e6,4),(0x66ea,4),(0x670a,4),(0x6f78,2),(0x67be,2),(0x6806,2),(0x763e,36),(0x17fc4,2),(0x18768,2),
      (0x18556,12),(0x18772,8),(0x18784,4),(0x18788,2),(0x18796,2),(0x18798,4),(0x53ac,4),(0x53da,4),
      (0x7590,2),(0x7582,2),(0x759c,2),(0x40b6,2),(0x1dfba,4)]   # last 5: preconditions / wave pointer (compared when WV)
cov=set()
for a,n in SC: cov.update(range(a,a+n))
for i in range(30):
    a=0x3532+i*0x42
    for off in (0,2,4,6,8,0xa,0xc,0xe,0x16,0x1a,0x1c,0x1e,0x20,0x2c,0x2e,0x34): cov.update(range(a+off,a+off+2))
    a=0x3cee+i*0x18
    for off in (0,4,6,0xa,0xc): cov.update(range(a+off,a+off+2))
cov.update(range(0x4bfba,0x4bfba+80*16))
GATE={0x1877c,0x1877d}   # carried wave phase: handled (replayed on skip), see note
Wnr={}; R={}
tot=0
for path in sys.argv[1:]:
    recs=rdset.parse(path)
    isr=[]; phase='pre'; Wr=set(); n=0
    for (pc,mn,ops,nxt,line) in recs:
        inisr=False
        if pc in ENTRY: isr.append(pc)
        if isr:
            inisr=True
            if mn.startswith('rte'): isr.pop()
        if not inisr:
            if pc==0x31486: phase='pre'; Wr=set(); n+=1
            elif pc==0x5056: phase='render'
            elif pc==0x315a8: phase='post'
        ph='isr' if inisr else phase
        for kind,ea,size in rdset.accesses(mn,ops):
            for b in range(ea,ea+size):
                if 0x60000<=b<0x80300 or 0x7d00<=b<0x8100: continue
                if ph=='render':
                    if kind=='W': Wr.add(b)
                    elif b not in Wr: R.setdefault(b,(path,pc))
                elif kind=='W': Wnr.setdefault(b,(path,ph,pc))
    tot+=n
    print(path,'iterations',n)
ch=sorted(b for b in R if b in Wnr)
unc=[b for b in ch if b not in cov and b not in GATE]
print('iterations',tot,'render-read bytes',len(R),'also written outside the render',len(ch),'covered',len(ch)-len(unc),'UNCOVERED',len(unc))
iv=rdset.intervals(unc)
for s,e in iv:
    print(f'  {s:06x}-{e:06x} {e-s+1} read by pc {R[s][1]:x} written outside render by {Wnr[s][1]} pc {Wnr[s][2]:x} ({Wnr[s][0].split("/")[-1]})')
