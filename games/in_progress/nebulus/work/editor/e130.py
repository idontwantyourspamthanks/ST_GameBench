from ui import *
gd=__import__('pathlib').Path
os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_final --only nt_trainers ed_overlay --ovl /tmp/test3.ovl >/dev/null")
h=start('/tmp/ned130',gd(E+'build_final'))
try:
    h.key('F10',hold=0.5); time.sleep(2)
    select(h,'Levels'); select_i(h,0); select(h,'Edit',1.5)
    fire(h); select(h,'Tower >'); select(h,'Name',1.0); K(h,'Right',2); K(h,'Up',1); time.sleep(0.6); h.shot(E+'guide_13_name_entry.png')
    fire(h,1.0); fire(h); select(h,'Leave editor',1.5); lv=show(h,'after rename')
    h.key('F10',hold=0.5); time.sleep(2); print('menu',menu(h)[0][:3])
finally: h.close()
