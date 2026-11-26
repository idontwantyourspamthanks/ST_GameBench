"""FLOPPY eject/swap gate. usage: fge.py GAME.st WORKDIR [ste|st|megaste] [fuzzsubset|nofuzz]"""
import sys; sys.path.insert(0,'/tmp/ng12fl/s')
from lib import *
import shutil, re, hashlib, glob
sys.path.insert(0,G+'tools')
import nebcampaign as nc, ovl
GAME=sys.argv[1]; WD=sys.argv[2]; MACH=sys.argv[3] if len(sys.argv)>3 else 'ste'
FUZZ=(sys.argv[4] if len(sys.argv)>4 else 'fuzzsubset')
D='/tmp/ng12fl/nfe/dd/'
MEM={'ste':1024,'st':1024,'megaste':4096}[MACH]
h=NebFloppy(GAME,machine=MACH,mem=MEM,workdir=WD,trace='fdc'); t=T(h)
fails=[]; log=[]
def chk(name,got,exp):
    ok=(got==exp); line=f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line,flush=True); log.append(line)
    if not ok: fails.append(name)
def op(save=False):
    h.key('F10',hold=0.4); time.sleep(2.5); h.key('F10',hold=0.4); time.sleep(2.5)
    t.K('Down',4 if save else 3,hold=0.2,gap=0.4); t.F(1.0); t0=time.time(); t.F(1.0)
    m=None
    for _ in range(80):
        time.sleep(0.5)
        try: busy=struct.unpack('>H',grab(h,0x77cc0+174,2,'vd'))[0]
        except Exception: continue
        if busy==0:
            m=t.msg()
            if m is not None: break
    dt=time.time()-t0
    print('   (%.1f s) %r'%(dt,m),flush=True); return m
def eject(wait=5.0):
    h.cmd('hatari-option --disk-a none'); time.sleep(wait)
def nfdc():
    return len(re.findall(r'^fdc type II', h._logtext(), re.M))
def exp_of(f):
    ok,text,_=nc.status(open(f,'rb').read())
    if not ok: return 'Not a campaign disk'
    m=re.findall(r'(\d+) levels / (\d+)',text)
    return 'Loaded %s levels / %s campaigns'%m[0] if 'valid:' in text else 'Loaded 0 levels / 0 campaigns'
try:
    print('title',h.boot_to_title(timeout=400,space_at=25 if MEM>1024 else 20),flush=True); time.sleep(3)
    rs=lambda off: struct.unpack('>L',grab(h,0x77c80+off,4,'rsx'))[0]
    print('  rsTosP %x rsMfpP %x'%(rs(52),rs(58)),'MFP block',grab(h,rs(58),24,'mb').hex(' '))
    chk('MFP block intact at the title (IERB $64 TCDCR $57)',(grab(h,rs(58),24,'mb')[4],grab(h,rs(58),24,'mb')[14]),(0x64,0x57))
    h.key('F10',hold=0.5); time.sleep(2)
    # S1: swap WITHOUT eject (game disk in the drive, campaign disk inserted over it)
    t.insert(D+'t3.st'); chk('S1 game disk -> t3 swap, no eject',op(),'Loaded 1 levels / 1 campaigns'); chk('  store == file',t.store()==open('/tmp/ng12fl/nfe/t3.ovl','rb').read(),True)
    # S2: reinsert the GAME disk and use Load: the game disk is not a campaign disk
    t.insert(GAME); chk('S2 campaign -> game disk back, Load',op(),'Not a campaign disk')
    chk('  store unchanged by the failed load',t.store()==open('/tmp/ng12fl/nfe/t3.ovl','rb').read(),True)
    # E1/E2: really empty drive
    eject(5.0); chk('E1 eject (none), 5 s, fire',op(),'No disk'); h.shot('/tmp/ng12fl/nfe/shot_nodisk_%s.png'%MACH)
    chk('E2 still empty, fire again',op(),'No disk')
    t.insert(D+'t3.st'); chk('E3 no disk -> insert -> fire',op(),'Loaded 1 levels / 1 campaigns')
    for nm,tail in (('nofile',None),('short',None),('big',None),('blank',None),('t3',None)):
        eject(4.0); t.insert(D+nm+'.st'); chk('E4 eject, 4 s, insert %s, fire'%nm,op(),exp_of(D+nm+'.st'))
        if nm=='blank': chk('  store zero',t.store()==bytes(8192),True)
        if nm=='t3': chk('  store == file',t.store()==open('/tmp/ng12fl/nfe/t3.ovl','rb').read(),True)
    # eject + game disk back (no campaign disk) then campaign
    eject(3.0); t.insert(GAME); chk('E5 eject, game disk back, Load',op(),'Not a campaign disk')
    t.insert(D+'t3.st'); chk('E6 game disk -> t3 swap again',op(),'Loaded 1 levels / 1 campaigns')
    # write protection
    h.cmd('hatari-option --protect-floppy on'); time.sleep(1)
    t.insert(D+'t3.st'); chk('W1 write-protected, load',op(),'Loaded 1 levels / 1 campaigns')
    chk('W2 write-protected, SAVE',op(save=True),'Disk is write protected')
    eject(3.0); t.insert(D+'t3.st'); chk('W3 eject + reinsert protected, SAVE',op(save=True),'Disk is write protected')
    h.cmd('hatari-option --protect-floppy off'); time.sleep(1)
    chk('game alive after the cells',t.alive(),True)
    # save
    shutil.copy(D+'t3.st',D+'save1.st'); s1=open(D+'save1.st','rb').read()
    eject(3.0); t.insert(D+'save1.st'); chk('V1 eject + insert, SAVE',op(save=True),'Saved')
    eject(3.0)                                    # Hatari writes the image back on eject
    img=open(D+'save1.st','rb').read(); ok,text,data=nc.status(img)
    chk('  saved image is a usable campaign disk',ok,True); chk('  its NEBLEVEL.OVL == RAM store',data==t.store(),True)
    chk('  image changed only inside file data/dir entry',[i for i in range(len(img)) if img[i]!=s1[i] and not (nc.DIR0<=i<nc.DIR0+64 or nc.DATA0<=i<nc.DATA0+8192)],[])
    t.insert(D+'save1.st'); chk('V2 reload the saved disk',op(),'Loaded 1 levels / 1 campaigns')
    # fuzz
    if FUZZ!='nofuzz':
        names=['fz_00_random0','fz_05_magic_random','fz_06_flip1','fz_13_version2','fz_20_badentries','fz_21_valid'] if FUZZ=='fuzzsubset' else [f.split('/')[-1][:-3] for f in sorted(glob.glob(D+'fz_*.st'))]
        for name in names:
            f=D+name+'.st'
            if not os.path.exists(f): print('missing',f); continue
            ovf=open(f[:-3]+'.ovl','rb').read(); before=t.store(); exp=exp_of(f)
            eject(3.0); t.insert(f); m=op(); after=t.store(); okk=(after==ovf) if exp.startswith('Loaded') else (after==before)
            chk('fuzz '+name,(m,'store ok' if okk else 'STORE WRONG'),(exp,'store ok'))
    chk('alive after all',t.alive(),True)
    # FDC reads while the game runs after the last disk op: must be 0 (the game never reads the floppy after the title)
    t.K('Up',1,gap=0.5); t.K('Up',1,gap=0.5)
    h.key('F10',hold=0.5); time.sleep(3)
    h.key('Right',hold=0.5); time.sleep(0.5)
    n0=nfdc(); h.key('Control_R',hold=1.0); time.sleep(5)
    t0=grab(h,0x3ad74,6).hex(); x0=W(h,0x33a16); h.key('Right',hold=0.6); time.sleep(0.4); x1=W(h,0x33a16); time.sleep(10); t1=grab(h,0x3ad74,6).hex()
    chk('tower after all disk operations: timer runs',t0!=t1,True); chk('  frog answers the joystick',x0!=x1,True)
    chk('  FDC type II commands during 15 s of play',nfdc()-n0,0); print('  (control: FDC type II commands in the whole log:',nfdc(),')')
finally: pass
print('FAILS',fails); open(f'/tmp/ng12fl/nfe/fge_{MACH}.log','w').write('\n'.join(log)+f'\nFAILS {fails}\n')
h.close()
