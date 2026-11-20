"""python3 incl.py NAME... : inclusive cycles/pass for each top-level call of the pass (static call graph over the profile buckets); several NAMEs side by side"""
import sys, bisect, struct
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, G+'/tools')
import msrprof as P
TOP=[0xf9fa,0xfb96,0xfc2a,0xfc80,0xfce4,0xfd64,0xfa2c,0x10ca6,0x1125c,0x113d4,0x1147a,0x11792,0x112c4,0x11342,0x11230,0x11396,0xfe50,0xff76,0x1003c,0x17c24,0x100b4,0x17c42,0x10a5e,0x10a98,0xe218,0xe2e8,0x1182e,0x11a3c,0xe316,0x18318,0xe406,0xef7a,0x18888,0x18c86,0x18f0e,0xd1e4]
ENTRY={0x100b4:0xb4004,0x17c42:0xb5004,0xef7a:0xbb004}
def run(name):
    ram=open(f'{G}/work/tightC/res/ram_{name}.bin','rb').read()
    prof=P.load(f'{G}/work/tightC/res/prof_{name}.txt')
    tg=set(P.targets(ram)); tg|={0xb3040,0xb4004,0xb5004,0xb6000,0xbb004,0xbb700}
    tg=sorted(tg)
    frames=prof.get(0xd1ca,(0,0))[1]
    ex={}
    for a,(c,n) in prof.items():
        i=bisect.bisect_right(tg,a)-1; f=tg[i] if i>=0 else a
        ex[f]=ex.get(f,0)+c
    # call graph: scan each function's bytes
    calls={}
    ends=tg+[0xbe000]
    for k,f in enumerate(tg):
        hi=ends[k+1]; s=set()
        if f<0x800 or f>=0xbe000: continue
        for a in range(f,min(hi,len(ram)-6),2):
            op=struct.unpack_from('>H',ram,a)[0]
            if op in (0x4EB9,0x4EF9):
                x=struct.unpack_from('>I',ram,a+2)[0]
            elif op==0x6100: x=a+2+struct.unpack_from('>h',ram,a+2)[0]
            elif (op&0xff00)==0x6100 and (op&0xff) not in (0,0xff): x=a+2+struct.unpack_from('>b',ram,a+1)[0]
            else: continue
            if x in ex or x in tg: s.add(x)
        calls[f]=s
    res={}; used=set()
    for t in TOP:
        e=ENTRY.get(t,t); seen=set(); st=[e]
        while st:
            f=st.pop()
            if f in seen: continue
            seen.add(f); st.extend(calls.get(f,()))
        res[t]=(sum(ex.get(f,0) for f in seen), seen)
    tot=sum(ex.values())
    return frames,tot,res,ex
names=sys.argv[1:]
R=[run(n) for n in names]
print('frames',[r[0] for r in R],'cyc/frame',[round(r[1]/r[0]) for r in R])
for t in TOP:
    print(f'${t:05x} '+' '.join(f'{r[2][t][0]/r[0]:9.0f}' for r in R))
