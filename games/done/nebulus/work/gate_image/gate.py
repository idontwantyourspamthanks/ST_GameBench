import sys,time,struct
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ed import grab
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from stharness import Hatari, TOS
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
W=G+'work/gate_image/'
v=sys.argv[1]; joy=len(sys.argv)>2
R=W+'run_'+v
ex=['--fast-boot','no','--gemdos-drive','skip','--acsi','0='+W+v+'.img']+(['--joy1','keys'] if joy else [])
h=Hatari(game_dir=G,workdir=R,machine='ste',tos=TOS['1.62'],memsize_kb=1024,files=[],overlay='/nonexistent',autorun='',extra=ex)
print('args joy1keys=',joy,flush=True)
def mark(): return grab(h,0xb0020,8,'mk').hex()
try:
    t0=time.time(); ok=False
    while time.time()-t0<150:
        time.sleep(3)
        out=h.debug("m $3d00f 4",0.4)
        if "48 69 67 68" in out.upper(): ok=True;break
    print('title marker',ok,round(time.time()-t0),'s',flush=True)
    time.sleep(2)
    print('marker b0020',mark(),'(NEPO=4e45504f, count 27=0000001b)',flush=True)
    for i in range(14):
        h.shot(f'{R}/title_{i:02d}.png'); time.sleep(1.8)
    print('VBL vector $70',grab(h,0x70,4,'v').hex(),flush=True)
    if v=='NEBULUS':
        h.key('F10',hold=1.0); time.sleep(2)
        print('manager VBL vec',grab(h,0x70,4,'v').hex(),flush=True); h.shot(R+'/manager.png')
        h.key('F10',hold=1.0); time.sleep(2)
        print('after F10 again VBL vec',grab(h,0x70,4,'v').hex(),flush=True)
    d=grab(h,0x70000,0x10000,'big')
    for needle in (b'enhanced by dad_prg',b'F10/D'): print('RAM search',needle,[hex(0x70000+i) for i in [d.find(needle)] if i>=0],flush=True)
    time.sleep(1)
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(6)
    t=[h.peekw(0x3ad98+2*i) for i in range(3)]; print('timer words',t,'tower idx',h.peekw(0x3390c),flush=True)
    h.shot(R+'/tower0.png')
    for i in range(3):
        h.key('Right',hold=1.0); time.sleep(0.5); h.shot(R+f'/tower_r{i}.png')
    t=[h.peekw(0x3ad98+2*i) for i in range(3)]; print('timer words later',t,flush=True)
    open(R+'/tower.bin','wb').write(grab(h,0x327f0,0x1000,'tw'))
finally: h.close()
