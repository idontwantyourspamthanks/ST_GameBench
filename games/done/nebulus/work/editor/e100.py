from ui import *
import sys, ovl
from stharness import TOS
gd=__import__('pathlib').Path
which=sys.argv[1]; machine=sys.argv[2]
kw=dict(machine='megaste',tos=TOS['2.06'],memsize_kb=4096) if machine=='megaste' else {}
os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_final --only nt_trainers ed_overlay --ovl /tmp/test3.ovl >/dev/null")
h=start(f'/tmp/ned100_{which}_{machine}',gd(E+'build_final'),**kw)
def S(tag):
    w=rs(h); print(f"{tag:14s} rsCamp {w[0]} rsPos {w[1]} rsLvl {w[2]:#x} rsEd {w[3]} rsTest {w[4]} | tower {W(h,0x3390c)} pl {W(h,0x33a20)} timer {grab(h,0x3ad98,6).hex()}",flush=True)
def force(): poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
def ready(cond,limit=90):
    t0=time.time()
    while time.time()-t0<limit:
        time.sleep(1.0)
        if cond(): return True
    return False
try:
    h.key('F10',hold=0.5); time.sleep(2)
    if which=='campaign':
        select(h,'Campaigns'); select_i(h,0); select(h,'Play',0.5)
        time.sleep(7); K(h,'e',hold=0.3,gap=0.5); S('lvl1')
        for pos in (1,2):
            force(); ok=ready(lambda: rs(h)[1]==pos and W(h,0x33a20)==0 and W(h,0x33938)==1); S(f'entry {pos+1} {ok}')
            g=grab(h,0x327f0,0x1000)
            print('   cells (3,1) (4,1) (3,2) (4,2):',[hex(g[c*256+r]) for c,r in [(3,1),(4,1),(3,2),(4,2)]])
        force(); ok=ready(lambda: W(h,0x3390c)==8); S(f'victory {ok}'); h.shot(E+f'e100_{machine}_victory.png')
    else:
        select(h,'Levels'); select_i(h,0); select(h,'Edit',1.5); fire(h); select(h,'Playtest',1.0)
        ok=ready(lambda: W(h,0x33a20)==0 and W(h,0x33938)==1); S(f'playing {ok}'); K(h,'e',hold=0.3,gap=0.5)
        force(); ok=ready(lambda: rs(h)[4]==0 and rs(h)[3]==1,60); time.sleep(3); S(f'back in editor {ok}'); h.shot(E+f'e100_{machine}_playtest_back.png')
        g=grab(h,0x327f0,0x1000); print('   grid intact (3,1) (4,1) (3,2) (4,2):',[hex(g[c*256+r]) for c,r in [(3,1),(4,1),(3,2),(4,2)]])
finally: h.close()
