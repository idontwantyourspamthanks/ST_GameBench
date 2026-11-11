import sys
sys.path.insert(0,'.')
import rdset
recs = rdset.parse(sys.argv[1])
ENTRY = {0x263de, 0x26298, 0x26882}
isr=[]; W=set(); rbw={}; carried={}
for (pc,mn,ops,nxt,line) in recs:
    if pc in ENTRY: isr.append(pc)
    if isr:
        if mn.startswith('rte'): isr.pop()
        continue
    for kind,ea,size in rdset.accesses(mn,ops):
        for b in range(ea,ea+size):
            if kind=='R':
                if b not in W and b not in rbw: rbw[b]=pc
            else:
                if b in rbw and b not in W and b not in carried: carried[b]=pc
                W.add(b)
ch=sorted(b for b in carried if not(0x60000<=b<0x80300) and not (0x7d00<=b<0x8100))
iv=[]
for b in ch:
    if iv and b-iv[-1][1]<=2: iv[-1][1]=b
    else: iv.append([b,b])
for s,e in iv:
    print(f'{s:06x}-{e:06x} {e-s+1:4d} read-first by {sorted({hex(rbw[b]) for b in range(s,e+1) if b in rbw})[:3]} then written by {sorted({hex(carried[b]) for b in range(s,e+1) if b in carried})[:3]}')
