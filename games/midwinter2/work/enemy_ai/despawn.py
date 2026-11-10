import sys
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
from live import *
h=start()
try:
    time.sleep(3)
    px=int.from_bytes(mem(h,0x66bc,2),'big'); py=int.from_bytes(mem(h,0x66be,2),'big')
    g=0xc6fc+0x10*4
    w16(h,g,px+14,py+3); w16(h,g+10,0)
    out=[]
    for k in range(40):
        time.sleep(0.5)
        e=mem(h,0x3532,0x42); gm=mem(h,g,16)
        typ=int.from_bytes(e[0x2e:0x30],'big'); st=int.from_bytes(e[0x3a:0x3c],'big')
        out.append('t=%.1f typ=%d st=%d x=%d y=%d  garrison +8 deployed=%d +4=%d +e=%04x'%(k*0.5,typ if typ<32768 else typ-65536,st,int.from_bytes(e[6:10],'big'),int.from_bytes(e[10:14],'big'),int.from_bytes(gm[8:10],'big'),int.from_bytes(gm[4:6],'big'),int.from_bytes(gm[14:16],'big')))
        if k==10 and typ>0:
            w32(h,0x3532+6,int.from_bytes(e[6:10],'big')+9000)
            out.append('--- poked NPC0 x += 9000 (player offset now %d)'%(int.from_bytes(e[6:10],'big')+9000-25600))
    open('/tmp/ai/despawn.txt','w').write('\n'.join(out))
finally:
    h.close()
