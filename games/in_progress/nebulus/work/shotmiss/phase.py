"""Where do the stock misses sit?  For every loop in which the shot's intended hit box overlaps the (hittable) ball: actual hit/miss by dy, ball hop counter, loop parity, frog x."""
import sys, itertools, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from sim import *
from ideal import ideal_hit, sgn as isgn
s = Sim(); img = s.snap(); pr = Probe(s)
by_dy = collections.defaultdict(lambda: [0, 0]); by_cnt = collections.defaultdict(lambda: [0, 0]); by_par = collections.defaultdict(lambda: [0, 0]); by_fx = collections.defaultdict(lambda: [0, 0]); by_dx = collections.defaultdict(lambda: [0, 0])
first_ov = collections.Counter()
n = 0
for fx, spd, bx, cnt, fire in itertools.product((100, 103, 105, 108, 110), (0, 1, -1), range(66, 110), range(11), range(0, 11, 2)):
    prep(s, img, dict(x=bx, y=60, spd=spd, cnt=cnt, st=1), dict(x=fx))
    log = shoot(s, fire_at=fire, nloops=28, probe=pr)
    n += 1
    # per attempt: the FIRST loop with an intended overlap decides (after a hit the shot is gone); misses continue to later loops
    for r in log:
        if not r['ov']: continue
        e = r['ent'][0]
        cx, cy, st = e['cr'][0]
        if st in (0, 4, 6, 7): continue
        if ideal_hit(e['sx'], e['sy'], cx, cy):
            dy = e['sy'] - cy; dx = isgn(e['sx'] - cx, 128); hit = any(h for h, _ in r['ov'])
            for d, k in ((by_dy, dy), (by_cnt, r['bcnt'] if False else (r['bcnt'] - 1) % 11), (by_par, r['i'] % 2), (by_fx, fx), (by_dx, dx)):
                d[k][0] += 1; d[k][1] += (not hit)
            break
def show(name, d):
    print(name, ' '.join('%s:%d/%d' % (k, v[1], v[0]) for k, v in sorted(d.items())))
print('attempts', n, '(first intended overlap per attempt: misses/overlaps)')
show('by dy (shot.y-ball.y)', by_dy); show('by ball hop counter at the test', by_cnt); show('by loop parity', by_par); show('by frog x', by_fx); show('by dx', by_dx)
