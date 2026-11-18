"""t6.py HOLDms KEY : trace ACIA bytes + ed_key + latch for one tap on the title (IMG env)"""
import os, sys, time, re
sys.path.insert(0,'../input')
from kh import KH
import tr
IMG=os.environ['IMG']
hold=int(sys.argv[1])/1000; key=sys.argv[2]
h=KH(IMG, workdir='/tmp/nf/t6', auto=r'C:\NEBULUS\START.TOS')
while '48 69 67 68' not in h.debug('m $3d00f 4',0.25): time.sleep(1.5)
time.sleep(2)
tr.EV['KEY']='pc = $778e6'; tr.EV['EDT']='pc = $75752+$0'   # EDT unused
order=tr.arm(h,['ACIA','KEY','POLL'])
n0=len(h._logtext()); tr.marker(h)
time.sleep(0.5)
t=time.time(); h._xdo('keydown',key); tr.marker(h); time.sleep(hold); h._xdo('keyup',key); tr.marker(h)
print('host hold', round(time.time()-t,3))
time.sleep(1.5); tr.marker(h); time.sleep(0.4)
txt=h._logtext()[n0:]; h.debug('b all',0.3)
for e in tr.parse(txt,order,160256): print(e['n'],e['vbl'],e['fc'])
print('$70',hex(h.peekl(0x70)),'rsKey',hex(h.peekw(0x77caa)))
h.close()
