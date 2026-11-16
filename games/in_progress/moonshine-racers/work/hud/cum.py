import sys; sys.path.insert(0,'work/hud')
from skiprun import go
scene=sys.argv[1]; npass=int(sys.argv[2])
order=['f22c','f214','f620','f76a','f90c','f7f0','f3b6','f53c','f430','efc6','f1c0','f134']
cfgs=[]; acc=[]
for i,n in enumerate(order):
    acc.append(n)
    if n in ('f214','f620','f76a','f90c','f7f0','f3b6','f53c','f134'): cfgs.append('+'.join(acc))
for c in cfgs:
    r=go(scene,npass,'cum_'+c if False else c,gate=False,tag=f"{scene}_cum_{len(c.split('+'))}")
    print(c,len(r),flush=True)
