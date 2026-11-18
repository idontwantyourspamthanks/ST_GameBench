from ed import *
import sys
sys.path.insert(0,E)
gd=__import__('pathlib').Path
RS=0x77c80
h=Nebulus(workdir='/tmp/ned41',game=gd(E+'build_final'))
def K(k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R',hold=0.35,gap=gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def S(tag):
    w=rs(); print(f"{tag:14s} rsLvl {w[2]:#x} rsEd {w[3]} rsTest {w[4]} rsSlot {w[5]} mis {w[6]} tow {w[7]} rows {w[8]} time {w[9]:04x} cx {w[10]} cy {w[11]} | pl {W(h,0x33a20)} 33938 {W(h,0x33938)} tower {W(h,0x3390c)}",flush=True)
    h.shot(E+f'e41_{tag.replace(" ","_")}.png')
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down',2); F(1.0); S('levels')
    F(1.0); S('lvl_menu'); K('Down'); F(1.5); S('edit_loaded')
    g=grab(h,0x327f0,0x1000); print('cells (3,1) (4,1) (3,2) (4,2):',[hex(g[c*256+r]) for c,r in [(3,1),(4,1),(3,2),(4,2)]])
    F(); K('Down',9); F(1.0)                   # Playtest
    t0=time.time()
    while time.time()-t0<60:
        time.sleep(1.5)
        if W(h,0x33a20)==0 and W(h,0x33938)==1: break
    S('playing'); K('e',hold=0.3,gap=0.5)
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
    time.sleep(20); S('after_complete')
    g=grab(h,0x327f0,0x1000); print('grid intact:',[hex(g[c*256+r]) for c,r in [(3,1),(4,1),(3,2),(4,2)]])
finally: h.close()
