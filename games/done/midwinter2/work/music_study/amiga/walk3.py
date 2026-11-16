import sys
from trace import *
from mw2cl import MW2
IMG='/home/ryan/Code/Amiga/gamebench/dist/Amiga_enhanced_games_2026-11-15.hdf'
game='mw2orig'
sizes=[217912,84432,100000,138204]; FL=[0,217912,302344,402344]
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    t=Tracer(g)
    nprev=[0]
    def rt(op):
        segs=g.call("segments.list")["current"]
        f=op-0x270d0
        for i in (3,2,1,0):
            if f>=FL[i]: return segs[i]['start']+f-FL[i]
    def mark(name,shot=True):
        v=None
        try:
            v=(g.read_w(rt(0x60a8e)), hex(g.read_l(rt(0x5e296))), g.read_w(rt(0x57344)), g.read_w(rt(0x60aa2)), g.read_w(rt(0x27632)), g.read_w(rt(0x5d3a8)))
        except Exception as e: v=str(e)[:40]
        new=t.rows[nprev[0]:]; nprev[0]=len(t.rows)
        resets=[(r[3]) for r in new if r[5]==0xdff096 and r[7]==15]
        nrows=len([r for r in new if 0xdff0a0<=r[5]<0xdff0e0])
        print(f'{g.now():8.2f} f{g.frame()} {name:14s} tune,tick,pause,on,scr,5d3a8={v} newrows={nrows} resets@{resets}', flush=True)
        if shot: g.shot(f'shots/o_{name}.png')
    t.run_to(40)
    g.wait_region(mw2cl_hall:=(300,100,120,60),"9cb6dabffa4f3c25",timeout=1) if False else None
    # wait for hall
    T=40
    while True:
        T+=5; t.run_to(T)
        try:
            if g.region_digest(*(300,100,120,60))=="9cb6dabffa4f3c25": break
        except Exception: pass
        if T>140: break
    mark('hall')
    g.save_state(STATES+'orig_hall.clstate')
    t.run_to(g.now()+5); mark('hall+5')
    # RAIDS
    from mw2cl import HALL_RAIDS, LEVELS, CAMARGO, BRIEFING_QUESTION, THUMBS_UP
    def step(name, fn):
        fn(); mark(name)
    def hc(pt,settle):
        pos=g.goto(*pt); g.click(hold=1.0)
        t.run_to(g.now()+settle)
    step('raids', lambda: hc(HALL_RAIDS,10))
    step('level', lambda: hc(LEVELS['intermediate'],10))
    step('island', lambda: hc(CAMARGO,6))
    def space():
        g.key(0x40, hold_ms=500); t.run_to(g.now()+14)
    step('briefing', space)
    step('equip', lambda: hc(BRIEFING_QUESTION,6))
    step('start', lambda: hc(THUMBS_UP,12))
    t.run_to(g.now()+30); mark('cockpit')
    g.save_state(STATES+'orig_cockpit.clstate')
    t.dump('walk3.jsonl')
