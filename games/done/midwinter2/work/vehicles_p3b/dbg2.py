import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
import subprocess
def default_names():
    out = subprocess.run([sys.executable, str(GAME/'tools/mw2patch.py'), 'list'], capture_output=True, text=True, cwd=GAME).stdout
    names=[]
    for l in out.splitlines()[1:]:
        p=l.split()
        if len(p)>2 and p[1]=='yes' and 'HAGA' not in l and not l.startswith(('pp_','floppy')) and p[0]!='mw2_credit': names.append(p[0])
    return names
drop = {'p3b_head','p3b_pos','p3b_hdg','p3b_alt','p3b_bank','p3b_save','p3b_probe'}
names=[n for n in default_names() if n not in drop]+['p3c_head','p3c_sim']
print(names)
live=build_live(names,'dbg2')
h=Hatari(snapshot=str(SNAP/'raid_onfoot_dhafra.sav'),memsize_kb=2048)
try:
    v=h.vbl(); at_flip(h, apply_cmds(live), v+100)
    time.sleep(5)
    print(h._logtext()[-1500:])
finally: h.close()
