"""Strategic layer experiment: (1) call $2b948 (invasion route builder: Dijkstra over the island graph,
then $2bf50 route expansion and $2c0f0 force creation) once via a stub at $B3000 hijacked into the
frame loop at $31498; (2) advance the game clock by whole hours and dump the force table $efc0."""
import sys
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
from live import *
def main(out='/tmp/ai/forces.txt', hours=30, src=None, dst=None):
    h=start()
    try:
        time.sleep(3)
        stub=[0x4e,0xb9,0x00,0x02,0xb9,0x48, 0x4e,0xf9,0x00,0x03,0x14,0x98]
        h.debug('w $b3000 '+' '.join('$%02x'%b for b in stub),0.3)
        if src is not None: w16(h,0x93b0,src)
        if dst is not None: w16(h,0x93ae,dst)
        open('/tmp/ai/stub.txt','w').write('r pc=$b3000\n')
        h.debug('b all',0.3)
        n0=len(h._logtext())
        h.cmd('hatari-debug b pc = $31498 :trace :once :file /tmp/ai/stub.txt')
        time.sleep(6)
        print(h._logtext()[n0:][-600:])
        o=[]
        o.append('route100e4 '+mem(h,0x100e4,24).hex(' '))
        o.append('fce8 '+mem(h,0xfce8,96).hex(' ',2))
        o.append('93ae/93b0 '+mem(h,0x93ae,4).hex(' ',2))
        for i in range(6):
            o.append('force%d '%i+mem(h,0xefc0+0x30*i,0x30).hex(' ',2))
        h.debug('w $eb96 $ff $ff',0.2); w16(h,0xeb94,0)
        eb8c=int.from_bytes(mem(h,0xeb8c,4),'big')
        o.append('eb8c %d eb90 %d'%(eb8c,int.from_bytes(mem(h,0xeb90,4),'big')))
        open(out,'w').write('\n'.join(o))
        for k in range(hours):
            eb90=int.from_bytes(mem(h,0xeb90,4),'big')
            w32(h,0xeb8c,eb90+60)
            time.sleep(1.2)
            o.append('--- hour %d eb8c=%d eb90=%d eb96=%s'%(k+1,int.from_bytes(mem(h,0xeb8c,4),'big'),int.from_bytes(mem(h,0xeb90,4),'big'),mem(h,0xeb96,2).hex()))
            for i in (0,3,7):
                f=mem(h,0xefc0+0x30*i,0x30)
                if f[0]&0x80 and f[1]==0xff: break
                o.append(' f%d x=%d y=%d str=%d thr=%d losses=%d typ=%d c=%04x e=%04x spd=%d seg=%d/%d loc=%04x wait=%d tmr=%d'%(i,int.from_bytes(f[0:2],'big'),int.from_bytes(f[2:4],'big'),int.from_bytes(f[4:6],'big'),int.from_bytes(f[6:8],'big'),int.from_bytes(f[14:16],'big')&0x1fff,int.from_bytes(f[10:12],'big'),int.from_bytes(f[12:14],'big'),int.from_bytes(f[14:16],'big'),int.from_bytes(f[24:26],'big'),int.from_bytes(f[32:34],'big'),int.from_bytes(f[30:32],'big'),int.from_bytes(f[38:40],'big'),int.from_bytes(f[40:42],'big'),int.from_bytes(f[42:44],'big')))
            open(out,'w').write('\n'.join(o))
    finally:
        h.close()
if __name__=='__main__': main()
