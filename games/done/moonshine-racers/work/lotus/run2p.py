import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/lotus')
from lstages import run
L='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/lotus/'
seq=[0x76378,0x76576,0x7657a,0x7657e,0x7658a,0x7658e,0x7659a,0x7659e,0x765a2,0x765a6,0x765ba,0x765be,0x765c2,0x765d6,0x765da,0x765ee,0x765f2,0x765f6,0x765fa]
run(L+'race2p.sav','drive2p',frames=30,seq=seq,poke=[(0x7056a,1)],settle=80)
