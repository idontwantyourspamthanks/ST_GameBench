"""Real-Hatari experiment: N shot attempts at the hopping ball in tower-1 geometry, same attempts for stock / ni_shoot / np_shot-fix / both.
usage: hat_main.py gen | run VARIANT"""
import sys, json, random, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from hatt import *
import sweep2
AT = W + 'shotmiss/attempts.json'
def sim_outcome(rows_of_attempt):
    return 'HIT' if any(r['bst'] in (4, 5) for r in rows_of_attempt) else 'MISS'
def gen():
    rnd = random.Random(1987)
    pop = []
    for fx in range(100, 111):
        for d in range(6, 30):
            for cnt in range(11):
                for spd in (0, 1, -1):
                    pop.append(dict(fx=fx, bx=fx - d, cnt=cnt, spd=spd))
    rnd.shuffle(pop)
    # classify each candidate under stock in the sim (single attempts, fresh sim each)
    keep_rand, keep_miss = [], []
    for at in pop:
        _, rows, _ = sim_chain([at], nloops_each=SPAN)
        c, nt, d = sweep2.classify(rows)
        if c in ('NOSHOT', 'MISS_RANGE'): continue
        at = dict(at, sim_stock=c)
        if len(keep_rand) < 60: keep_rand.append(at)
        elif c == 'MISS_MASK' and len(keep_miss) < 30: keep_miss.append(at)
        if len(keep_rand) >= 60 and len(keep_miss) >= 30: break
    json.dump(dict(random=keep_rand, targeted_miss=keep_miss), open(AT, 'w'), indent=0)
    print(len(keep_rand), len(keep_miss), collections.Counter(a['sim_stock'] for a in keep_rand))
def run(variant, which='all'):
    d = json.load(open(AT)); ats = d['random'] + d['targeted_miss']
    ats = [{k: v for k, v in a.items() if k != 'sim_stock'} for a in ats]
    timers, fl, starts, srows = hat_chain(ats, 'hm_' + variant, variant=variant, max_wait=600)
    hr = hat_rows(timers, fl)
    nm, nd, first = compare(srows, hr)
    print(variant, 'loops matched sim==Hatari', nm, 'differ', nd, first)
    out = []
    for k, (at, L) in enumerate(zip(ats, starts)):
        hs = [hr[l] for l in range(L, L + SPAN) if l in hr]
        ss = [r for r in srows if L <= r['L'] < L + SPAN]
        ho = 'HIT' if any(r['bst'] in (4, 5) for r in hs) else 'MISS'
        so = sim_outcome(ss)
        out.append(dict(k=k, **at, hatari=ho, sim=so, nloops_h=len(hs), shot_end=[(r['sx'], r['sy']) for r in hs if r['sst'] == 1][-1:], frog_hit=any(r['pst'] == 7 for r in hs)))
    import re
    log = open(W + f'shotmiss/sc/hm_{variant}/log.txt').read()
    stamps = [int(x) for x in re.findall(r'> e VBL\n= [^\n]*#(\d+) \(dec\)', log)]
    per = [(stamps[2 * k + 1] - stamps[2 * k]) / 2 for k in range(len(ats)) if 2 * k + 1 < len(stamps)]
    if per: print(variant, 'VBL per game loop (stamps 2 loops apart, per attempt): min %.2f mean %.2f max %.2f' % (min(per), sum(per) / len(per), max(per)))
    json.dump(out, open(W + f'shotmiss/hat_{variant}.json', 'w'))
    for part, sl in (('random 60', out[:60]), ('targeted-miss 30', out[60:])):
        print(variant, part, dict(collections.Counter(o['hatari'] for o in sl)), 'sim==hatari in', sum(o['hatari'] == o['sim'] for o in sl), '/', len(sl))
if __name__ == '__main__':
    gen() if sys.argv[1] == 'gen' else run(sys.argv[2])
