"""Does the editor itself make a file that crashes the game?  Level 1: blank grid + ONE extra ledge cell (22 -> 23 cells = odd record), level 2: blank grid.
Then Levels > level 2 > Edit.  Reports the store layout and any Address Error in the Hatari log.  usage: e_odd.py GAMEDIR(zero OVL)"""
import sys,time,struct,os,subprocess
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ui import *
from pathlib import Path
WD='/tmp/looks/wd_eodd'
h=start(WD,Path(sys.argv[1]))
def addrerr(): return subprocess.run(f"grep -n 'Address Error' {WD}/log.txt",shell=True,capture_output=True,text=True).stdout.strip()
try:
    h.key('F10',hold=0.5); time.sleep(2)
    select(h,'Levels'); select(h,'<new level>',1.5)
    K(h,'Right',2); K(h,'Up',2); K(h,'l',1,hold=0.3)           # ledge at (2,3): one more non-zero cell
    fire(h); select(h,'Leave editor',1.5); show(h,'level 1 stored (odd size?)')
    d,p=store(h); lv=p[0]; print('level 1 record size',lv[0]['size'],'cells',sum(1 for a in range(16) for r in range(lv[0]['rows']) if lv[0]['grid'][a][r]),flush=True)
    select(h,'<new level>',1.5); fire(h); select(h,'Leave editor',1.5); show(h,'level 2 stored')
    print('address errors so far:',repr(addrerr()),flush=True)
    d,p=store(h); open('/tmp/looks/odd_store.ovl','wb').write(d)
    print('vbl vector',hex(L(h,0x70)),flush=True)
    select_i(h,1,1.5); select(h,'Edit',2.5)                     # level 2 > Edit
    print('after Edit of level 2: address errors:',repr(addrerr()),'vbl vector',hex(L(h,0x70)),flush=True)
    h.shot('/tmp/looks/odd_after_edit.png')
finally: h.close()
