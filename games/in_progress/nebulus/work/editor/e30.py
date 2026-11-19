from ed import *
import shutil, sys
gd=__import__('pathlib').Path
RS=0x77c80
ovl=sys.argv[1] if len(sys.argv)>1 else '/tmp/test3.ovl'
os.system(f"cd {G} && python3 work/editor/nepatch_priv.py build --out work/editor/build_ed --only nt_trainers ed_overlay --ovl {ovl} >/dev/null")
h=Nebulus(workdir='/tmp/ned30',game=gd(E+'build_ed'))
def K(k,n=1,hold=0.2,gap=0.35):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def st(tag):
    d=grab(h,RS,40,'rs'); w=struct.unpack('>20H',d)
    print(f"{tag:12s} rsCamp {w[0]} rsPos {w[1]} rsLvl {w[2]} rsEd {w[3]} rsTest {w[4]} | tower {W(h,0x3390c)} mission {W(h,0x33910)} timer {grab(h,0x3ad98,6).hex()} lives {W(h,0x33922)}",flush=True)
def force():
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    print('store magic',grab(h,0xBC000,16).hex(' '))
    h.key('F10',hold=0.5); time.sleep(2); h.shot(E+'e30_main.png')
    K('Down'); K('Control_R',hold=0.4,gap=1.0); h.shot(E+'e30_camps.png')
    K('Control_R',hold=0.4,gap=1.0); h.shot(E+'e30_campmenu.png')
    K('Control_R',hold=0.4,gap=0.5)          # Play
    time.sleep(6); st('started'); h.shot(E+'e30_lvl1.png')
    for n in range(4):
        force(); 
        for i in range(40):
            time.sleep(1.5)
            d=struct.unpack('>20H',grab(h,RS,40,'rs'))
            if d[1]!=n or W(h,0x3390c)==8: break
        time.sleep(6); st(f'after force {n+1}'); h.shot(E+f'e30_lvl{n+2}.png')
        g=grab(h,0x327f0,0x1000); print('   cells (3,1) (4,1) (3,2) (4,2):',[hex(g[c*256+r]) for c,r in [(3,1),(4,1),(3,2),(4,2)]])
finally: h.close()
