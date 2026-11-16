from explore import *
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8]}
game='mw2'
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    segs=[{'start':a} for a in SEG[game]]
    g.load_state(STATES+'mw2_key.clstate'); g._hunk1=lambda: segs[1]['start']
    x=Explorer(g,mmio=False,segs=segs)
    for i in range(4):
        x.run_to(g.now()+2); g.shot(f'shots/k_c{i}.png'); print(g.now(),g.cursor())
    print(x.ev)
