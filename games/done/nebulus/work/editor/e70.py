from ui import *
import sys
gd=__import__('pathlib').Path
os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_final --only nt_trainers ed_overlay --ovl /tmp/test3.ovl >/dev/null")
h=start('/tmp/ned70',gd(E+'build_final'))
try:
    h.key('F10',hold=0.5); time.sleep(2)
    select(h,'Levels'); print(menu(h))
    select(h,'<new level>',1.5)
    K(h,'Right',3); K(h,'Up',3)
    fire(h); select(h,'Enemy'); select(h,'Eye up'); select(h,'Start up',1.2)
    K(h,'Right',2); fire(h); select(h,'Enemy'); select(h,'Stone'); select(h,'Start left',1.2)
    time.sleep(1); h.shot(E+'e70_editor.png'); print(rs(h))
finally: h.close()
