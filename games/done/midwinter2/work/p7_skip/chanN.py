"""chanN.py trace... : per-iteration, bytes written outside render (logic/ISR/post) and read by the render before written.
Aggregates over all iterations in the traces. Also reports union write set of non-render code."""
import sys
sys.path.insert(0,'.')
import rdset
rdset.NEXTPC=False
ENTRY = {0x263de, 0x26298, 0x26882}   # $26a50 is a bare `rte` (timer C and the exit of $26882)
W_nr = {}      # byte -> set(pc)
R_ren = {}
n_it = 0
for path in sys.argv[1:]:
    recs = rdset.parse(path)
    isr=[]; phase='pre'; Wr=set()
    for (pc,mn,ops,nxt,line) in recs:
        inisr=False
        if pc in ENTRY: isr.append(pc)
        if isr:
            inisr=True
            if mn.startswith('rte'): isr.pop()
        if not inisr:
            if pc==0x31486: phase='pre'; n_it+=1; Wr=set()
            elif pc==0x5056: phase='render'
            elif pc==0x315a8: phase='post'
        ph='isr' if inisr else phase
        for kind,ea,size in rdset.accesses(mn,ops):
            for b in range(ea,ea+size):
                if 0x60000<=b<0x80300: continue
                if ph=='render':
                    if kind=='W': Wr.add(b)
                    elif b not in Wr and b not in R_ren: R_ren[b]=pc
                    elif b not in Wr: pass
                elif kind=='W':
                    W_nr.setdefault(b,set()).add((ph,pc))
print('iterations',n_it,'render rbw bytes',len(R_ren),'non-render written bytes',len(W_nr))
ch=sorted(b for b in R_ren if b in W_nr and not(0x7d00<=b<0x8100))
iv=[]
for b in ch:
    if iv and b-iv[-1][1]<=2: iv[-1][1]=b
    else: iv.append([b,b])
for s,e in iv:
    ph=sorted({p for b in range(s,e+1) if b in W_nr for p,_ in W_nr[b]})
    wp=sorted({hex(pc) for b in range(s,e+1) if b in W_nr for _,pc in W_nr[b]})[:4]
    rp=sorted({hex(R_ren[b]) for b in range(s,e+1) if b in R_ren})[:4]
    print(f'{s:06x}-{e:06x} {e-s+1:4d} {ph} wpc {wp} readers {rp}')
import json
json.dump({'rbw':sorted(R_ren),'wnr':sorted(W_nr)}, open('/tmp/chanN_last.json','w'))
