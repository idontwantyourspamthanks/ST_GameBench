"""chan.py <looptrace> : bytes written outside render (logic/ISR) that the render reads before writing."""
import sys, collections
sys.path.insert(0,'.')
import rdset
recs = rdset.parse(sys.argv[1])
ENTRY = {0x263de, 0x26298, 0x26882}
isr=[]; phase='pre'
Wout = {}   # byte -> (phase, pc)  last non-render writer
rbw = {}; Wr=set()
for (pc,mn,ops,nxt,line) in recs:
    inisr=False
    if pc in ENTRY: isr.append(pc)
    if isr:
        inisr=True
        if mn.startswith('rte'): isr.pop()
    if not inisr:
        if pc==0x5056: phase='render'
        elif pc==0x315a8: phase='post'
        elif pc==0x315c6: phase='flip'
        elif pc==0x315ca: phase='postflip'
    ph = 'isr' if inisr else phase
    for kind,ea,size in rdset.accesses(mn,ops):
        for b in range(ea,ea+size):
            if ph=='render':
                if kind=='W': Wr.add(b)
                elif b not in Wr and b not in rbw: rbw[b]=pc
            elif kind=='W' and not (0x60000<=b<0x80300):
                Wout[b]=(ph,pc)
ch = sorted(b for b in rbw if b in Wout and not(0x7d00<=b<0x8100))
iv=[]
for b in ch:
    if iv and b-iv[-1][1]<=2: iv[-1][1]=b
    else: iv.append([b,b])
print('render rbw',len(rbw),'channel bytes (written outside render this iteration)',len(ch))
for s,e in iv:
    ph={Wout[b][0] for b in range(s,e+1) if b in Wout}
    wp={hex(Wout[b][1]) for b in range(s,e+1) if b in Wout}
    rp={hex(rbw[b]) for b in range(s,e+1) if b in rbw}
    print(f'{s:06x}-{e:06x} {e-s+1:4d} writers {sorted(ph)} wpc {sorted(wp)[:4]} readers {sorted(rp)[:4]}')
