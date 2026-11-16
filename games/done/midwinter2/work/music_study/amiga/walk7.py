from explore import *
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8],'mw2orig':[0x24a070,0x27f3b0,0x293d88,0x5cc8]}
game='mw2'
BTN={'warroom':(81,19),'personnel':(236,22),'control':(159,61),'training':(202,56)}
for name,pt in BTN.items():
    with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
        segs=[{'start':a} for a in SEG[game]]
        g.load_state(STATES+f'{game}_hall.clstate'); g._hunk1=lambda: segs[1]['start']
        x=Explorer(g,mmio=True,segs=segs)
        x.run_to(g.now()+1)
        n=len(x.rows)
        hold_click(x,pt,settle=12)
        print(f'=== {name}: t={g.now():.1f}')
        for q in x.ev: print('   ',q)
        print('   music rows',len(x.rows)-n)
        g.shot(f'shots/h_{name}.png')
