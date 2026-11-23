"""Equivalence gate: scripted2-style loop-keyed scenarios (J1, K1, K1n, K2n, K3, K4b, K5 of work/input) with and without np_shot (live pokes), enemies ON/OFF as in input.md 11.
Outputs go to work/shotmiss/eq/sc/<tag>/ (scripted2.W is redirected); the reference run for loop numbering is made first.
usage: eq_run.py <scenario> <variant>     variants: stock fix all allfix  (all = ni_jump+ni_shoot+ni_turn live pokes, i.e. the default set's gameplay patches)"""
import sys, os, runpy
from pathlib import Path
IN = '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input'
EQ = '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss/eq'
sys.path.insert(0, IN)
import scripted2 as S
S.W = Path(EQ)
FIX = ['w $3b87a $66 $08 $48 $80']
S.LIVE['stock'] = []
S.LIVE['fix'] = FIX
S.LIVE['allfix'] = S.LIVE['all'] + FIX
os.chdir(EQ)
scen, var = sys.argv[1], sys.argv[2]
if not Path('sc/s1/log.txt').exists():
    S.run('s1', [], duration=9.0)           # reference run: loop numbering = first flip with the timer ticking (same procedure as input.md 8.2)
tag = f'{scen}_{var}'
if scen == 'j1':
    sys.argv = ['s3.py', tag, var]; runpy.run_path(IN + '/s3.py', run_name='__main__')
elif scen == 'j1n':
    sys.argv = ['s3.py', 'noen_' + tag, var]; runpy.run_path(IN + '/s3.py', run_name='__main__')
elif scen in ('k1', 'k2', 'k3'):
    sys.argv = ['s5.py', scen, tag, var]; runpy.run_path(IN + '/s5.py', run_name='__main__')
elif scen in ('k1n', 'k2n'):
    sys.argv = ['s5.py', scen[:2], tag, var, 'noen']; runpy.run_path(IN + '/s5.py', run_name='__main__')
elif scen in ('k4', 'k4b', 'k5'):
    sys.argv = ['s6.py', scen, tag, var]; runpy.run_path(IN + '/s6.py', run_name='__main__')
