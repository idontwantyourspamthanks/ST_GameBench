import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/jagpad')
from jt import *
J=('jag_poll','jag_dir','jag_btn')
sets={'fire_fix_jag':names(), 'fire_fix_nojag':names(drop=J), 'fire_old_jag':names(drop=('p3cp_keys',)), 'fire_old_nojag':names(drop=J+('p3cp_keys',))}
for k,v in sets.items():
    print(k, build_live(v,k), len(v))
