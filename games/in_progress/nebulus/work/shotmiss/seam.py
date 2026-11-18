"""Class (d): wrap-around at the tower's x=127/0 seam.  The same attempts shifted by `s` angle units (frog, ball and the ledge cells); outcomes must not depend on s."""
import sys, collections, itertools
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from hatt import *
import sweep2
def run(variant, shift):
    fixes = VARIANT[variant]
    ledge = [B8(cell(c, r), 0x81 if r == 14 else 0) for c in range(16) for r in range(10, 22)]   # rotation-symmetric world: a full ring ledge, nothing else near it
    cnt = collections.Counter(); out = {}
    for fx, d, c, spd in itertools.product((101, 105, 109), range(4, 30, 2), range(0, 11, 2), (0, 1, -1)):
        at = dict(fx=(fx + shift) & 127, bx=(fx - d + shift) & 127, cnt=c, spd=spd)
        _, rows, _ = sim_chain([at], fixes=fixes, extra_pokes=ledge)
        cls, nt, dd = sweep2.classify(rows)
        out[(fx, d, c, spd)] = cls; cnt[cls] += 1
    return out, cnt
if __name__ == '__main__':
    for v in ('stock', 'fix'):
        res = {}
        for sh in (0, 24, 40, 56, 88, 104):
            o, c = run(v, sh); res[sh] = o
            print(v, 'shift', sh, dict(c))
        diffs = sum(res[0][k] != res[sh][k] for sh in (24, 40, 56, 88, 104) for k in res[0])
        print(v, 'attempts whose class differs from shift 0:', diffs)
