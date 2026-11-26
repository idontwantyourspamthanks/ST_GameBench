"""NebGateCore: ball-hit sweep on a snapshot of the SHIPPED build (hatt.hat_chain with own paths).
usage: hat_g.py SNAP TAG   -> runs the 60 random + 30 targeted-miss attempts of work/shotmiss/attempts.json (same file as hat_main.py), no live pokes; prints HIT/MISS per group."""
import sys, json, collections, re
from pathlib import Path
S0 = '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/'
sys.path.insert(0, S0 + 'shotmiss'); sys.path.insert(0, S0 + 'input')
import hatt
from hatt import *
import scripted2 as S
MYS = Path(S0 + 'gate_NebOddGateCore/shot')
src = open(hatt.__file__).read()
# own scripted2 output dir + own Hatari workdir
src = src.replace("S.W = Path(W + 'shotmiss')", "S.W = Path('%s')" % (S0 + 'gate_NebOddGateCore/shot')).replace("workdir='/tmp/sr-at'", "workdir='/tmp/oddcore/sr-at'")
ns = {}
exec(compile(src, 'hatt_g', 'exec'), ns)
snap, tag = sys.argv[1], sys.argv[2]
d = json.load(open(S0 + 'shotmiss/attempts.json')); ats0 = d['random'] + d['targeted_miss']
ats = [{k: v for k, v in a.items() if k != 'sim_stock'} for a in ats0]
timers, fl, starts, srows = ns['hat_chain'](ats, 'g_' + tag, variant='stock', snap=snap, max_wait=900)
hr = ns['hat_rows'](timers, fl)
out = []
for k, (at, L, a0) in enumerate(zip(ats, starts, ats0)):
    hs = [hr[l] for l in range(L, L + SPAN) if l in hr]
    ho = 'HIT' if any(r['bst'] in (4, 5) for r in hs) else 'MISS'
    out.append(dict(k=k, **at, stock_pred=a0['sim_stock'], hatari=ho, nloops=len(hs), frog_hit=any(r['pst'] == 7 for r in hs)))
json.dump(out, open(str(MYS / f'hat_{tag}.json'), 'w'))
for part, sl in (('random 60', out[:60]), ('targeted-miss 30', out[60:])):
    print(tag, part, dict(collections.Counter(o['hatari'] for o in sl)), 'stock-predicted MISS_MASK among them:', sum(o['stock_pred'] == 'MISS_MASK' for o in sl), 'short (loops<%d):' % SPAN, sum(o['nloops'] < SPAN for o in sl))
for o in out:
    if o['hatari'] != 'HIT': print('NON-HIT', o)
