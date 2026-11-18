import sys, json; sys.path.insert(0,'work/hud')
from analyze import *
ELEM=[('f1c0','overheat puff erase'),('efc6','thermometer'),('f214','minimap box fill'),('f22c','minimap'),('f3b6','score'),('f430','position no.'),('f53c','stopwatch dial'),('11ef0','message ticker'),('f90c','talking face'),('f620','turbo-fuel tank'),('f76a','gear lever'),('f7f0','speedometer'),('f134','overheat puff')]
def classes(p,s):
    c={}
    for k in p:
        if k in s:
            a=s[k]['11ab']; er=p[k]['stage']['11ef0']>20000
            c[k]='erase' if er else 'typing' if a==1 else 'hold' if a and a>=2 else 'none'
    return c
def tab(scene, title):
    p,s=load(f'skip_{scene}_stock'); c=classes(p,s)
    print(f"\n### {title}")
    classes_=['none','typing','hold','erase']
    cols={}
    for cl in classes_:
        ks=[k for k in c if c[k]==cl]
        if not ks: continue
        w=sum(p[k]['work'] for k in ks)/len(ks)
        cols[cl]=(len(ks),w,{n:sum(p[k]['stage'].get(n,0) for k in ks)/len(ks) for n,_ in ELEM+[('de1c',''),('de6c','')]})
    print('| call | element | '+' | '.join(f"{cl} (n={cols[cl][0]}) cyc / %" for cl in cols)+' |')
    print('|---|---|'+'---:|'*len(cols))
    for n,lab in ELEM:
        print(f"| `{n}` | {lab} | "+' | '.join(f"{cols[cl][2][n]:,.0f} / {100*cols[cl][2][n]/cols[cl][1]:.1f}%" for cl in cols)+' |')
    hud=lambda cl: sum(cols[cl][2][n] for n,_ in ELEM)
    print('| HUD total (13 calls) | | '+' | '.join(f"{hud(cl):,.0f} / {100*hud(cl)/cols[cl][1]:.1f}%" for cl in cols)+' |')
    print('| clouds `de1c`+`de6c` | | '+' | '.join(f"{cols[cl][2]['de1c']+cols[cl][2]['de6c']:,.0f} / {100*(cols[cl][2]['de1c']+cols[cl][2]['de6c'])/cols[cl][1]:.1f}%" for cl in cols)+' |')
    print('| pass work (loop top to flip) | | '+' | '.join(f"{cols[cl][1]:,.0f}" for cl in cols)+' |')
tab('race_start','race_start (driving)'); tab('race_grid','race_grid (standing, time-out state)')
