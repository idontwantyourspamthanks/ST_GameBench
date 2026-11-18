"""g1.py TAG machine : cold boot on IMG, report marker/sites/hook bytes, screenshots of the three title pages, F10 and D opens."""
import os, sys, time
from kh import KH
from stharness import TOS
IMG=os.environ['IMG']; tag=sys.argv[1]; mach=sys.argv[2]
wd=f'/tmp/nf/g1_{tag}'
if mach=='megaste': h=KH(IMG, workdir=wd, machine='megaste', tos=TOS['2.06'], mem=4096, auto=r'C:\NEBULUS\START.TOS')
else: h=KH(IMG, workdir=wd, auto=r'C:\NEBULUS\START.TOS')
def mark(): return '48 69 67 68' in h.debug('m $3d00f 4',0.25)
while not mark(): time.sleep(1.5)
print('title at', round(time.time()-h.t0,1), 's after Hatari start')
last=lambda s: s.strip().splitlines()[-1]
h.debug(f'savebin {wd}/b.bin $b0000 $40',1.0); b=open(f'{wd}/b.bin','rb').read(); print('marker (savebin $b0020):', b[0x20:0x24], 'count', int.from_bytes(b[0x24:0x26],'big'), '| debugger m $b0020:', last(h.debug('m $b0020 8',0.3)))
print('hooks $3851a', last(h.debug('m $3851a 6',0.3)), '| $3d662', last(h.debug('m $3d662 8',0.3)))
time.sleep(1)
got={}
t0=time.time()
while len(got)<3 and time.time()-t0<60:
    p=h.peekw(0x3d5b6); c=h.peekw(0x3d5b8)
    if p not in got and 50<=c<=70:
        out=f'/tmp/nf/g1_{tag}_p{p}.png'; h.shot(out); got[p]=out; print('page',p,'ctr',c,out)
if len(sys.argv)>3 and sys.argv[3]=='keys':
    for key in ('F10','d'):
        h.tap(key,0.1); time.sleep(1.0)
        print(key,'-> $70', hex(h.peekl(0x70)), '(game VBL = 0x382d8)')
        if h.peekl(0x70)!=0x382d8:
            h.shot(f'/tmp/nf/g1_{tag}_mgr_{key}.png')
            for i in range(6):
                h.tap('F10',0.6); time.sleep(0.8)
                if h.peekl(0x70)==0x382d8: break
            time.sleep(1.0)
h.close()
