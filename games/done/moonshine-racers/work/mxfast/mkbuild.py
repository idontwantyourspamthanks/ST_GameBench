import sys, subprocess
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/mxfast')
from mflib import *
s = sets()
for v, tag in (('M', 'mf_hd'), ('G', 'mg_hd'), ('X', 'mx_hd')):
    r = subprocess.run([sys.executable, PRIV, 'build', '--only', *(s[v] + ['pp_bigram_cache']), '--out', f'work/mxfast/build/{tag}'], capture_output=True, text=True, cwd=GAME)
    print(v, tag, 'rc', r.returncode, [l for l in r.stdout.splitlines() if 'payload' in l or 'built' in l][-1:])
