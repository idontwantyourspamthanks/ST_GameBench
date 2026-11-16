from explore import *
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8]}
game='mw2'
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    segs=[{'start':a} for a in SEG[game]]
    g.load_state(STATES+'mw2_wp.clstate'); g._hunk1=lambda: segs[1]['start']
    x=Explorer(g,mmio=False,segs=segs)
    n=0
    def show(name):
        global n
        e=x.ev[n:]; n=len(x.ev); print(f'--- {name} t={g.now():.2f} cur={g.cursor()}'); [print('   ',q) for q in e]
        g.shot(f'shots/y_{name}.png')
    g.goto(200,100); x.run_to(g.now()+1)
    g.key(0x40,hold_ms=500); x.run_to(g.now()+3); show('space')
    g.goto(21,176); x.run_to(g.now()+1.5); show('hoverkey'); 
    g.goto(21,178); x.run_to(g.now()+0.5)
    g.mouse(left=True); x.run_to(g.now()+1.0); g.mouse(left=False); x.run_to(g.now()+4); show('clickfarleft')
    for i in range(4):
        x.run_to(g.now()+5); show(f'acc{i}')
    g.save_state(STATES+'mw2_acc.clstate')
