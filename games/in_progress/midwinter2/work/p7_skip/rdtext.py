import sys, collections
sys.path.insert(0,'.')
import rdset
traces=sys.argv[1:]
first={}
for t in traces:
    rdset.NEXTPC = ('tr_' in t or 'tr_bank' in t)
    recs=rdset.parse(t)
    ENTRY = {0x263de, 0x26298, 0x26882}
    isr=[]; W=set(); ren=('tn_' not in t and 'tl_' not in t and 'bank_loop' not in t)
    for (pc,mn,ops,nxt,line) in recs:
        if pc in ENTRY: isr.append(pc)
        if isr:
            if mn.startswith('rte'): isr.pop()
            continue
        if not ren:
            if pc==0x5056: ren=True; W=set()
            continue
        if 'tn_' in t or 'tl_' in t or 'bank_loop' in t:
            pass
        for kind,ea,size in rdset.accesses(mn,ops):
            for b in range(ea,ea+size):
                if kind=='W': W.add(b)
                elif b not in W and b not in first: first[b]=line.strip()
        if pc==0x315a8 and 'tn_' not in t: pass
iv=rdset.intervals(first.keys())
lo,hi=int(0x6000),int(0x20000)
for s,e in iv:
    if s<0x6000 or s>=0x20000 or 0x7d00<=s<0x8100 : continue
    txt=sorted({first[b][:90] for b in range(s,e+1) if b in first})
    print(f'{s:06x}-{e:06x} {e-s+1:3d}  ', ' || '.join(t[18:] for t in txt[:3]))
