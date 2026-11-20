"""Policy simulation 2: does a sub-VBL clock + per-tick prediction D^ = a + b*m (m = this tick's main pass length) beat the VBL-coarse rule with the mean D?"""
import json, random, statistics as st
V = 160256; TICK = 5 * V
T = json.load(open('../triple/res/lat2_X8_ticks.json'))
pairs = []; mains = []
for t in T:
    if t['main_end'] and t['main_end'] < 4 * V: mains.append(t['main_end'])
    if t['nextra'] >= 1 and t['ex'] and t['ex'][0]['t5'] and t['t4'] and t['main_end']:
        D = t['ex'][0]['t5'] - t['t4'][0] + 0.24 * V
        if 1.5 * V < D < 4.5 * V and t['main_end'] < 4 * V: pairs.append((t['main_end'], D))
xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
mx, my = st.mean(xs), st.mean(ys); b = sum((x - mx) * (y - my) for x, y in pairs) / sum((x - mx) ** 2 for x in xs); a = my - b * mx
res = [y - (a + b * x) for x, y in pairs]; sd = st.pstdev(res)
print('regression D = %.2f VBL + %.2f * m ; residual sd %.3f VBL ; D sd %.3f' % (a / V, b, sd / V, st.pstdev(ys) / V))
def sim(policy, slip, dred, n=40000, seed=3, mnoise=0.0):
    r = random.Random(seed); L = 0; ex = 0; fd = []
    for i in range(n):
        m = r.choice(mains); D = a + b * m + r.gauss(0, sd) - dred
        tnow = L + m; fd.append(L)
        if policy == 'coarse': ok = (int(tnow // V)) * V + (my - dred) <= TICK + slip
        elif policy == 'fine_mean': ok = tnow + (my - dred) <= TICK + slip
        else:
            mhat = m + r.gauss(0, mnoise * V); ok = tnow + (a + b * mhat - dred) <= TICK + slip
        if ok: tend = tnow + D; ex += 1
        else: tend = tnow
        L = max(0, tend - TICK)
        if L > 2 * TICK: L = 0
    fd.sort(); return ex / n, st.mean(fd) / V, fd[int(.9 * n)] / V, fd[int(.99 * n)] / V
for dred in (0.43 * V,):
    print('D reduction %.2f VBL' % (dred / V))
    for pol, mn in (('coarse', 0), ('fine_mean', 0), ('fine_pred', 0.0), ('fine_pred', 0.1)):
        for slip in (-0.25 * V, 0, 0.25 * V, 0.5 * V, 0.75 * V, 1.0 * V, 1.5 * V):
            sh, mean, p90, p99 = sim(pol, slip, dred, mnoise=mn)
            print(f'   {pol:9s}{"(noise %.1f)" % mn if pol == "fine_pred" else "":12s} slip {slip/V:+.2f}: extras/tick {sh:.3f} lateness mean {mean:.2f} p90 {p90:.2f} p99 {p99:.2f}')
