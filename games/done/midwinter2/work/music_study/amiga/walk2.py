import sys
from trace import *
from mw2cl import MW2
IMG='/home/ryan/Code/Amiga/gamebench/dist/Amiga_enhanced_games_2026-11-15.hdf'
game=sys.argv[1]
with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
    t=Tracer(g)
    def mark(name):
        v=None
        if g.call("segments.list")["current"]:
            segs=g.call("segments.list")["current"]
            rt=lambda op: segs[3]['start']+0 if False else None
            sizes=[217912,84432,100000,138204]; fl=[0,217912,302344,402344]
            def rt(op):
                f=op-0x270d0
                for i in (3,2,1,0):
                    if f>=fl[i]: return segs[i]['start']+f-fl[i]
            v=(g.read_w(rt(0x60a8e)), hex(g.read_l(rt(0x5e296))), g.read_w(rt(0x57344)), g.read_w(rt(0x60aa2)))
        print(f'{g.now():8.2f} f{g.frame()} {name} tune/tick/pause/on={v} rows={len(t.rows)}', flush=True)
        g.shot(f'shots/{game}_{name}.png')
    for T in (60,100,125,140):
        t.run_to(T); mark(f't{T}')
    g.key(0x37, hold_ms=300)   # 'M'
    for i in range(3):
        t.run_to(g.now()+4); mark(f'afterM{i}')
    t.dump(f'walk2_{game}.jsonl')
