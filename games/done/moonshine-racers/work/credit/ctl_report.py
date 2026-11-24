import json, glob, os, sys
R='work/credit/st_ctl_%s.json'
PAR={'0x1004','0x1005','0x1006','0x1007','0x1008','0x1009','0x100a','0x100b','0x12f2'}
def load(n): return json.load(open(R%n))
def key(m): return (m['0x100e']<<8)|m['0x100f']
def cmp(A,B):
    ka,kb=[key(m) for m in A],[key(m) for m in B]
    best=None
    for s in range(-12,13):
        pairs=[(i+s,i) for i in range(len(B)) if 0<=i+s<len(A) and ka[i+s]==kb[i]]
        if best is None or len(pairs)>len(best): best=pairs
    bad={}
    for a,b in best:
        for ad in A[a]:
            if A[a][ad]!=B[b].get(ad): bad.setdefault(ad,[]).append(ka[a])
    return len(best),bad
ref=load('stock_a')
names=['stock_b','stock_c','real_a','real_b','real_c']+[f'delay_{n}' for n in (0,500,1500,3000,6000,9000,12000,20000,30000)]
print(f"reference stock_a: $1006={ref[0].get('0x1006')} $100a={ref[0].get('0x100a')} $12f2={ref[0].get('0x12f2')} $1221={ref[0].get('0x1221')}, {len(ref)} passes")
for n in names:
    if not os.path.exists(R%n) or os.path.getsize(R%n)<10: print(n,'(no data)'); continue
    B=load(n); c,bad=cmp(ref,B)
    par=sorted(a for a in bad if a in ('0x1006','0x100a','0x12f2'))
    other=sorted((a for a in bad if a not in ('0x1006','0x100a','0x12f2')),key=lambda x:int(x,16))
    print(f"{n:12s} passes {len(B)} common {c}: $1006={B[0].get('0x1006')} $100a={B[0].get('0x100a')} $12f2={B[0].get('0x12f2')} | parity addrs differing: {par or 'none'} | other differing addrs: {[(a,len(bad[a])) for a in other] or 'none'}")
