"""Static byte accounting of the Amiga music data (operand space)."""
import sys; sys.path.insert(0,'.')
from mwmusic import *
H3=0x89478
used=[]          # (start,len,what)
def add(a,n,w): used.append((a,n,w))
add(TUNE_TABLE+16,17*16,'tune table (17 x 4 ptrs)')
envs={}; pats={}; lists={}; insts={}
for n in range(1,18):
    for c in range(4):
        p=u32(TUNE_TABLE+16*n+4*c)
        L=read_list(p)
        lists[p]=len(L)*4+4
        for pp in L:
            if pp in pats: continue
            ev,end=parse_pattern(pp); pats[pp]=end-pp
            for e in ev:
                if e[0]=='ENV': envs[e[3][0]]=1
                if e[0]=='INSTR': insts[e[3][0]]=1
def env_len(a):
    p=a+4
    while u16(p)!=0xff: p+=2
    return p+2-a
for a in envs: envs[a]=env_len(a)
tot_pat=sum(pats.values()); tot_list=sum(lists.values()); tot_env=sum(envs.values())
print('tunes 17; unique lists',len(lists),'bytes',tot_list,'; unique patterns',len(pats),'bytes',tot_pat,'; unique envelopes',len(envs),'bytes',tot_env,'; instrument descriptors',len(insts),'x14 =',14*len(insts))
print('tune table',17*16)
print('score total (tune table + lists + patterns + envelopes + descriptors) =',17*16+tot_list+tot_pat+tot_env+14*len(insts))
# per tune
for n in range(1,18):
    ps=set();es=set();ins=set();lb=0
    for c in range(4):
        p=u32(TUNE_TABLE+16*n+4*c); L=read_list(p); lb+=len(L)*4+4
        for pp in L:
            ps.add(pp)
            ev,end=parse_pattern(pp)
            for e in ev:
                if e[0]=='ENV': es.add(e[3][0])
                if e[0]=='INSTR': ins.add(e[3][0])
    nb=lb+16+sum(pats[p] for p in ps)+sum(envs[e] for e in es)+14*len(ins)
    print(f'tune {n:2d}: patterns {len(ps):2d} envelopes {len(es)} instruments {len(ins):2d} score bytes {nb}')
print('envelopes:')
for a,l in sorted(envs.items()):
    w=[u16(a+4+2*i) for i in range((l-4)//2)]
    print(hex(a),'volsub',u16(a),'voladd',u16(a+2),'len',l,'steps',w[:40])
# sample regions
rg={}
for a in insts:
    f=u16(a)
    rg[(u32(a+2),u16(a+6)*2)]=1
    if f: rg[(u32(a+8),u16(a+12)*2)]=1
tot=0
for (lc,ln) in sorted(rg):
    if lc>=H3: tot+=ln
print('sample bytes (hunk 3 regions)',tot,'regions',sum(1 for lc,ln in rg if lc>=H3))
