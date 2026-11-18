from ed import *
import shutil, sys
gd=__import__('pathlib').Path
src=gd(E+'build_ed'); dst=gd('/tmp/gd_e21')
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src,dst); (dst/'NEBLEVEL.OVL').write_bytes(bytes(4096))
h=Nebulus(workdir='/tmp/ned21',game=dst)
try:
    print('title',h.boot_to_title(timeout=100),flush=True)
    time.sleep(3)
    h.shot(E+'e21_title.png')
    h.key('F10',hold=0.5); time.sleep(3)
    h.shot(E+'e21_ed0.png')
    print('vframe',W(h,0x76730),'mode',W(h,0x7673e),'pc?',h.debug('r',0.8)[-300:])
finally: h.close()
