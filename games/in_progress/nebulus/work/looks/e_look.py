"""Editor behaviour check (user question b): new level defaults, Tower > Look writes THIS level's record, level 2 does not inherit level 1's look.
usage: e_look.py GAMEDIR(with a zero NEBLEVEL.OVL) OUTDIR"""
import sys,time,struct,os
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ui import *
from pathlib import Path
import ovl
OUT=Path(sys.argv[2]); OUT.mkdir(parents=True,exist_ok=True)
h=start('/tmp/looks/wd_elook',Path(sys.argv[1]))
def st(tag):
    w=rs(h)   # RS words: +12 rsMis (idx 6), +14 rsTow (idx 7), +16 rsRows?, rsTime..
    print(f"{tag:34s} rsMis {w[6]} rsTow {w[7]} rsSlot {w[8]} rsLvl {w[2]} rsEd {w[3]} | vDirty {W(h,V+162)}",flush=True)
    h.shot(str(OUT/(tag.replace(' ','_')+'.png')))
try:
    h.key('F10',hold=0.5); time.sleep(2)
    select(h,'Levels'); select(h,'<new level>',1.5); st('L1 new level opened')
    fire(h); select(h,'Tower >'); st('L1 tower menu')
    select(h,'Look: next tower',0.8); select(h,'Look: next tower',0.8) if False else None
    fire(h); select(h,'Tower >'); select(h,'Look: next tower',0.8)
    st('L1 after 2x look next')
    fire(h); select(h,'Tower >'); select(h,'Look: other mission',0.8); st('L1 after other mission')
    fire(h); select(h,'Leave editor',1.5); show(h,'after leaving L1')
    select(h,'<new level>',1.5); st('L2 new level opened')
    fire(h); select(h,'Tower >'); select(h,'Look: next tower',0.8); select(h,'Look: next tower',0.8) if False else None
    fire(h); select(h,'Tower >'); select(h,'Look: next tower',0.8)
    fire(h); select(h,'Tower >'); select(h,'Look: next tower',0.8); st('L2 after 3x look next')
    fire(h); select(h,'Leave editor',1.5); lv,cs=show(h,'after leaving L2')
    d,_=store(h); open(OUT/'store_after.ovl','wb').write(d)
finally: h.close()
