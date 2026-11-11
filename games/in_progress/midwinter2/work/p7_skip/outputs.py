"""outputs.py looptrace.. : bytes written by render and read by non-render code (logic/HUD/ISR), over the traced iterations."""
import sys
sys.path.insert(0,'.')
import rdset
rdset.NEXTPC=False
ENTRY = {0x263de, 0x26298, 0x26882}   # $26a50 is a bare `rte` (timer C and the exit of $26882)
Wren={}; Rnr={}
for path in sys.argv[1:]:
    recs=rdset.parse(path)
    isr=[]; phase='pre'
    for (pc,mn,ops,nxt,line) in recs:
        inisr=False
        if pc in ENTRY: isr.append(pc)
        if isr:
            inisr=True
            if mn.startswith('rte'): isr.pop()
        if not inisr:
            if pc==0x31486: phase='pre'
            elif pc==0x5056: phase='render'
            elif pc==0x315a8: phase='post'
        ph='isr' if inisr else phase
        for kind,ea,size in rdset.accesses(mn,ops):
            for b in range(ea,ea+size):
                if 0x60000<=b<0x80300 or 0x7d00<=b<0x8100: continue
                if ph=='render':
                    if kind=='W': Wren.setdefault(b,pc)
                else:
                    if kind=='R': Rnr.setdefault(b,(ph,pc))
ch=sorted(b for b in Wren if b in Rnr)
iv=rdset.intervals(ch)
print('render-written bytes',len(Wren),'read by non-render code:',len(ch))
for s,e in iv:
    print(f'{s:06x}-{e:06x} {e-s+1:4d} written by {sorted({hex(Wren[b]) for b in range(s,e+1)})[:3]} read by {sorted({(Rnr[b][0],hex(Rnr[b][1])) for b in range(s,e+1)})[:3]}')
