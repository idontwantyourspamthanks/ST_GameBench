import sys, collections
sys.path.insert(0,'.')
import rdset
rdset.NEXTPC=False
ENTRY = {0x263de, 0x26298, 0x26882}
for path in sys.argv[1:]:
    recs=rdset.parse(path)
    isr=[]; phase='pre'; bad=collections.Counter(); hud=collections.Counter(); n=0
    for (pc,mn,ops,nxt,line) in recs:
        if pc in ENTRY: isr.append(pc)
        inisr=bool(isr)
        if isr and mn.startswith('rte'): isr.pop()
        if not inisr:
            if pc==0x31486: phase='pre'; n+=1
            elif pc==0x5056: phase='render'
            elif pc==0x315a8: phase='post'
        ph='isr' if inisr else phase
        if ph=='render': continue
        for kind,ea,size in rdset.accesses(mn,ops):
            if kind!='W': continue
            for b in range(ea,ea+size):
                for base in (0x60000,0x70000):
                    if base<=b<base+32000:
                        y=(b-base)//160
                        if y>=58: bad[(ph,hex(pc))]+=1
                        else: hud[ph]+=1
    print(path.split('/')[-1],'iterations',n,'| writes into rows >= 58 outside the render:',dict(bad) or 'NONE','| rows<58 writes by phase',dict(hud))
