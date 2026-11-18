"""Stage 3 gate: campaign disk Load/Save (drive A:, image inserted into Hatari), every failure mode, 22 fuzz disks, save integrity, game keeps running.
FLOPPY build: game disk .st booted in drive A (--disk-a, real FDC), campaign disks swapped in with hatari-option --disk-a.
usage: f161.py GAME.st WORKDIR [ste|st|megaste] [skipfuzz]"""
import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy')
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from e160_lib import *
from nebfloppy import NebFloppy
import hashlib, ovl
sys.path.insert(0,G+'tools')
import nebcampaign as nc
GAMEDIR=sys.argv[1]; WD=sys.argv[2]; MACH=sys.argv[3] if len(sys.argv)>3 else 'ste'
FUZZ=not (len(sys.argv)>4 and sys.argv[4]=='skipfuzz')
D='/tmp/ne/d/'
MEM={'ste':1024,'st':1024,'megaste':4096}[MACH]
h=NebFloppy(GAMEDIR,machine=MACH,mem=MEM,workdir=WD,trace='fdc'); t=T(h)
fails=[]; log=[]
def chk(name,got,exp):
    ok=(got==exp); line=f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line,flush=True); log.append(line)
    if not ok: fails.append(name)
def op(save=False,name=''):
    """manager at the top (F10 out, F10 in), Down to Load/Save, FIRE, FIRE at the prompt, then wait for the excursion to end:
    vDisk back to 0 AND a message set (4-8 s with a disk, ~10 s on an empty drive)."""
    h.key('F10',hold=0.4); time.sleep(2.5); h.key('F10',hold=0.4); time.sleep(2.5)
    t.K('Down',4 if save else 3,hold=0.2,gap=0.4); t.F(1.0); t0=time.time(); t.F(1.0)
    m=None
    for _ in range(60):
        time.sleep(0.5)
        try:                                     # the debugger is busy while the screen is frozen: a read can fail, just retry
            busy=struct.unpack('>H',grab(h,0x77cc0+174,2,'vd'))[0]
        except Exception:
            continue
        if busy==0:
            m=t.msg()
            if m is not None: break
    print('   (%.1f s) %r'%(time.time()-t0,m),flush=True)
    return m
try:
    print('title',h.boot_to_title(timeout=400,space_at=25 if MEM>1024 else 20),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    h.cmd('hatari-option --disk-a /dev/null'); time.sleep(2)   # the game disk out of drive A: (the boot disk was in it)
    chk('empty drive (game disk ejected)',op(),'No disk')
    h.shot('/tmp/nr3/shots/f161_nodisk.png')
    t.insert(D+'nofile.st'); chk('disk without NEBLEVEL.OVL',op(),'Not a campaign disk')
    t.insert(D+'short.st'); chk('NEBLEVEL.OVL 4096 B',op(),'Not a campaign disk')
    t.insert(D+'big.st'); chk('8192 B text file',op(),'Not a campaign disk'); h.shot('/tmp/nr3/shots/f161_notcamp.png')
    s0=t.store()
    t.insert(D+'blank.st'); chk('blank campaign disk (all zero file)',op(),'Loaded 0 levels / 0 campaigns')
    chk('  store is zero (blank loaded)',t.store()==bytes(8192),True)
    t.insert(D+'t3.st'); chk('valid campaign disk',op(),'Loaded 1 levels / 1 campaigns'); h.shot('/tmp/nr3/shots/f161_loaded.png')
    t3=open('/tmp/t3.ovl','rb').read(); chk('  store == file',t.store()==t3,True)
    # write protection: read ok, save refused, image untouched
    h.cmd('hatari-option --protect-floppy on'); time.sleep(1)
    t.insert(D+'t3.st'); chk('write-protected disk, load',op(),'Loaded 1 levels / 1 campaigns')
    chk('write-protected disk, SAVE',op(save=True),'Disk is write protected'); h.shot('/tmp/nr3/shots/f161_wp.png')
    h.cmd('hatari-option --protect-floppy off'); time.sleep(1)
    chk('game still alive after the disk operations',t.alive(),True)
    if FUZZ:
        import glob, ovl
        for f in sorted(glob.glob(D+'fz_*.st')):
            name=f.split('/')[-1][:-3]; ovf=open(f[:-3]+'.ovl','rb').read()
            ok,text,_=nc.status(open(f,'rb').read())
            before=t.store()
            t.insert(f); m=op()
            exp='Not a campaign disk' if not ok else 'Loaded %d levels / %d campaigns'%tuple(map(int,[__import__('re').findall(r'(\d+) levels / (\d+)',text)[0][0],__import__('re').findall(r'(\d+) levels / (\d+)',text)[0][1]])) if 'valid:' in text else 'Loaded 0 levels / 0 campaigns'
            after=t.store()
            good=(m==exp) and ((after==ovf) if ok else (after==before))
            chk(f'fuzz {name}',(m,'store ok' if good else 'STORE WRONG'),(exp,'store ok'))
        chk('alive after the fuzz set',t.alive(),True)
    # ---- save: edit a level in the editor, save from the editor menu and from the manager, compare the image
    import shutil
    shutil.copy(D+'t3.st','/tmp/ne/d/save1.st'); t.insert('/tmp/ne/d/save1.st'); op()          # load t3 (store = t3)
    t.K('Down',2,hold=0.2,gap=0.4); t.F(1.0)       # Levels >
    t.K('Down',1)                                   # list: level 0 'MY LEVEL', <new level>, < back  -> select <new level>
    t.F(1.5)                                        # new level -> editor
    t.K('Up',3); t.K('p'); t.K('Right',2); t.K('l')   # a pillar and a ledge
    t.F(); t.K('Down',10); h.shot('/tmp/nr3/shots/f161_editor_save_item.png'); t.F(1.0); h.shot('/tmp/nr3/shots/f161_prompt_in_editor.png')
    t.F(3.5); time.sleep(1.5); chk('Save from the editor root menu',t.msg(),'Saved'); h.shot('/tmp/nr3/shots/f161_saved.png')
    ram=t.store(); lv=ovl.parse(ram)
    chk('  RAM store has 2 levels now',len(lv[0]),2)
    h.key('F10',hold=0.5); time.sleep(2)             # leave editor -> level list
    t.insert(D+'blank.st'); time.sleep(2)           # inserting another image makes Hatari write the saved one back
    img=open('/tmp/ne/d/save1.st','rb').read() if False else None
    # Hatari writes the image back on eject: read it now
    img=open('/tmp/ne/d/save1.st','rb').read()
    ok,text,data=nc.status(img)
    chk('image after save: usable campaign disk',ok,True); print('  ',text)
    chk('image NEBLEVEL.OVL == RAM store',data==ram,True)
    ref=nc.build(open('/tmp/t3.ovl','rb').read())
    # only the file's clusters + the directory entry (time stamp/size) may differ: FATs, boot sector and everything outside the data must be identical
    diff=[i for i in range(len(img)) if img[i]!=ref[i]]
    outside=[i for i in diff if not (nc.DATA0<=i<nc.DATA0+8192)]
    print('  bytes differing from the original image outside the file data:',[hex(i) for i in outside][:12])
    chk('  boot sector + FATs untouched',[i for i in outside if i<nc.DIR0],[])
    chk('  directory differs only in the entry (date/time)',[i for i in outside if nc.DIR0<=i<nc.DATA0 and not (nc.DIR0+32<=i<nc.DIR0+64)],[])
    # back in the manager: Left = "< back" from the level list
    t.K('Left',1,gap=1.0)
    # saves that must be refused: disk without the file, write-protected disk; the images stay byte-identical
    t.insert(D+'nofile.st'); nf0=open(D+'nofile.st','rb').read()
    chk('Save to a disk without NEBLEVEL.OVL',op(save=True),'Not a campaign disk')
    t.insert(D+'blank.st'); time.sleep(2); chk('  that image is unchanged',open(D+'nofile.st','rb').read()==nf0,True)
    shutil.copy(D+'t3.st','/tmp/ne/d/save2.st'); s2=open('/tmp/ne/d/save2.st','rb').read()
    h.cmd('hatari-option --protect-floppy on'); time.sleep(1)
    t.insert('/tmp/ne/d/save2.st'); chk('Save to a write-protected campaign disk',op(save=True),'Disk is write protected')
    t.insert(D+'blank.st'); time.sleep(2); chk('  that image is unchanged',open('/tmp/ne/d/save2.st','rb').read()==s2,True)
    h.cmd('hatari-option --protect-floppy off'); time.sleep(1)
    # reload what was saved, from the saved disk image (a fresh Load replaces the store)
    t.insert('/tmp/ne/d/save1.st'); chk('Load the disk saved above',op(),'Loaded 2 levels / 1 campaigns'); chk('  store == saved file',t.store()==data,True)
    # the game must still run and take keys after all of that: Original game
    t.K('Up',1,gap=0.5); t.K('Up',1,gap=0.5)
    # F10 in the manager = quit to the title, then a normal game from the title: fire starts, the frog must answer
    h.key('F10',hold=0.5); time.sleep(3)
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(5)
    t0=grab(h,0x3ad74,6).hex(); x0=W(h,0x33a16); h.key('Right',hold=0.6); time.sleep(0.4); x1=W(h,0x33a16); time.sleep(2); t1=grab(h,0x3ad74,6).hex()
    chk('tower after all disk operations: timer runs',t0!=t1,True); chk('  frog answers the joystick (x changed)',x0!=x1,True)
finally: pass
print('FAILS',fails); open(f'/tmp/f161_{MACH}.log','w').write('\n'.join(log)+f'\nFAILS {fails}\n')
h.close()
