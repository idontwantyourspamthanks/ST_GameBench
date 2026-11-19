from ed import *
import sys
sys.path.insert(0,E)
import ovl
gd=__import__('pathlib').Path
RS=0x77c80
os.system(f"cd {G} && python3 work/editor/gen_ed.py >/dev/null && python3 work/editor/nepatch_priv.py build --out work/editor/build_ed --only nt_trainers ed_overlay >/dev/null")
h=Nebulus(workdir='/tmp/ned40',game=gd(E+'build_ed'))
def K(k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R',hold=0.35,gap=gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def S(tag):
    w=rs(); print(f"{tag:14s} rsCamp {w[0]} rsPos {w[1]} rsLvl {w[2]:#x} rsEd {w[3]} rsTest {w[4]} rsSlot {w[5]} cx {w[10]} cy {w[11]} top {w[12]} rows {w[8]} | tower {W(h,0x3390c)} pl {W(h,0x33a20)} t {grab(h,0x3ad98,6).hex()}",flush=True)
    h.shot(E+f'e40_{tag.replace(" ","_")}.png')
def cells(): 
    g=grab(h,0x327f0,0x1000); return [hex(g[c*256+r]) for c,r in [(3,4),(4,4),(5,4)]]
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down',2); F(1.0); S('levels')
    F(1.5); S('editor_new')
    K('Right',3); K('Up',3); S('moved')
    F(); K('Down',1); S('cellmenu'); F(1.0)
    K('Right'); F(); K('Down',4); F(1.0)
    K('Right'); F(); K('Down',7); F(); S('enemymenu'); F(); F(1.0)
    S('edited'); print('cells (3,4) (4,4) (5,4):',cells())
    F(); K('Down',9); S('playtest_item'); F(1.0)
    time.sleep(8); S('playing'); print('cells in play:',cells())
    h.key('F10',hold=0.5); time.sleep(3); S('back_in_editor'); print('cells after:',cells())
    h.key('F10',hold=0.5); time.sleep(2); S('level_list')
    K('Down',2); F(1.0); S('main_again'); K('Down',3); F(1.0); time.sleep(3); S('saved')
finally: h.close()
os.system("cd /tmp/ned40; mcopy -n -o -i hd.img@@1024 ::NEBLEVEL.OVL /tmp/e40.ovl && python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/ovl.py dump /tmp/e40.ovl")
