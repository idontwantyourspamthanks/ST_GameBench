from ed import *
import sys
sys.path.insert(0,E)
import ovl
gd=__import__('pathlib').Path
RS=0x77c80
h=Nebulus(workdir='/tmp/ned33',game=gd(E+'build_ed'))
def K(k,n=1,hold=0.2,gap=0.35):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def st(tag):
    w=rs()
    print(f"{tag:12s} t={time.time()-T0:5.1f} rsCamp {w[0]} rsPos {w[1]} rsLvl {w[2]} | tower {W(h,0x3390c)} mission {W(h,0x33910)} pl {W(h,0x33a20)} timer {grab(h,0x3ad98,6).hex()} noen {W(h,0x76c04):#x}",flush=True)
def force():
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
def grid_eq(m,t):
    g=grab(h,0x327f0,0x1000); og,rows=ovl.original(m,t)
    return [(a,r) for a in range(16) for r in range(rows) if g[a*256+r]!=og[a][r]]
def wait_level(pos):
    t0=time.time()
    while time.time()-t0<90:
        time.sleep(1.0)
        w=rs()
        if pos==9:
            if W(h,0x3390c)==8: break
        elif w[1]==pos and W(h,0x33a20)==0 and W(h,0x33938)==1: break
    time.sleep(1)
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down'); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=0.5)
    T0=time.time(); time.sleep(7); K('e',hold=0.3,gap=0.5); st('lvl1 (E on)'); print('  grid vs stock M1 T1 diffs:',grid_eq(1,0))
    force(); wait_level(1); st('after force1'); print('  grid vs stock M1 T1 diffs (custom, expect the 4 changed cells):',grid_eq(1,0)); h.shot(E+'e33_custom.png')
    force(); wait_level(2); st('after force2'); print('  grid vs stock M1 T3 diffs (expect none):',grid_eq(1,2)); h.shot(E+'e33_t3.png')
    force(); wait_level(9); st('after force3'); h.shot(E+'e33_end.png'); time.sleep(6); st('later'); h.shot(E+'e33_end2.png')
finally: h.close()
