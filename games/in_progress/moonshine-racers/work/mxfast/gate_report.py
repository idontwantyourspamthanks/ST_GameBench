"""Per-pass state gate report: python3 gate_report.py SCENE(start|drive|up) CAND(M|G) MHZ
A = stock 8 MHz, T = default set tick ON no extras 8 MHz, CAND = candidate with extras at MHZ.  Mask = cmpstate_int's documented display-scratch list (with TC_GEOM).
differing addresses CAND vs A are split into: also different in T vs A (patch sites / tb_car's kernel immediates: not caused by extras) and NEW ones (caused by the extras); NEW must be empty.
Also CAND vs T directly."""
import sys, json
sys.path.insert(0, '../tint')
scene, cand, mhz = sys.argv[1], sys.argv[2], sys.argv[3]
import importlib.util
spec = importlib.util.spec_from_file_location('cs', '../tint/cmpstate_int.py')
src = open('../tint/cmpstate_int.py').read().split("a, b = load(sys.argv[1])")[0]
ns = {}; exec(src, ns)
load, MASK = ns['load'], ns['MASK']
def diff(pa, pb):
    a, b = load(pa), load(pb); common = sorted(set(a) & set(b)); bad = {}; tot = 0; masked = 0
    for k in common:
        ma, mb = a[k][1], b[k][1]
        for ad in ma:
            if ad >= 0xb8000 or ad not in mb: continue
            tot += 1
            if ma[ad] != mb[ad]:
                if any(lo <= ad < hi for _, lo, hi in MASK): masked += 1; continue
                bad.setdefault(ad, []).append(k)
    return common, tot, masked, bad
def runs(l):
    r = []
    for a in sorted(l):
        if r and a - r[-1][1] <= 1: r[-1][1] = a
        else: r.append([a, a])
    return ' '.join(f'{x:x}-{y:x}' for x, y in r)
R = 'res/'
A = f'{R}st_{scene}_A8.json'; C = f'{R}st_{scene}_{cand}{mhz}.json'; T = f'{R}st_{scene}_T8.json'
common, tot, masked, bad = diff(A, C)
print(f'{scene} A8 vs {cand}{mhz}: common passes {len(common)} (keys {common[0]}..{common[-1]}), {tot} bytes compared, masked differing bytes {masked}, differing addresses {len(bad)}: {runs(bad)}')
try:
    c2, t2, m2, base = diff(A, T)
    new = set(bad) - set(base)
    print(f'   A8 vs T8 (tick ON, no extras): differing addresses {len(base)}: {runs(base)}')
    print(f'   differing addresses in {cand}{mhz} that are NOT already different in T8: {len(new)} {runs(new)}')
    c3, t3, m3, dt = diff(T, C)
    print(f'   T8 vs {cand}{mhz}: common {len(c3)} passes, {t3} bytes, differing addresses {len(dt)} {runs(dt)}')
except FileNotFoundError:
    print('   (T8 reference not run yet)')
