"""coverage: count executions of given addresses in stock+live run. python3 cover.py DUMP NPASS LIVE sched addr..."""
import sys, json
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
sys.path.insert(0,'.')
from emu import Emu
from proto import flip
from unicorn import UC_HOOK_CODE
import emgate
dump,npass,live,kind=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4]
addrs=[int(x,16) for x in sys.argv[5:]]
e=Emu(dump); emgate.apply_live(e,live) if live!='none' else None
cnt={a:0 for a in addrs}
def hk(uc,addr,size,ud):
    if addr in cnt: cnt[addr]+=1
for a in addrs: e.uc.hook_add(UC_HOOK_CODE,hk,None,a,a)
for p in range(npass):
    v=emgate.schedule(p,kind)
    if v is not None: e.setb(0x6105,v)
    try:
        e.run(0x7a88,0x7b74); flip(e); e.run(0x7b7a,0x7a88)
    except Exception as ex: print('stop',p,ex); break
print({hex(a):c for a,c in cnt.items()})
