import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
from unicorn import *
from unicorn.m68k_const import *
live=sys.argv[1]; CRE=int(sys.argv[2],16)
print("live", live)
for d,kind in ((14,'zig'),(11,'zig'),(12,'zig'),(5,'zig'),(14,'upleft'),(12,'up')):
    e=Emu('work/int/mx/dumps/L%d.bin'%d); apply_live_p(e,live); e.setb(0xBF000,1)
    cnt={'entry':0,'hit':0,'gen':0,'flush':0}
    def hk(uc,addr,size,ud):
        cnt[{0xBF500:'entry',0xBF5E6:'hit',CRE:'gen',0xBF678:'flush'}[addr]]+=1
    for a in (0xBF500,0xBF5E6,CRE,0xBF678): e.uc.hook_add(UC_HOOK_CODE,hk,begin=a,end=a)
    for p in range(600):
        v=schedule(p,kind)
        if v is not None: e.setb(0x6105,v)
        e.run(0x7a88,0x7b74); flip(e); e.run(0x7b7a,0x7a88)
    ent=cnt['entry']; hit=cnt['hit']; gen=cnt['gen']; stock=ent-hit
    # model: compiled ~9k avg, stock ~28k avg per draw (car 35k/layer 22k), generation ~80k
    est=(hit*9000+stock*28000+gen*80000)/600
    base=ent*28000/600
    print(f"L{d} {kind:7s} stub entries {ent} compiled {hit} ({100*hit/max(ent,1):.1f} %) generations {gen} flushes {cnt['flush']}  est. car+layer cycles/pass {est:.0f} (stock {base:.0f})")
