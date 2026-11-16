from explore import *
game='mw2orig'
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    g.load_state(STATES+'orig_hall.clstate')
    x=Explorer(g)
    n=0
    def show(name):
        global n
        e=x.ev[n:]; n=len(x.ev)
        print(f'--- {name} t={g.now():.2f} cursor={g.cursor()} musicrows={len(x.rows)}')
        for q in e[:30]: print('   ',q)
        g.shot(f'shots/x_{name}.png')
    x.run_to(g.now()+2); show('hall0')
    hold_click(x,HALL_RAIDS,settle=10); show('raids')
    hold_click(x,LEVELS['intermediate'],settle=10); show('map')
    hold_click(x,CAMARGO,settle=6); show('island')
    key(x,0x40,hold=0.5,settle=14); show('briefing')
    hold_click(x,BRIEFING_QUESTION,settle=6); show('equip')
    g.save_state(STATES+'orig_equip.clstate')
    hold_click(x,THUMBS_UP,settle=12); show('start')
    x.run_to(g.now()+30); show('cockpit')
    g.save_state(STATES+'orig_cockpit.clstate')
    json.dump(x.rows,open('walk5_rows.json','w')); json.dump(x.ev,open('walk5_ev.json','w'))
