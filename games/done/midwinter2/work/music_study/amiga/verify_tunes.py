"""Start tune N in the emulator (calling the game's own $4cbba with d0=N from a parked stub), log the Paula writes of
the music code for NTICKS VBLs and compare with sim.py tick by tick.  usage: verify_tunes.py NTICKS tune..."""
import sys, json, collections
from explore import *
sys.path.insert(0,'.')
from sim import Music
NT=int(sys.argv[1]); tunes=[int(a) for a in sys.argv[2:]] or list(range(1,18))
game='mw2orig'
names={0xdff096:'DMACON'}
for c in range(4):
    b=0xdff0a0+16*c; names[b]=f'LC{c}'; names[b+4]=f'LEN{c}'; names[b+6]=f'PER{c}'; names[b+8]=f'VOL{c}'
results={}
for tune in tunes:
    with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
        g.load_state(STATES+'orig_hall.clstate')
        x=Explorer(g)
        segs=x.segs; base0=segs[0]['start']
        rt=x.rt
        stub=segs[2]['start']+0x100
        call=rt(0x4cbba)
        g.write(stub, bytes.fromhex('4eb9')+call.to_bytes(4,'big')+bytes.fromhex('60fe'))
        x.run_to(g.now()+1)
        g.write_w(rt(0x60a8e),0xffff)
        g.call('regs.set',reg='d0',value=tune); g.call('regs.set',reg='pc',value=stub)
        n0=len(x.rows)
        x.run_to(g.now()+NT/49.92+0.3)
        LO=base0+0x30440; HI=base0+0x31240
        real=[r for r in x.rows[n0:] if LO<=r[4]<HI and r[5] in names]
        byf=collections.OrderedDict()
        for r in real: byf.setdefault(r[0],[]).append((names[r[5]],r[7]))
        frames=list(byf)
        # real start: the reset frame contains LC writes of 0 for the 4 channels
        f0=[f for f in frames if byf[f][:1]==[('LC0',0)]][0]
        m=Music(); m.start(tune)
        delta=None
        # hunk 3 base: runtime = operand - 0x89478 + segs[3]
        h3=segs[3]['start']; c0=base0-0x270d0
        def lcmap(v): return v+c0 if v<0x89478 else v-0x89478+h3
        bad=0; first=None
        for i in range(1,NT):
            m.out=[]; m.tick()
            sim=[(k,lcmap(v) if k.startswith('LC') and v!=0 else v) for k,v in m.out]
            rl=byf.get(f0+i,[])
            if sim!=rl:
                bad+=1
                if first is None: first=(i,sim,rl)
        results[tune]=(NT-1,bad,first)
        print(f'tune {tune:2d}: ticks compared {NT-1} mismatching {bad}', ('' if not first else f'first at tick {first[0]}\n  sim {first[1]}\n  real {first[2]}'), flush=True)
