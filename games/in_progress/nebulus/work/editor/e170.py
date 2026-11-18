"""Cold boot gate: marker NEPO, site count, hooks in RAM, F10 and D open the manager. usage: e170.py GAMEDIR WORKDIR [ste|megaste]"""
from e160_lib import *
GAMEDIR=sys.argv[1]; WD=sys.argv[2]; MACH=sys.argv[3] if len(sys.argv)>3 else 'ste'
h=mk(GAMEDIR,WD,MACH); t=T(h)
fails=[]
def chk(n,g,e):
    ok=g==e; print(('PASS ' if ok else 'FAIL ')+n+': '+repr(g)+('' if ok else ' expected '+repr(e)),flush=True)
    if not ok: fails.append(n)
try:
    print('title',h.boot_to_title(timeout=240),flush=True); time.sleep(3)
    m=grab(h,0xb0020,8,'mk'); print('marker/count',m[:4],struct.unpack('>H',m[4:6])[0] if False else m.hex())
    chk('marker NEPO',m[:4],b'NEPO'); cnt=struct.unpack('>H',grab(h,0xb0024,2,'cnt'))[0]; chk('site count word',cnt,20)
    chk('hook $3851a -> ed_key',grab(h,0x3851a,2,'a').hex(),'4ef9'); chk('hook $3d662',grab(h,0x3d662,2,'b').hex(),'4ef9')
    chk('block CODE1 magic (jump table at $75740)',grab(h,0x75740,2,'c').hex(),'4ef9')
    chk('block CODE4 $77dc0 first word nonzero',grab(h,0x77dc0,2,'d')!=b'\0\0',True)
    chk('trainer blob intact (first hook insn at $76c08)',grab(h,0x76c08,2,'e').hex(),'4eb9')
    v70=struct.unpack('>L',grab(h,0x70,4,'v'))[0]; chk('VBL vector normal',hex(v70),'0x382d8')
    h.key('F10',hold=0.1); time.sleep(2); v=struct.unpack('>L',grab(h,0x70,4,'v'))[0]; chk('F10 (100 ms tap) opens the manager (VBL = editor)',v!=0x382d8,True); h.shot(E+f'e170_{MACH}_manager.png')
    h.key('F10',hold=0.1); time.sleep(2.5); chk('F10 leaves again',struct.unpack('>L',grab(h,0x70,4,'v'))[0],0x382d8)
    time.sleep(1); h.key('d',hold=0.1); time.sleep(2); v=struct.unpack('>L',grab(h,0x70,4,'v'))[0]; chk('D opens the manager',v!=0x382d8,True)
finally: pass
print('FAILS',fails); h.close()
