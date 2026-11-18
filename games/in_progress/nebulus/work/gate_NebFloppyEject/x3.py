import sys; sys.path.insert(0,'.')
from lib import *
WD=sys.argv[1]
h=NebFloppy(UNZ+'Nebulus_game_disk.st',machine='ste',mem=1024,workdir=WD,trace='fdc'); t=T(h)
print('title',h.boot_to_title(timeout=400,space_at=20),flush=True); time.sleep(3)
mp=struct.unpack('>L',grab(h,0x77c80+58,4,'b'))[0]
print('blk before', grab(h,mp,24,'mfp').hex(' '))
h.key('F10',hold=0.5); time.sleep(2)
h.cmd('hatari-option --disk-a none'); time.sleep(2)
h.key('F10',hold=0.4); time.sleep(2.5); h.key('F10',hold=0.4); time.sleep(2.5)
t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); t.F(1.0)
time.sleep(6)
print('blk during', grab(h,mp,24,'mfp').hex(' '))
print('RS', grab(h,0x77c80+50,16,'rs').hex(' '))
print('V vMfp(92..116)', grab(h,0x77cc0+92,24,'vm').hex(' '))
for i in range(3):
    v=bytes(grab(h,0xfffa01,48,'live')); print('live', bytes(v[j] for j in range(0,48,2)).hex(' '))
o=h.debug('r',1.0); print(o[-1500:])
h.close()
