import sys; sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/example')
from drv import *
r = Run('/tmp/neb_ex/old_start.sav', '/tmp/neb_ex/wd2', '/tmp/neb_ex/g_wd1', trainers=('E','T'))
try:
    ok, fl, txt = r.go([dict(cell=0x08), dict(cond='x>=10', cell=0x88), dict(cond='stp>=3&st=2', cell=0)], tail=3)
    print(ok, len(fl))
    for f in fl: print(f['x'],f['y'],f['st'],f['stp'],f['pose'])
finally: r.close()
