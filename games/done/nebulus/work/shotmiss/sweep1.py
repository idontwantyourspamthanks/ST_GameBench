"""Sweep: frog at x=105 facing left shooting at a hopping ball (kind 1) behind the (removed) stack; stock code."""
import sys, time, json, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from sim import *
def classify(log):
    """returns (class, detail)"""
    kill = any(r['bst'] in (4,5) and (k==0 or log[k-1]['bst'] not in (4,5)) for k,r in enumerate(log))
    hits = [(r['i'], r['ov']) for r in log if any(h for h,_ in (r['ov'] or []))]
    if kill: return 'HIT', hits[:1]
    if hits: return 'HIT_NOEFFECT', hits[:1]
    shotted = [r for r in log if r['sst'] == 1]
    if not shotted: return 'NOSHOT', None
    terr = [r['i'] for r in log if r['terr']]
    # geometric near-overlap: |dx|<=2 and |dy|<=6 at some loop where shot active
    near = [(r['i'], sgn(r['sx']-r['bx'],128), r['sy']-r['by']) for r in shotted if abs(sgn(r['sx']-r['bx'],128))<=2 and abs(r['sy']-r['by'])<=6]
    if terr: return 'MISS_TERRAIN', terr[:1]
    lastshot = shotted[-1]
    return 'MISS_FLIGHT', (lastshot['sx'], lastshot['scnt'], near[:2])
if __name__ == '__main__':
    s = Sim(); img = s.snap(); pr = Probe(s)
    res = collections.Counter(); rows = []
    t0 = time.time()
    for fx in (105,):
      for spd in (0, 1, -1):
        for bx in range(70, 105):
          for cnt in range(0, 11):
            for fire_at in (0,):
                prep(s, img, dict(x=bx, y=60, spd=spd, cnt=cnt, st=1), dict(x=fx))
                log = shoot(s, fire_at=fire_at, nloops=26, probe=pr)
                c, d = classify(log)
                res[(spd, c)] += 1
                rows.append((fx, spd, bx, cnt, fire_at, c, d))
    print(time.time()-t0, 's', len(rows))
    for k in sorted(res): print(k, res[k])
    json.dump(rows, open('/tmp/sweep1.json','w'))
