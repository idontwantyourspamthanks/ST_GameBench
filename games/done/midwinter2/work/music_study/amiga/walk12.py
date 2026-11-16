from explore import *
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8]}
game='mw2'
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    segs=[{'start':a} for a in SEG[game]]
    g.load_state(STATES+'mw2_f5b.clstate'); g._hunk1=lambda: segs[1]['start']
    x=Explorer(g,mmio=False,segs=segs)
    g.goto(21,176); x.run_to(g.now()+1.5)
    g.goto(138,178); x.run_to(g.now()+0.5); print(g.cursor())
    g.mouse(left=True); x.run_to(g.now()+1.0); g.mouse(left=False)
    for i in range(4):
        x.run_to(g.now()+2); g.shot(f'shots/w_{i}.png'); print(g.now(),g.cursor())
    print(x.ev)
    g.save_state(STATES+'mw2_wp.clstate')
