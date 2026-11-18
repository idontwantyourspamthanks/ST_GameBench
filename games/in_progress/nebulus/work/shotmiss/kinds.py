"""By-design 'hit, nothing happens' cases of the stock code: creature kinds that survive a shot (sub_03b9a2 $3ba18..$3ba72)."""
import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from hatt import *
def trace(st, spd, tgt, bx=90, by=60, cnt=0, nl=16, fire2=None):
    s = Sim(BASE); pr = Probe(s)
    for a, b in attempt_pokes(dict(bx=bx, by=by, cnt=cnt, spd=spd, fx=105, st=st)): s.uc.mem_write(a, b)
    s.ww(fld(0, F_TGT), tgt)
    out = []
    for i in range(nl):
        s.wb(0x38498, 0x80 if i in (0, 1) or (fire2 is not None and fire2 <= i < fire2 + 2) else 0)
        pr.rows.clear(); loop(s, extra=True)
        b0 = slot(s, 0); sh = slot(s, SHOT)
        out.append((i, 'ball', b0['x'], b0['y'], 'st', b0['st'], 'cnt', b0['cnt'], 'shot', sh['x'], sh['st'], [(h) for h, k, e in pr.rows]))
    return out
for name, st, spd, tgt in (('kind1 ball (state 1)', 1, 0, 1), ('kind2 walker (state 2)', 2, 1, 2), ('kind8 vertical eye (state 8)', 8, 1, 8), ('kind9 horizontal eye (state 9)', 9, 1, 9)):
    print('==', name)
    for r in trace(st, spd, tgt, bx=92 if st != 8 else 96): print(r)
print('== kind2 walker, second shot while stunned (state 5)')
for r in trace(2, 1, 2, bx=92, nl=24, fire2=9): print(r)
