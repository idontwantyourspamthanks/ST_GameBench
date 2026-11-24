import json, sys, statistics as st
from collections import Counter
import os
V=int(os.environ.get("CYC",160256))
def load(p):
    r=json.load(open(p))
    idx=[i for i in range(1,len(r)) if r[i]['pass']<r[i-1]['pass']]
    rs=idx[0] if idx else 0
    race=[d for d in r[rs:] if d['pass']>=130]
    return r,race
def hist(l): return dict(sorted(Counter(l).items()))
def mean(l): return st.mean(l) if l else float('nan')
def report(name,p):
    r,race=load(p)
    print('=====',name,'ticks',len(r),'racing',len(race))
    h=hist(d['nextra'] for d in race); n=len(race)
    print(' extras/tick histogram',h,' share with >=1 extra %.1f%%'%(100*sum(v for k,v in h.items() if k>0)/n),' mean extras %.3f'%(sum(k*v for k,v in h.items())/n))
    print(' displayed fps ~ (passes+extras)/time = %.2f (10 passes/s x (1+mean extras))'%(10*(1+sum(k*v for k,v in h.items())/n)))
    print(' tick len mean %.3f; >5.05: %d; <4.95: %d; main_end mean %.3f'%(mean([d['len']/V for d in race]),sum(d['len']/V>5.05 for d in race),sum(d['len']/V<4.95 for d in race),mean([d['main_end']/V for d in race])))
    ex=[(d,e) for d in race for e in d['ex']]
    if not ex: return
    first=[(d,d['ex'][0]) for d in race if d['ex']]
    def row(nm,l): print('  %-46s n %3d mean %.3f min %.3f med %.3f max %.3f'%(nm,len(l),mean(l),min(l),st.median(l),max(l)))
    mf=[]
    # main flip -> extras entry
    row('main flip entry(tag3) -> extras entry (tag32)',[(d['t32']-d['main_end'])/V for d,e in first if d['t32']])
    row('extras entry -> saveundo entry',[(d['t20']-d['t32'])/V for d,e in first if d['t20'] and d['t32']])
    sv=[(d['t21'][0]-d['t20'])/V for d,e in first if d['t20'] and d['t21']]
    row('saveundo (tag20 -> tag21)',sv)
    row('saveundo exit -> fe50 (tag6)',[(e['t6']-d['t21'][0])/V for d,e in first if d['t21']])
    row('rings fe50 ff76 1003c (6->22)',[(e['t22']-e['t6'])/V for d,e in ex if e['t22']])
    row('17c24 clear (22->23)',[(e['t23']-e['t22'])/V for d,e in ex if e['t23'] and e['t22']])
    row('100b4 geometry (23->wait start)',[(e['w0']-e['t23'])/V for d,e in ex if e['w0'] and e['t23']])
    row('latch wait loop (wait start -> 17c42)',[(e['t8']-e['w0'])/V for d,e in ex if e['t8'] and e['w0']])
    row('road 17c42 (8->24)',[(e['t24']-e['t8'])/V for d,e in ex if e['t24'] and e['t8']])
    row('10a5e+10a98 (24->25)',[(e['t25']-e['t24'])/V for d,e in ex if e['t25'] and e['t24']])
    row('prerestore+e2e8+carstep+e316 (25->26)',[(e['t26']-e['t25'])/V for d,e in ex if e['t26'] and e['t25']])
    row('horizon 18318 (26->27)',[(e['t27']-e['t26'])/V for d,e in ex if e['t27'] and e['t26']])
    row('objects e406 (27->28)',[(e['t28']-e['t27'])/V for d,e in ex if e['t28'] and e['t27']])
    row('hud (28->flip call 5)',[(e['t5']-e['t28'])/V for d,e in ex if e['t5'] and e['t28']])
    row('extra frame, tag6 -> flip',[(e['t5']-e['t6'])/V for d,e in ex if e['t5']])
    row('restoreundo (tag30 -> tag31)',[(d['t31']-d['t30'])/V for d in race if d['t30'] and d['t31']])
    row('last flip -> tick end (sleep + restoreundo)',[(d['len']-max(e['t5'] for e in d['ex'] if e['t5']))/V for d in race if d['ex'] and any(e['t5'] for e in d['ex'])])
    # latch wait histogram
    w=[(e['t8']-e['w0'])/V for d,e in ex if e['t8'] and e['w0']]
    print('  latch-wait histogram (0.1 VBL):',hist(round(x*10)/10 for x in w),' >0.02: %d of %d'%(sum(x>0.02 for x in w),len(w)))
    nm=[d for d in race if not d['ex']]
    print('  no-extra ticks: n %d, main_end mean %.3f, idle (len - main_end) mean %.3f'%(len(nm),mean([d['main_end']/V for d in nm]),mean([(d['len']-d['main_end'])/V for d in nm])))
    for lo,hi in ((0,2.5),(2.5,2.75),(2.75,3.0),(3.0,3.25),(3.25,3.5),(3.5,9)):
        s=[d for d in race if lo<=d['main_end']/V<hi]
        if s: print('   main_end [%.2f,%.2f): %3d ticks, with extra %3.0f%%'%(lo,hi,len(s),100*sum(bool(d['ex']) for d in s)/len(s)))
    mw=[(d['main_first']-d['main_guard'])/V for d in race if d['main_first'] is not None and d['main_guard'] is not None]
    print('  main latch wait (tag8 - tag9): mean %.4f max %.3f; >0.02: %d of %d'%(mean(mw),max(mw),sum(w_>0.02 for w_ in mw),len(mw)))
report(sys.argv[3] if len(sys.argv)>3 else 'X8 baseline (default build)',sys.argv[1])
if len(sys.argv)>2 and sys.argv[2]!='-': report('NW8 latch waits removed (upper bound of triple buffering)',sys.argv[2])
