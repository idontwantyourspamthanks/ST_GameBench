from explore import *
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8],'mw2orig':[0x24a070,0x27f3b0,0x293d88,0x5cc8]}
game=sys.argv[1] if len(sys.argv)>1 else 'mw2'
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    segs=[{'start':a} for a in SEG[game]]
    g.run_to(7.5)
    x=Explorer(g,mmio=False,segs=segs)
    n=0
    def show(name):
        global n
        e=x.ev[n:]; n=len(x.ev)
        print(f'--- {name} t={g.now():.2f} f{g.frame()} cursor={g.cursor()}')
        for q in e[:40]: print('   ',q)
        g.shot(f'shots/m_{name}.png')
    x.run_to(75); show('t75')
    x.run_to(g.now()+10); show('t85')
    g.key(0x37, hold_ms=400); x.run_to(g.now()+8); show('afterM')
    g.save_state(STATES+f'{game}_hall.clstate')
    hold_click(x,HALL_RAIDS,settle=10); show('raids')
    hold_click(x,LEVELS['intermediate'],settle=10); show('map')
    hold_click(x,CAMARGO,settle=6); show('island')
    key(x,0x40,hold=0.5,settle=14); show('briefing')
    hold_click(x,BRIEFING_QUESTION,settle=6); show('equip')
    g.save_state(STATES+f'{game}_equip.clstate')
    hold_click(x,THUMBS_UP,settle=12); show('start')
    x.run_to(g.now()+30); show('cockpit')
    g.save_state(STATES+f'{game}_cockpit.clstate')
    json.dump(x.ev,open(f'walk6_{game}_ev.json','w'))
