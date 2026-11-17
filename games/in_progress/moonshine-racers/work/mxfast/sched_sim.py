"""Packing simulation of the extra-frame scheduler with the measured per-tick data of MSRTripleStudy (8 MHz STE, 1,110 racing ticks).
main work m_i = main_end (cycles from the tick start to the main flip), extra cost D = measured (flip entry -> end of restoreundo); policies: start an extra iff predicted end <= next grid + slip."""
import json, random, statistics as st
V = 160256; TICK = 5 * V
T = json.load(open('../triple/res/lat2_X8_ticks.json'))
T = [t for t in T if t['pass'] >= 130 or t['pass'] < 1000]
main = [t['main_end'] for t in T if t['main_end'] and t['main_end'] < 3 * TICK]
Ds = []
for t in T:
    if t['nextra'] == 1 and t['ex'] and t['ex'][0]['t5'] and t['t4']:
        e0 = t['ex'][0]
        D = e0['t5'] - t['t4'][0] + 0.24 * V  # flip-to-flip incl. saveundo + the restore after the flip
        if 1.5 * V < D < 4.5 * V: Ds.append(D)
print('main ticks', len(main), 'mean %.3f VBL' % (st.mean(main) / V), 'extra cost samples', len(Ds), 'mean %.3f VBL' % (st.mean(Ds) / V))
def sim(slip, dred, est='mean', n=20000, seed=1, maxlag=2):
    r = random.Random(seed); L = 0; ex = 0; late = []; flipdelay = []
    Dm = st.mean(Ds) - dred
    for i in range(n):
        m = r.choice(main); D = r.choice(Ds) - dred
        tnow = L + m                      # relative to this tick's grid start
        flipdelay.append(L)
        if tnow + Dm <= TICK + slip:
            tend = tnow + D; ex += 1
        else: tend = tnow
        L = max(0, tend - TICK)
        if L > maxlag * TICK: L = 0
    return ex / n, st.mean(flipdelay) / V, sorted(flipdelay)[int(0.9 * n)] / V
for dred in (0, 0.23 * V, 0.5 * V):
    print('D reduction %.2f VBL' % (dred / V))
    for slip in (0, 0.5 * V, 1 * V, 1.5 * V, 2 * V, 3 * V):
        sh, mean, p90 = sim(slip, dred)
        print('   slip %.1f VBL: extras/tick %.3f   main-frame lateness mean %.2f p90 %.2f VBL' % (slip / V, sh, mean, p90))

print('\n--- coarse (VBL-floor start, the current rule) vs fine start time, D reduction 0 / 0.43 VBL, mean D estimate')
def sim2(slip, dred, coarse, n=30000, seed=2):
    r = random.Random(seed); L = 0; ex = 0; fd = []
    Dm = st.mean(Ds) - dred
    for i in range(n):
        m = r.choice(main); D = r.choice(Ds) - dred
        tnow = L + m
        t_dec = (int(tnow // V)) * V if coarse else tnow
        fd.append(L)
        if t_dec + Dm <= TICK + slip: tend = tnow + D; ex += 1
        else: tend = tnow
        L = max(0, tend - TICK)
        if L > 2 * TICK: L = 0
    return ex / n, st.mean(fd) / V, sorted(fd)[int(.9 * n)] / V, sorted(fd)[int(.99 * n)] / V
for dred in (0, 0.43 * V):
    print('D reduction %.2f VBL' % (dred / V))
    for coarse in (True, False):
        for slip in (-0.5 * V, 0, 0.25 * V, 0.5 * V, 0.75 * V, 1.0 * V):
            sh, mean, p90, p99 = sim2(slip, dred, coarse)
            print('   %s slip %+.2f VBL: extras/tick %.3f  lateness mean %.2f p90 %.2f p99 %.2f VBL' % ('coarse' if coarse else 'fine  ', slip / V, sh, mean, p90, p99))
