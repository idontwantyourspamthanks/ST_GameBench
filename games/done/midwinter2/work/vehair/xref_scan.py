import sys, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/tools')
import m68dis
ram=open('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/dumps/ram_ingame_lobos.bin','rb').read()
# renderer ranges (frameloop.md/p7 notes): $1d000-$20400 view+scene, $37a00-$3d400 poly/edge/span, $1b996 sky, $30f2c HUD overlay
R=[(0x1d000,0x20500),(0x37a62,0x3d500),(0x1b996,0x1ba00),(0x30f2c,0x31100)]
res={}
for a in range(0x6700,0x7700,2):
    hs=m68dis.xrefs(ram,a)
    rd=[h for h in hs if any(lo<=int(h.split(':')[0],16)<hi for lo,hi in R)]
    if rd: res[a]=rd
for a,rd in res.items():
    print('$%x'%a, ' | '.join(rd[:6]))
