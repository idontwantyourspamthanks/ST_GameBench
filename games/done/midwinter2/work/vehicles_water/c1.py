from vw import *
import sys
snap=sys.argv[1]; n=int(sys.argv[2]); ty=sys.argv[3]
pokes=[wb(0x6fba,int(sys.argv[4])<<16,4), wb(0x6fb6,(int(sys.argv[5])&0xffff)<<16,4)]
rows=run(SNAP/snap,'c1_'+ty,n,pokes=pokes)
def S(r):
    return dict(X=r.l(0x66e6),Y=r.l(0x66ea),H=r.w(0x6742),H94=r.w(0x6294),lean=r.sw(0x674e),bank=r.sw(0x6746),pit=r.sw(0x674a),thr=r.sw(0x6750),r52=r.sw(0x6752),r56=r.sw(0x6756),r5a=r.sw(0x675a),d40=r.sw(0x6740),spd=r.sw(0x6772),alt=r.sw(0x764c),r2=r.sw(0x66e2),r4=r.sw(0x66e4),cd=r.w(0x6290),f84=r.sw(0xf984),b6=r.sw(0x6888),t=r.w(0x6220),s36=r.sw(0x34936),s38=r.sw(0x34938),s3a=r.sw(0x3493a),p76e=r.w(0x676e))
for i,r in enumerate(rows):
    print(i,S(r))
