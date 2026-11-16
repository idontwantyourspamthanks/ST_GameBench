import sys, json
from trace import *
from mw2cl import MW2, HALL_RAIDS, LEVELS, CAMARGO, BRIEFING_QUESTION, THUMBS_UP
IMG='/home/ryan/Code/Amiga/gamebench/dist/Amiga_enhanced_games_2026-11-15.hdf'
game='mw2orig'
FL=[0,217912,302344,402344]
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    g.load_state(STATES+'orig_hall.clstate')
    segs=g.call("segments.list")["current"]; print([hex(s['start']) for s in segs])
    def rt(op):
        f=op-0x270d0
        for i in (3,2,1,0):
            if f>=FL[i]: return segs[i]['start']+f-FL[i]
    ids=[g.watch(rt(0x60a8e),'write'), g.watch(rt(0x57340),'write',len=4) if False else g.watch(rt(0x57340),'write'), g.watch(rt(0x57344),'write'), g.watch(rt(0x5e296),'write')]
    print(ids)
    r=g.run_to(g.now()+5)
    print(json.dumps(r)[:600])
