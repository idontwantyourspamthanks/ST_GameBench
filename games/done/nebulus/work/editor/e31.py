from ed import *
import shutil, sys
gd=__import__('pathlib').Path
RS=0x77c80
h=Nebulus(workdir='/tmp/ned31',game=gd(E+'build_ed'))
def K(k,n=1,hold=0.2,gap=0.35):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def st(tag):
    w=struct.unpack('>20H',grab(h,RS,40,'rs'))
    print(f"{tag:10s} t={time.time()-T0:5.1f} rsCamp {w[0]} rsPos {w[1]} rsLvl {w[2]} | tower {W(h,0x3390c)} pl {W(h,0x33a20)} 46={W(h,0x33a46)} 3390e={W(h,0x3390e)} timer {grab(h,0x3ad98,6).hex()} lives {W(h,0x33922)} 33938={W(h,0x33938)}",flush=True)
def force():
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down'); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=0.5)
    T0=time.time(); time.sleep(8); st('lvl1')
    force()
    for i in range(14):
        time.sleep(2.5); st(f'f1+{i}')
    force()
    for i in range(14):
        time.sleep(2.5); st(f'f2+{i}')
    h.shot(E+'e31_end.png')
finally: h.close()
