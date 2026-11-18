"""Uniform-phase sweep: fire phase x hop phase x ball x x ball speed; variants stock/shoot/fix/shootfix; in-range = shot reaches the ball's x (distance <= 24)."""
import sys, json, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
import sweep2
out = {}
for v in ('stock','shoot','fix','shootfix'):
    rows, res = sweep2.run(v, fxs=(105,), bxs=range(70, 106), cnts=range(0, 11), spds=(0, 1, -1), fires=range(0, 11), out=f'/tmp/sweep3_{v}.json')
    inr = [r for r in rows if r['cls'] not in ('NOSHOT', 'MISS_RANGE')]
    c = collections.Counter(r['cls'] for r in inr)
    print(v, 'attempts', len(rows), 'in-range', len(inr), dict(c), 'miss %.1f%%' % (100 * c['MISS_MASK'] / len(inr)), 'all classes', dict(collections.Counter(r['cls'] for r in rows)))
    for spd in (0, 1, -1):
        rr = [r for r in inr if r['spd'] == spd]; cc = collections.Counter(r['cls'] for r in rr)
        print('   spd', spd, len(rr), dict(cc), 'miss %.1f%%' % (100 * cc['MISS_MASK'] / len(rr)))
