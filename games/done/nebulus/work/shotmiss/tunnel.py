"""Class (a): tunnelling.  For every attempt of the uniform grid (stock, fixed mask not needed): did the shot's x pass the ball's x (dx = shot.x-ball.x went from >=+3 to <=-3, or sign flipped while |dy| <= 5)
between two consecutive overlap tests without ANY test overlapping the intended (symmetric) box?  Also prints the maximum relative x step per loop."""
import sys, itertools, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
import sweep2
from sim import *
from ideal import ideal_hit, sgn as isgn
s = Sim(); img = s.snap(); pr = Probe(s)
maxrel = 0; cross = 0; n = 0; crossed_nohit = 0
for fx, spd, bx, cnt, fire in itertools.product((105,), (0, 1, -1), range(66, 106), range(11), range(0, 11)):
    prep(s, img, dict(x=bx, y=60, spd=spd, cnt=cnt, st=1), dict(x=fx), patches=sweep2.PATCH['fix'])
    log = shoot(s, fire_at=fire, nloops=28, probe=pr)
    tested = [r for r in log if r['ov']]
    n += 1
    for a, b in zip(tested, tested[1:]):
        ea, eb = a['ent'][0], b['ent'][0]
        dxa = isgn(ea['sx'] - ea['cr'][0][0], 128); dxb = isgn(eb['sx'] - eb['cr'][0][0], 128)
        # relative step in x between the two tests (shot and ball moved in the same loop)
        rel = abs(isgn(dxb - dxa, 128)); maxrel = max(maxrel, rel)
        if dxa > 0 and dxb < 0 and abs(dxa) + abs(dxb) >= 1:
            cross += 1
            hit_any = any(h for h, _ in a['ov'] + b['ov'])
            if not hit_any and abs(eb['sy'] - eb['cr'][0][1]) <= 5 and eb['cr'][0][2] not in (0, 4, 6, 7): crossed_nohit += 1
print('attempts', n, 'x crossings between consecutive tests', cross, 'crossings with |dy|<=5 and no hit (tunnelling, with the mask fixed)', crossed_nohit, 'max |relative x step| per loop', maxrel)
