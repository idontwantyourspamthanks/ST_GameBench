import sys, math
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
from live import *
h=start()
try:
    time.sleep(3)
    stub=[0x4e,0xb9,0x00,0x02,0xb9,0x48, 0x4e,0xf9,0x00,0x03,0x14,0x98]
    h.debug('w $b3000 '+' '.join('$%02x'%b for b in stub),0.3)
    open('/tmp/ai/stub.txt','w').write('r pc=$b3000\n')
    h.debug('b all',0.3)
    h.cmd('hatari-debug b pc = $31498 :trace :once :file /tmp/ai/stub.txt')
    time.sleep(6)
    buf=mem(h,0xfce8,1200)
    recs=[]
    for i in range(0,1200,6):
        x=int.from_bytes(buf[i:i+2],'big'); y=int.from_bytes(buf[i+2:i+4],'big'); l=int.from_bytes(buf[i+4:i+6],'big')
        if x==0xffff: break
        recs.append((x,y,l))
    tot=0; out=[]
    for a,b in zip(recs,recs[1:]):
        d=math.hypot(a[0]-b[0],a[1]-b[1]); tot+=d
    out.append('waypoints=%d total length=%.0f map units'%(len(recs),tot))
    for r in recs: out.append(str(r))
    out.append('fce4 %s'%mem(h,0xfce4,4).hex())
    open('/tmp/ai/route.txt','w').write('\n'.join(out))
    print('\n'.join(out[:6]))
finally:
    h.close()
