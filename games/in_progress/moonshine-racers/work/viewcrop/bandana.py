import pickle, sys, numpy as np, collections
res = pickle.load(open(sys.argv[1], 'rb'))
NAMES = {0xf9fa:'logic f9fa',0xfb96:'logic',0xfc2a:'logic',0xfc80:'logic',0x11396:'logic', 0xfe50:'ring fe50', 0xff76:'ring ff76', 0x1003c:'ring 1003c', 0x17c24:'span clear', 0x100b4:'road geometry', 0xb8200:'road draw', 0x10a5e:'raster table', 0x10a98:'horizon scroll', 0xe218:'e218', 0xe2e8:'obj distance', 0x1182e:'AI cars', 0x11a3c:'11a3c', 0xe316:'obj project', 0xdd50:'clouds', 0x18318:'horizon draw', 0xb8300:'objects/sprites', 0xef7a:'HUD stage', 0x18888:'18888', 0x18c86:'collide', 0x18f0e:'debris'}
sites = res[0]['sites']
def tag(i): 
    t = sites[i][1] if i >= 0 else 0
    return NAMES.get(t, '%x' % t)
# per stage per row: pending-to-next-write rule within a stage
S = collections.defaultdict(lambda: np.zeros(201))   # stage name -> cycles by row (index 200 = no screen write)
tot = 0
for r in res:
    pend = 0; cur = None
    for pc, c, row, st in zip(r['pcs'], r['cy'], r['rows'], r['st']):
        name = tag(st) if st >= 0 else 'head'
        if name != cur:
            if cur is not None and pend: S[cur][200] += pend / len(res)
            pend = 0; cur = name
        pend += int(c)
        if row >= 0:
            S[name][row] += pend / len(res); pend = 0
    if pend: S[cur][200] += pend / len(res)
    tot += r['cyc']
print('mean pass cycles', tot / len(res), 'passes', len(res))
print('%-18s %8s | %8s' % ('stage', 'total', 'no-row'))
rows_all = np.zeros(201)
for k, v in sorted(S.items(), key=lambda kv: -kv[1].sum()):
    if v.sum() < 500: continue
    print('%-18s %8.0f | %8.0f   rows written %d' % (k, v.sum(), v[200], int((v[:200] > 0).sum())))
    rows_all += v
print('sum', rows_all.sum())
bands = [(0, 16, 'HUD strip 0-15'), (16, 65, 'sky 16-64')] + [(a, a + 10, '') for a in range(65, 125, 10)] + [(125, 200, '')]
def band(lo, hi, names=None):
    out = 0
    for k, v in S.items():
        if names and k not in names: continue
        out += v[lo:hi].sum()
    return out
print('\nCycles per 10-row band (all stages / road draw / horizon draw / objects / HUD / other with rows):')
edges = [0, 16, 32, 48, 65, 75, 85, 95, 105, 115, 125, 135, 145, 155, 165, 175, 185, 195, 200]
print('rows       total   road   horiz  objects  HUD   other   /row')
for a, b in zip(edges[:-1], edges[1:]):
    tt = band(a, b); rd = band(a, b, ['road draw']); hz = band(a, b, ['horizon draw']); ob = band(a, b, ['objects/sprites']); hu = band(a, b, ['HUD stage'])
    print(f'{a:3d}-{b-1:3d} {tt:9.0f} {rd:7.0f} {hz:7.0f} {ob:7.0f} {hu:6.0f} {tt-rd-hz-ob-hu:7.0f}  {tt/(b-a):6.0f}')
