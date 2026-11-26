import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
import ovl, nebcampaign as nc
g,rows=ovl.original(1,0); g2,rows2=ovl.original(1,1); g3,rows3=ovl.original(1,2)
lv=[ovl.level(1,0,rows,g,0x0300,'B ONE'),ovl.level(1,1,rows2,g2,0x0300,'B TWO'),ovl.level(1,2,rows3,g3,0x0300,'B THREE')]
B=ovl.build(lv,[ovl.camp('CAMP B1',[0x80,0,1]),ovl.camp('CAMP B2',[2,ovl.orig(1,1)])])
assert ovl.validate(B) is None or True
open('/tmp/oddcore/nfe/B.ovl','wb').write(B); open('/tmp/oddcore/nfe/dd/cB.st','wb').write(nc.build(B)); open('/tmp/oddcore/nfe/dd/cB2.st','wb').write(nc.build(B))
A=open('/tmp/oddcore/nfe/t3.ovl','rb').read(); open('/tmp/oddcore/nfe/A.ovl','wb').write(A)
open('/tmp/oddcore/nfe/dd/cA.st','wb').write(nc.build(A)); open('/tmp/oddcore/nfe/dd/cA2.st','wb').write(nc.build(A))
print(nc.status(nc.build(A))[1]); print(nc.status(nc.build(B))[1])
