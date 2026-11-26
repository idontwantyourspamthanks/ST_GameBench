from ui import *
import sys, ovl
gd=__import__('pathlib').Path
os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_final --only nt_trainers ed_overlay --ovl /tmp/test3.ovl >/dev/null")
h=start('/tmp/ned80',gd(E+'build_final'))
def entry_op(i,op):
    select_i(h,i); select(h,op,1.2)
def chk(cond,msg): print(('PASS ' if cond else 'FAIL ')+msg,flush=True)
try:
    h.key('F10',hold=0.5); time.sleep(2)
    lv,cs=show(h,'initial')
    # ---- campaign editor
    select(h,'Campaigns'); select(h,'<new campaign>',1.5)
    select(h,'<add entry>',1.2); select(h,'<add entry>',1.2)
    lv,cs=show(h,'2 entries'); chk(len(cs)==2 and cs[1][1]==[0x80,0x80],'new campaign with 2 entries')
    entry_op(0,'Change source'); entry_op(0,'Change source')
    lv,cs=show(h,'cycled 2x'); chk(cs[1][1][0]==0x82,'change source x2 -> orig M1 T3')
    entry_op(1,'Insert after'); lv,cs=show(h,'inserted'); chk(len(cs[1][1])==3 and cs[1][1][1]==cs[1][1][2]==0x80,'insert after')
    entry_op(2,'Move up'); lv,cs=show(h,'moved up'); chk(cs[1][1]==[0x82,0x80,0x80],'move up (swap equal entries keeps order)')
    entry_op(0,'Move down'); lv,cs=show(h,'moved down'); chk(cs[1][1]==[0x80,0x82,0x80],'move down')
    entry_op(1,'Change source'); entry_op(1,'Change source'); entry_op(1,'Change source'); entry_op(1,'Change source')
    lv,cs=show(h,'cycle to custom'); print('   entry1 =',hex(cs[1][1][1]))
    entry_op(2,'Remove'); lv,cs=show(h,'removed'); chk(len(cs[1][1])==2,'remove')
    select(h,'< back',1.2)                      # entry list -> campaign list
    select_i(h,1); select(h,'Rename',1.0)       # name entry
    K(h,'Up',1); K(h,'Right',1); K(h,'Down',1); fire(h,1.2)
    lv,cs=show(h,'renamed'); print('   name',repr(cs[1][0]))
    chk(cs[1][0].startswith('OEW') or cs[1][0].startswith('NEW')==False,'rename changed the name')
    select_i(h,1); select(h,'Delete',1.2); lv,cs=show(h,'deleted camp'); chk(len(cs)==1,'delete campaign')
    # ---- level ops
    select(h,'< back',1.2); select(h,'Levels',1.2)
    select_i(h,0); select(h,'Copy',1.2); lv,cs=show(h,'copied'); chk(len(lv)==2 and lv[0]['grid']==lv[1]['grid'],'copy level')
    select_i(h,1); select(h,'Edit',1.5)
    fire(h); select(h,'Level >'); select(h,'Name',1.0)
    K(h,'Up',1); fire(h,1.0)                    # name entry in the editor
    fire(h); select(h,'Leave editor',1.5)       # commit
    lv,cs=show(h,'renamed level'); chk(lv[1]['name'].startswith('OY') or lv[1]['name']!=lv[0]['name'],'level rename + commit')
    select_i(h,0); select(h,'Delete',1.5); lv,cs=show(h,'deleted level 0')
    chk(len(lv)==1 and cs[0][1]==[0x80,0x82],'delete level: campaign TEST REMIX lost its custom entry')
    select(h,'< back',1.2); select(h,'Save to disk',1.0); time.sleep(4); h.shot(E+'e80_saved.png')
    print('vErr',hex(L(h,0x77cf4)),flush=True)
finally: h.close()
os.system("cd /tmp/ned80; mcopy -n -o -i hd.img@@1024 ::NEBLEVEL.OVL /tmp/e80.ovl && python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/ovl.py validate /tmp/e80.ovl && python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor/ovl.py dump /tmp/e80.ovl")
