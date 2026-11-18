import sys; sys.path.insert(0,'.')
from lib import *
WD=sys.argv[1]
h=NebFloppy(UNZ+'Nebulus_game_disk.st',machine='ste',mem=1024,workdir=WD,trace='fdc'); t=T(h)
print('title',h.boot_to_title(timeout=400,space_at=20),flush=True); time.sleep(3)
rs=struct.unpack('>32H',grab(h,0x77c80,64,'rs')); 
tp=struct.unpack('>L',grab(h,0x77c80+52,4,'a'))[0]; tn=W(h,0x77c80+56); mp=struct.unpack('>L',grab(h,0x77c80+58,4,'b'))[0]
print('rsTosP %x rsTosN %d rsMfpP %x'%(tp,tn,mp))


print('$4ba now',hex(L(h,0x4ba)), 'copy@', hex(L(h,tp+0x4ba-8)))
print('$400..$4c0 TOS copy: hz200', L(h,tp+0x4ba-8))
h.key('F10',hold=0.5); time.sleep(2)
h.cmd('hatari-option --disk-a none'); time.sleep(2)
h.key('F10',hold=0.4); time.sleep(2.5); h.key('F10',hold=0.4); time.sleep(2.5)
t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); t.F(1.0)
for i in range(12):
    time.sleep(3)
    try:
        v=bytes(grab(h,0xfffa01,48,'live')); print(i,'live MFP', bytes(v[j] for j in range(0,48,2)).hex(' '), '$4ba',hex(L(h,0x4ba)),'vDisk',W(h,0x77cc0+174), 'msg', t.msg(),flush=True)
    except Exception as e: print(i,'err',e)
h.close()
