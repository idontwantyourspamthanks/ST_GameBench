"""Two distinct campaign disks A (1 level/1 camp) and B (3/2): the user sequences. usage: fge2.py GAME.st WORKDIR [ste|st|megaste]"""
import sys; sys.path.insert(0,'/tmp/ng12fl/s')
from lib import *
import shutil, re
sys.path.insert(0,G+'tools')
import nebcampaign as nc
GAME=sys.argv[1]; WD=sys.argv[2]; MACH=sys.argv[3] if len(sys.argv)>3 else 'ste'
D='/tmp/ng12fl/nfe/dd/'; MEM={'ste':1024,'st':1024,'megaste':4096}[MACH]
A=open('/tmp/ng12fl/nfe/A.ovl','rb').read(); B=open('/tmp/ng12fl/nfe/B.ovl','rb').read()
for n in ('A2','B2'): shutil.copy(D+('campone.st' if n[0]=='A' else 'campthree.st'),D+('campone_2.st' if n[0]=='A' else 'campthree_2.st'))
h=NebFloppy(GAME,machine=MACH,mem=MEM,workdir=WD,trace='fdc'); t=T(h)
fails=[]
def chk(name,got,exp):
    ok=(got==exp); print(f"{'PASS' if ok else 'FAIL'} {name}: {got!r}"+('' if ok else f"  (expected {exp!r})"),flush=True)
    if not ok: fails.append(name)
def op(save=False):
    h.key('F10',hold=0.4); time.sleep(2.5); h.key('F10',hold=0.4); time.sleep(2.5)
    t.K('Down',4 if save else 3,hold=0.2,gap=0.4); t.F(1.0); t0=time.time(); t.F(1.0); m=None
    for _ in range(80):
        time.sleep(0.5)
        try:
            if struct.unpack('>H',grab(h,0x77cc0+174,2,'vd'))[0]==0:
                m=t.msg()
                if m is not None: break
        except Exception: continue
    print('   (%.1f s) %r'%(time.time()-t0,m),flush=True); return m
def eject(w=5.0): h.cmd('hatari-option --disk-a none'); time.sleep(w)
def img(n): return nc.status(open(D+n+'.st','rb').read())
try:
    print('title',h.boot_to_title(timeout=400,space_at=25 if MEM>1024 else 20),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    eject(5); t.insert(D+'campone.st'); chk('U1 game disk out, campaign A in, Load',op(),'Loaded 1 levels / 1 campaigns'); chk('  store == A',t.store()==A,True)
    eject(5); t.insert(D+'campthree.st'); chk('U2 A out, B in, Load',op(),'Loaded 3 levels / 2 campaigns'); chk('  store == B (not A)',t.store()==B,True)
    chk('U3 Save (store B) onto B',op(save=True),'Saved'); eject(3)
    ok,text,data=img('campthree'); chk('  image B NEBLEVEL.OVL == RAM store',(ok,data==t.store()),(True,True))
    ref=nc.build(B); cur=open(D+'campthree.st','rb').read()
    chk('  image B differs from the original only in the file data/dir entry',[i for i in range(len(cur)) if cur[i]!=ref[i] and not (nc.DIR0<=i<nc.DIR0+64 or nc.DATA0<=i<nc.DATA0+8192)],[])
    # store = A, then Save onto a DIFFERENT disk (B2): B2's file must become A's content
    eject(4); t.insert(D+'campone_2.st'); chk('U4 insert A2, Load',op(),'Loaded 1 levels / 1 campaigns'); chk('  store == A',t.store()==A,True)
    eject(4); t.insert(D+'campthree_2.st'); chk('U5 insert B2 (3 levels), Save (store = A content)',op(save=True),'Saved'); eject(3)
    ok,text,data=img('campthree_2'); chk('  image B2 NEBLEVEL.OVL == store (A content, B2 old content gone)',(ok,data==A),(True,True))
    t.insert(D+'campthree_2.st'); chk('U6 reload B2',op(),'Loaded 1 levels / 1 campaigns')
    # no disk -> fire -> 'No disk' -> insert -> fire
    eject(5); chk('U7 empty drive, fire',op(),'No disk'); t.insert(D+'campthree.st'); chk('U8 insert B, fire again',op(),'Loaded 3 levels / 2 campaigns'); chk('  store == B',t.store()==B,True)
    eject(5); chk('U9 empty again, fire',op(),'No disk'); t.insert(D+'campone.st'); chk('U10 insert A, fire',op(),'Loaded 1 levels / 1 campaigns'); chk('  store == A',t.store()==A,True)
    # game disk back: not a campaign disk; then campaign
    eject(3); t.insert(GAME); chk('U11 game disk back, Load',op(),'Not a campaign disk'); t.insert(D+'campthree.st'); chk('U12 B in over game disk (no eject)',op(),'Loaded 3 levels / 2 campaigns')
    chk('alive',t.alive(),True)
finally: pass
print('FAILS',fails); h.close()
