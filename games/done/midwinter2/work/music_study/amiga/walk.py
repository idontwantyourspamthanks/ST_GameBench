import sys
from trace import *
from mw2cl import MW2
IMG='/home/ryan/Code/Amiga/gamebench/dist/Amiga_enhanced_games_2026-11-15.hdf'
KEEP=STATES+'scratch.hdf'
V={}   # operand -> runtime resolver
def mk_rt(s):
    segs=s.call("segments.list")["current"]
    sizes=[217912,84432,100000,138204]
    flat0=[0]
    for z in sizes[:-1]: flat0.append(flat0[-1]+z)
    def rt(op):
        f=op-0x270d0
        for i in range(3,-1,-1):
            if f>=flat0[i]: return segs[i]['start']+(f-flat0[i])
    return rt,segs
with MW2.from_image(IMG, game="mw2", keep=KEEP) as g:
    t=Tracer(g)
    log=[]
    def mark(name):
        rt,segs=mk_rt(g) if g.call("segments.list")["current"] else (None,None)
        v=None
        if rt:
            v=(g.read_w(rt(0x60a8e)), g.read_l(rt(0x5e296)), g.read_w(rt(0x57344)), g.read_w(rt(0x60aa2)))
        print(f'{g.now():8.2f} f{g.frame()} {name} tune/tick/pause/on={v} rows={len(t.rows)}', flush=True)
        g.shot(f'shots/w_{name}.png')
    t.run_to(40); 
    for T in (60,90):
        t.run_to(T); mark(f'boot{T}')
    cnt=0
    while cnt<8:
        t.run_to(g.now()+20); mark(f'w{int(g.now())}'); cnt+=1
        try:
            g.wait_region((300,100,120,60),"9cb6dabffa4f3c25",timeout=1)
            break
        except Exception: pass
    t.dump('walk_a.jsonl')
