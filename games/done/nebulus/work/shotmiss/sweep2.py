"""Sweep v2: classify every shot against the hopping ball (kind 1) in tower-1 geometry; stock / ni_shoot / np_shot variants.
usage: sweep2.py VARIANT   (stock | shoot | fix | shootfix)  -> /tmp/sweep2_<variant>.json + summary"""
import sys, time, json, collections, itertools
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from sim import *
from ideal import ideal_hit, sgn as isgn
PATCH = {'stock': [], 'shoot': [(0x3a332, b'\x4e\x71')], 'fix': [(0x3b87a, b'\x66\x08\x48\x80')],
         'shootfix': [(0x3a332, b'\x4e\x71'), (0x3b87a, b'\x66\x08\x48\x80')]}

def classify(log):
    """-> (class, tested_loops, detail).  classes:
       HIT         shot killed the ball (ball state -> 4/5 in the loop of the overlap result)
       MISS_MASK   >=1 tested loop where the intended hit box (symmetric table) overlaps but sub_03b7d6 said no and the ball was hittable
       MISS_RANGE  shot expired after 12 moves (24 px) without any intended overlap
       MISS_TUNNEL shot/ball crossed (dx sign change, |dy|<=5) in consecutive loops without an intended overlap
       NOSHOT      frog got hit / no shot spawned
       MISS_OTHER  anything else"""
    tested = [r for r in log if r['ov']]
    kill = [r['i'] for r in log if r['ov'] and any(h for h, _ in r['ov'])]
    ideal_missed = []; false_hit = []
    for r in tested:
        e = r['ent'][0]
        ih = any(st not in (0, 4, 6, 7) and ideal_hit(e['sx'], e['sy'], cx, cy) for cx, cy, st in e['cr'])
        ah = any(h for h, _ in r['ov'])
        if ih and not ah: ideal_missed.append(r['i'])
        if ah and not ih: false_hit.append(r['i'])
    if kill:
        return ('HIT_FALSE' if (false_hit and not ideal_missed and kill[0] == false_hit[0]) else 'HIT'), len(tested), dict(ideal_missed=ideal_missed, false_hit=false_hit, kill=kill[0])
    if not tested: return 'NOSHOT', 0, None
    if ideal_missed: return 'MISS_MASK', len(tested), dict(ideal_missed=ideal_missed)
    # tunnelling check
    cr = []
    for a, b in zip(tested, tested[1:]):
        if b['i'] == a['i'] + 1:
            da = isgn(a['sx'] - a['bx'], 128); db = isgn(b['sx'] - b['bx'], 128)
            if (da > 0) != (db > 0) and abs(b['sy'] - b['by']) <= 5 and abs(da) + abs(db) >= 3 and not (-3 <= da <= 2 and -3 <= db <= 2):
                cr.append((a['i'], da, db))
    if cr: return 'MISS_TUNNEL', len(tested), dict(cross=cr)
    last = tested[-1]
    return 'MISS_RANGE', len(tested), dict(last=(last['sx'], last['scnt'], last['bx']))

def run(variant, fxs=(105,), bxs=range(66, 105), cnts=range(0, 11), spds=(0, 1, -1), fires=(0,), out=None, nloops=28):
    s = Sim(); img = s.snap(); pr = Probe(s)
    rows = []; res = collections.Counter()
    for fx, spd, bx, cnt, fire in itertools.product(fxs, spds, bxs, cnts, fires):
        prep(s, img, dict(x=bx, y=60, spd=spd, cnt=cnt, st=1), dict(x=fx), patches=PATCH[variant])
        log = shoot(s, fire_at=fire, nloops=nloops, probe=pr)
        c, nt, d = classify(log)
        frog_hit = any(r['pst'] == 7 for r in log)
        # kill must come from the shot hit, not noshot; rows
        rows.append(dict(fx=fx, spd=spd, bx=bx, cnt=cnt, fire=fire, cls=c, ntest=nt, d=d, frog_hit=frog_hit))
        res[(spd, c)] += 1
    if out: json.dump(rows, open(out, 'w'))
    return rows, res

if __name__ == '__main__':
    v = sys.argv[1]
    t0 = time.time()
    rows, res = run(v, out=f'/tmp/sweep2_{v}.json')
    print(v, round(time.time() - t0, 1), 's', len(rows))
    tot = collections.Counter(r['cls'] for r in rows); print(dict(tot))
    for k in sorted(res): print(k, res[k])
