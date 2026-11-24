import json, sys, statistics as st
from collections import Counter
V=160256
r=json.load(open(sys.argv[1]))
idx=[i for i in range(1,len(r)) if r[i]['pass']<r[i-1]['pass']]
rs=idx[0] if idx else 0
race=[d for d in r[rs:] if d['pass']>=130]
print('all ticks',len(r),'racing ticks (after restart, pass>=130)',len(race))
def hist(l): return dict(sorted(Counter(l).items()))
for nm,sel in (('racing',race),):
    print('== ',nm,'extras per tick',hist(d['nextra'] for d in sel), 'mean main_end %.3f VBL'%st.mean(d['main_end']/V for d in sel))
    print('   tick length mean %.3f; ticks longer than 5.05 VBL: %d, shorter than 4.95: %d'%(st.mean(d['len']/V for d in sel), sum(d['len']/V>5.05 for d in sel), sum(d['len']/V<4.95 for d in sel)))
    ex=[(d,e) for d in sel for e in d['ex']]
    print('   extras drawn',len(ex))
    pre=[(e['w0']-e['start'])/V for d,e in ex]; wait=[(e['first']-e['w0'])/V for d,e in ex]; post=[(e['flip']-e['first'])/V for d,e in ex]; tot=[(e['flip']-e['start'])/V for d,e in ex]
    gap=[(e['start']-d['main_end'])/V for d,e in ex]
    for n,l in (('gap main flip entry -> extra fe50',gap),('pre-latch work',pre),('latch wait (loop)',wait),('post-latch',post),('total start->flip',tot)):
        print('   %-34s mean %.3f  min %.3f  median %.3f  max %.3f'%(n,st.mean(l),min(l),st.median(l),max(l)))
    print('   latch wait histogram (VBL, 0.1 bins):',hist(round(w*10)/10 for w in wait))
    nz=[w for w in wait if w>0.02]
    print('   extras with a wait >0.02 VBL: %d of %d; mean wait of those %.3f'%(len(nz),len(ex),st.mean(nz) if nz else 0))
    # extras per tick vs main_end bucket
    for lo,hi in ((0,2.5),(2.5,2.75),(2.75,3.0),(3.0,3.25),(3.25,3.5),(3.5,9)):
        s=[d for d in sel if lo<=d['main_end']/V<hi]
        if s: print('   main_end in [%.2f,%.2f): ticks %d, with extra %.0f%%'%(lo,hi,len(s),100*sum(d['nextra']>0 for d in s)/len(s)))
    late=[(d,e) for d,e in ex if e['flip']>5.0*V+0.05*V]
    print('   extras whose flip came after the 5.0 VBL grid +0.05: %d of %d'%(len(late),len(ex)))
    print('   extra flip time (VBL from tick start) histogram:',hist(round(e['flip']/V*4)/4 for d,e in ex))
    nextra0=[d for d in sel if d['nextra']==0]
    print('   ticks with no extra: main_end mean %.3f, mean idle to tick end %.3f VBL'%(st.mean(d['main_end']/V for d in nextra0), st.mean((d['len']-d['main_end'])/V for d in nextra0)))
