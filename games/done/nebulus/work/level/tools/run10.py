from nl2 import *
import struct
h=Nebulus(workdir='/tmp/strun-nl2')
def slots():
    d=grab(h,0x33944,0x80,'sl')
    out=[]
    for s in range(4):
        W=lambda off: struct.unpack('>H',d[off+2*s:off+2*s+2])[0]
        out.append(dict(x=W(0),y=W(0xc),st=W(0x48),v54=W(0x54),k6c=W(0x6c)))
    return out
try:
    ok=h.boot_to_title(); time.sleep(2); cheat(h); time.sleep(1)
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(4)
    print('baseline slots',slots(),flush=True)
    for tag,vals in (('A','$10 $20 $30 $40'),('B','$60 $70 $50 $41')):
        poke(h,0x43c17,vals)
        h.key('F1',hold=0.6); time.sleep(3)
        print(tag,vals,'RAM',grab(h,0x43c17,4,'r').hex(),flush=True)
        h.shot(L+f'shots/k_{tag}.png')
        print(tag,'slots',slots(),flush=True)
        # grid copy of those cells
        print(tag,'grid',[grab(h,0x327f0+0x100*a+1,1,'g').hex() for a in (5,6,7,8)],flush=True)
finally:
    h.close()
