"""Type 17 Parachute: original per-tick vertical model vs the p3b 5-pass split (p3b_apply3 + p3b_par), exhaustive-ish check
plus comparison with the logged control run (out/parD.pkl: alt 1000, $7680=-10, no button)."""
import random, pickle, sys
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehair')
def clamp(v, lo, hi): return lo if v <= lo else (hi if v >= hi else v)     # $34872: d0<=lo -> lo ; d0>=hi -> hi
def orig(alt, W, b, ground):
    v = clamp(W + b, -100, -10)           # $34586 sel 3 (apply, step 9)
    alt2 = alt + v; W2 = 2 * v            # $33cc2..$33cd2
    if alt2 < 0: return alt2, W2, 'swim'
    agl = alt2 - ground
    if agl - 50 < 0: return alt2, W2, 'foot'
    return alt2, W2, clamp(agl // 10, 0, 100)             # speed -> $6740 -> $344ac
def split(alt, W, b, ground):
    v = clamp(W + b, -100, -10)           # pass 1 only (HOLD=0)
    FA = alt + v; W2 = 2 * v; rem = 0
    tr = FA < 0 or (FA - ground - 50) < 0
    out = None
    for j in range(1, 6):
        S = rem + v; q = S // 5; rem = S - 5 * q; alt += q
        if j < 5:
            speed = None if tr else clamp((FA - ground) // 10, 0, 100)   # frozen speed on passes 1..4, no motion in a transition tick
        else:
            assert alt == FA
            agl = alt - ground
            out = (alt, W2, 'swim' if alt < 0 else 'foot' if agl - 50 < 0 else clamp(agl // 10, 0, 100))
            speed = out[2] if not isinstance(out[2], str) else None
        if j == 1: s1 = speed
    return out
random.seed(1); n = 0
for _ in range(200000):
    alt = random.randint(-30, 4000); W = random.choice([-200, -160, -80, -40, -20, random.randint(-300, 0)]); b = random.choice([0, 0, 16, -16, 32, -32, random.randint(-60, 60)])
    g = random.randint(-3000, 1500)
    assert orig(alt, W, b, g) == split(alt, W, b, g), (alt, W, b, g)
    n += 1
print('random tick cases equal:', n)
A, B = pickle.load(open('/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehair/out/parD.pkl', 'rb'))
import cmp
Ar = [cmp.row(m) for m in A]
alt, W = Ar[0]['alt'], Ar[0]['d80']
ok = 0
for k in range(1, 13):
    alt, W, r = orig(alt, W, 0, -2523)
    ok += (alt == Ar[k]['alt'] and W == Ar[k]['d80'])
print('logged control ticks reproduced (alt, $7680):', ok, 'of 12; tick 13 ->', orig(alt, W, 0, -2523)[2], 'observed type', Ar[13]['type'])
