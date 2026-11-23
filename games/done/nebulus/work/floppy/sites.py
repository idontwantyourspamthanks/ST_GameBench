import sys; sys.path.insert(0,'.')
from sitecmp import *
n,flr,bad=compare()
ppr=reloc(pp,ppo)
sites=[(0x377a2,6,'ed decode hook'),(0x37a90,6,'ed spawn dir'),(0x3792c,6,'nt spawn head'),(0x3adb4,6,'ed init time'),(0x3b0a4,6,'nt timer tick'),
(0x38514,6,'ni_latch ACIA store'),(0x3855a,6,'ni_latch fire flag'),(0x39ffa,2,'ni_jump'),(0x3a332,2,'ni_shoot'),(0x3d110,6,'ed tower name'),(0x3d698,8,'cr_credit'),
(0x3d6c4,10,'ed title poll'),(0x3dcf4,6,'nt key poll (jsr 3853a)'),(0x3dfd6,6,'ed frame flip'),(0x3e352,6,'ed tower complete')]
print('site(PP)   floppy   PP orig bytes       floppy bytes (normalised compare)')
for a,l,name in sites:
    p=a-BASE; f=mp(p)
    pb=n[p:p+l].hex(); fb=flr[f:f+l].hex()
    print('%x %x'%(a,f+BASE), pb, fb, 'SAME' if pb==fb else 'DIFF', name)
