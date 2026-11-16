import sys; sys.path.insert(0,'work/hud')
from hudlab import *
V=[('100e',2),('10ba',2),('10c0',2),('10ca',2),('10ce',4),('10d8',4),('11c2',2),('11d9',1),('11dc',1),('10dc',2),('10de',2),('10e0',2),('10e2',2),('11ab',1),('11ac',1),('11ad',1),('11ae',1),('11b1',1),('11b2',1),('10f8',1),('10f9',1),('10ca',2),('1226',1),('1024',1),('5ff8',2),('130c',2),('11ce',1),('11cf',1)]
def val(m,a,n):
    try: return int.from_bytes(bytes(m[a+i] for i in range(n)),'big')
    except KeyError: return None
def show(r,vars=V):
    hdr=' '.join(f'{a:>5s}' for a,_ in vars); print(hdr)
    for k in sorted(r.state):
        m=r.state[k]; print(' '.join(f'{val(m,int(a,16),n):5x}' if val(m,int(a,16),n) is not None else '    -' for a,n in vars))
if __name__=='__main__':
    r=run(sys.argv[1],{},int(sys.argv[2]),state=HUD_STATE,stages=False)
    show(r)
