import sys, pickle, collections, statistics, struct
sys.path.insert(0,'work/sprite')
from analyze import *
import numpy as np
S16=lambda v: v-65536 if v>=32768 else v
NF={'race_grid':142,'race_start':120,'race_up':120,'race_drive':78}
allc=pickle.load(open('work/sprite/calls.pkl','rb'))
def vis_rows(x):
    y=x['y']; r=S16(x['rows']); top=-y if y<0 else 0; r2=r-top; y0=max(y,0)
    return max(0,min(r2,200-y0))
out=[]
def P(*a): 
    s=' '.join(str(x) for x in a); print(s); out.append(s)
# 1. per class cycles per frame (net slot time)
P("## T1 cycles per frame by class (slot net time = dispatch + draw; ISR time excluded), mean over traced frames")
P("| scene | frames | player (slot12) | player2 (slot49) | opponents 13-15 | scenery type 0 | scenery type 1/3 composites | inactive slots | stage total |")
P("|---|---|---|---|---|---|---|---|---|")
for sc in NF:
    fr=frames(f'work/sprite/raw/{sc}.log')
    agg=collections.defaultdict(float); tot=0
    for f in fr:
        ev=f['ev']; tn=lambda e:e['t']-e['isr']
        tot+=tn(ev[-1])-tn(ev[0])
        agg['head']+=tn(next(e for e in ev if e['pc'] in (0xe598,0xe568)))-tn(ev[0])
        for r in slots(f):
            c=cls(r['a2'])
            if not r['calls']: agg['inactive']+=r['net']; continue
            if c=='scenery': agg['t13' if r['calls'][0]['pc']!=0xed6e else 't0']+=r['net']
            else: agg[c]+=r['net']
    n=len(fr)
    P(f"| {sc} | {n} | {agg['player']/n:,.0f} | {agg['player2']/n:,.0f} | {agg['opponent']/n:,.0f} | {agg['t0']/n:,.0f} | {agg['t13']/n:,.0f} | {(agg['inactive']+agg['head'])/n:,.0f} | {tot/n:,.0f} |")
# 2. call histogram
P("\n## T2 type-0 single-sprite calls per frame by size class (columns x aligned/shifted), visible rows, mean kernel cycles")
P("| scene | cols | x&15 | calls/frame | mean visible rows | mean kernel cycles/call | kernel cycles/frame |")
P("|---|---|---|---|---|---|---|")
for sc in NF:
    l=[x for x in allc if x['sc']==sc and x['kind']=='t0']
    by=collections.defaultdict(list)
    for x in l:
        if S16(x['rows'])>0 and x.get('kcyc') and x['kcyc']>600:
            by[(x['cols'],'shifted' if x['shift'] else 'aligned')].append(x)
    for k in sorted(by):
        v=by[k]
        P(f"| {sc} | {k[0]} | {k[1]} | {len(v)/NF[sc]:.2f} | {statistics.mean(vis_rows(x) for x in v):.1f} | {statistics.mean(x['kcyc'] for x in v):,.0f} | {sum(x['kcyc'] for x in v)/NF[sc]:,.0f} |")
# 3. call outcomes
P("\n## T3 type-0 call outcomes (calls per frame)")
P("| scene | drawn | rows<=0 (nothing) | x off screen | y clipped to nothing | composite (type 1/3) objects | slots active (drawn) | slots in sort list not drawn |")
P("|---|---|---|---|---|---|---|---|")
for sc in NF:
    l=[x for x in allc if x['sc']==sc and x['kind']=='t0']
    cnt=collections.Counter()
    for x in l:
        cw=x['cols']*16
        if S16(x['rows'])<=0: cnt['rows']+=1
        elif x['x']<=-cw or x['x']>=320: cnt['x']+=1
        elif vis_rows(x)<=0: cnt['y']+=1
        else: cnt['drawn']+=1
    t13=len([x for x in allc if x['sc']==sc and x['kind']=='t13'])
    fr=frames(f'work/sprite/raw/{sc}.log'); nd=0; nn=0
    for f in fr:
        for r in slots(f):
            if r['calls']: nd+=1
            else: nn+=1
    n=NF[sc]
    P(f"| {sc} | {cnt['drawn']/n:.1f} | {cnt['rows']/n:.1f} | {cnt['x']/n:.1f} | {cnt['y']/n:.1f} | {t13/n:.1f} | {nd/len(fr):.1f} | {nn/len(fr):.1f} |")
# 4. fits
P("\n## T4 stock kernel cost fit, cycles = a + b * visible rows (type-0 calls of all four scenes)")
by=collections.defaultdict(list)
for x in allc:
    if x['kind']=='t0' and x.get('kcyc') and S16(x['rows'])>0 and x['kcyc']>600: by[(x['cols'],x['shift']!=0)].append(x)
P("| cols | x&15 | calls | a | b (cycles/row) | b per column-row |")
P("|---|---|---|---|---|---|")
for k in sorted(by):
    l=by[k]; A=np.array([[1,vis_rows(x)] for x in l],float); y=np.array([x['kcyc'] for x in l],float)
    co=np.linalg.lstsq(A,y,rcond=None)[0]
    P(f"| {k[0]} | {'shifted' if k[1] else 'aligned'} | {len(l)} | {co[0]:.0f} | {co[1]:.0f} | {co[1]/k[0]:.0f} |")
# 5. kernels used
P("\n## T5 kernel variants (type 0 full entries) over all traced calls")
cnt=collections.Counter(); cyc=collections.Counter()
for x in allc:
    if x['kind']=='t0' and x.get('kcyc'): cnt[(x['nib'],x['cols'],hex(x['kernel']))]+=1; cyc[(x['nib'],x['cols'],hex(x['kernel']))]+=x['kcyc']
P("| nibble | cols | entry | calls | cycles (M) |"); P("|---|---|---|---|---|")
for k,v in sorted(cnt.items(), key=lambda kv:-cyc[kv[0]]): P(f"| {k[0]} | {k[1]} | {k[2]} | {v} | {cyc[k]/1e6:.2f} |")
open('work/sprite/out/report_tables.md','w').write('\n'.join(out)+'\n')
