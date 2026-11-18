"""python3 analyze2.py LOG TE  -> LOG_ticks.json (per tick: events with times relative to the tick start)"""
import sys, json
sys.path.insert(0,'work/triple')
from parse import *
path, TE = sys.argv[1], int(sys.argv[2])
ev = parse(path)
V = CYC
T = lambda e: e[1]*V + e[2]
ticks=[]; cur=None
for e in ev:
    t=T(e)
    if e[0]==TE:
        if cur is not None:
            cur['end']=t; cur['mem']=e[3]; ticks.append(cur)
        cur=dict(start=t, ev=[]); continue
    if cur is not None: cur['ev'].append((e[0],t))
out=[]
for tk in ticks:
    E=tk['ev']; s=tk['start']
    d=dict(len=tk['end']-s)
    mem=tk['mem']; g=lambda a,n: int.from_bytes(bytes(mem.get(a+i,0) for i in range(n)),'big')
    d['nextra']=g(0xb8f32,2); d['pass']=g(0x100e,2); d['dext']=g(0xb8f24,2); d['speech']=mem.get(0x11ab,0)!=0
    f=lambda tag: [t-s for gg,t in E if gg==tag]
    if not f(1) or not f(3): continue
    d['main_end']=f(3)[0]; d['top']=f(1)[0]
    d['main_guard']=f(9)[0] if f(9) else None
    # main first write = first tag 8 after tag 9
    m8=[t-s for gg,t in E if gg==8]
    d['main_first']=m8[0] if m8 else None
    # extras: split by tag 6
    ex=[]
    T6=f(6)
    for k,t6 in enumerate(T6):
        nxt=T6[k+1] if k+1<len(T6) else 1e18
        seg=[(gg,t-s) for gg,t in E if t-s>=t6 and t-s<nxt]
        first=lambda tag,after=None: next((t for gg,t in seg if gg==tag),None)
        rec=dict(t6=t6)
        rec['t22']=first(22); rec['t23']=first(23); rec['w0']=first(7)
        w=[t for gg,t in seg if gg==7]; rec['w1']=max(w) if w else None; rec['nw']=len(w)
        rec['t8']=first(8)
        for nm,tag in (('t24',24),('t25',25),('t26',26),('t27',27),('t28',28),('t5',5)): rec[nm]=first(tag)
        ex.append(rec)
    # events before first extra
    d['ex']=ex
    d['t4']=[t for t in f(4)]
    d['t32']=f(32)[0] if f(32) else None
    d['t20']=f(20)[0] if f(20) else None; d['t21']=[t for t in f(21)]
    d['t30']=f(30)[0] if f(30) else None; d['t31']=f(31)[0] if f(31) else None
    out.append(d)
json.dump(out, open(path.replace('.json.log','_ticks.json'),'w'))
print('ticks',len(out))
