from ed import *
import shutil, sys
gd=__import__('pathlib').Path
src=gd(E+'build_ed'); dst=gd('/tmp/gd_e22')
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src,dst); (dst/'NEBLEVEL.OVL').write_bytes(bytes(4096))
h=Nebulus(workdir='/tmp/ned22',game=dst)
def K(k,n=1,hold=0.2,gap=0.2):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def S(name): time.sleep(0.5); h.shot(E+f'e22_{name}.png'); print(name,'cx',W(h,0x76732),'cy',W(h,0x76734),'mode',W(h,0x7673e),'sel',W(h,0x76744),flush=True)
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Right',3,gap=0.3); K('Up',5,gap=0.3); S('moved')
    K('Control_R',1,hold=0.4,gap=0.5); S('menu')
    K('Down',1,gap=0.3); K('Control_R',1,hold=0.4,gap=0.8); S('ledge_placed')
    K('Right',2,gap=0.3); K('Control_R',1,hold=0.4,gap=0.5); K('Down',7,gap=0.3); S('enemy_item')
    K('Control_R',1,hold=0.4,gap=0.5); S('enemy_menu')
    K('Control_R',1,hold=0.4,gap=0.5); S('dir_menu')
    K('Control_R',1,hold=0.4,gap=0.8); S('enemy_placed')
    K('Up',3,gap=0.3); K('Control_R',1,hold=0.4,gap=0.5); K('Down',3,gap=0.3); K('Control_R',1,hold=0.4,gap=0.5)
    K('Down',3,gap=0.3); K('Control_R',1,hold=0.4,gap=0.5); K('Control_R',1,hold=0.4,gap=0.5); S('eye_placed')
finally: h.close()
