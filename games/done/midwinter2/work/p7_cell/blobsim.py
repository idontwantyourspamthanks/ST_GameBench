import glob, sys
from model import *
def asr(v,n): return v>>n
def prologue(m):
    D={'EN':0,'HI':-1}
    if W(m,0x67be)!=0: return D
    mY=S(m,0x1856a); mW=S(m,0x1856c)
    if abs(mY)>16384 or abs(mW)>16384: return D
    K=9*mY+4*mW
    if K<0: return D
    Kc=(K+63)>>6
    zc=S(m,0x1878c)
    if zc<0: return D
    VY=(-zc*mY)>>14; VW=(-zc*mW)>>14
    t1y0=S(m,0x188fa); t1w0=S(m,0x188fc); t2y0=S(m,0x18a42); t2w0=S(m,0x18a44)
    for v in (t1y0,t1w0,t2y0,t2w0):
        if abs(v)>12000: return D
    d1y=s16(S(m,0x18902)-t1y0); d1w=s16(S(m,0x18904)-t1w0)
    d2y=s16(S(m,0x18a4a)-t2y0); d2w=s16(S(m,0x18a4c)-t2w0)
    for v in (d1y,d1w,d2y,d2w):
        if abs(v)>512: return D
    Ay=t1y0+t2y0-VY; Aw=t1w0+t2w0-VW
    BY=abs(Ay)+7*(abs(d1y)+abs(d2y)); BW=abs(Aw)+7*(abs(d1w)+abs(d2w))
    HLIM=min(7998-BY,13998-BW)
    if HLIM<0 or zc>HLIM: return D
    HI=min(zc+HLIM,32767)
    cb1=9*t1y0+4*t1w0; s1=9*d1y+4*d1w
    cb2=9*t2y0+4*t2w0+1; s2=9*d2y+4*d2w
    TC=[cb1+(k-8)*s1+max(0,s1) for k in range(16)]
    TR=[cb2+(k-8)*s2+max(0,s2) for k in range(16)]
    TC[0]=TC[15]=TR[0]=TR[15]=0x3fffffff
    D.update(EN=1,Kc=Kc,HI=HI,TC=TC,TR=TR,HLIM=HLIM)
    return D
def celltest(m,D,c):
    if S(m,c+6)!=0: return False
    hs=[S(m,c+o) for o in (0,0x10,0x200,0x210)]
    assert min(hs)>=0
    hmax=max(hs)
    if hmax>D['HI']: return False
    ci=(S(m,c+0xc)+64)&0xffff; ei=(S(m,c+0xe)+64)&0xffff
    if ci&0xff87 or ei&0xff87: return False
    u=D['TC'][ci//8]+D['TR'][ei//8]+((D['Kc']*hmax)>>8)
    return u<0
if __name__=='__main__':
    tot=cul=ideal=false=0
    for fn in sorted(glob.glob('*_1ebda_*.bin')):
        s,r,m=analyze(fn)
        D=prologue(m)
        n=t=f=ib=0
        for c,k,a,oc in r:
            t+=1
            cu=celltest(m,D,c)
            real=(a!=0)
            if cu and not real: f+=1
            n+=cu; ib+=real
        tot+=t;cul+=n;ideal+=ib;false+=f
        print(fn,'EN',D['EN'],'HLIM',D.get('HLIM'),'cells',t,'culled',n,'real-culled',ib,'FALSE',f)
    print('total',tot,cul,ideal,false)
