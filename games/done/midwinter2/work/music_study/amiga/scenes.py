from explore import *
import sys
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8]}
game='mw2'
entries=[(int(a,16)) for a in sys.argv[1:]]
for ent in entries:
    with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
        segs=[{'start':a} for a in SEG[game]]
        g.load_state(STATES+f'{game}_hall.clstate'); g._hunk1=lambda: segs[1]['start']
        x=Explorer(g,mmio=False,segs=segs)
        x.run_to(g.now()+1)
        pc=x.rt(ent)
        g.call('regs.set',reg='pc',value=pc)
        for i in range(3):
            x.run_to(g.now()+6); g.shot(f'shots/sc_{ent:x}_{i}.png')
        print(f'=== entry {ent:x}: t={g.now():.1f} pc={g.regs()["pc"]:x}')
        for q in x.ev: print('   ',q)
