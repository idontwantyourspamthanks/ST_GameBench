"""Lever D analysis of cap.py pickles.  python3 ana.py PKL [PKL ...]"""
import sys, pickle, statistics as st
import numpy as np
SKIP_TEST = 60     # assumed cycles per row for 'compare record with the stored one + advance a0' in a skipping rd_draw (cmpm.l x2 = 40, lea 160 = 8, loop 10)
def rows_of(f): return len(f['recs'])
def analyse_pair(g, f):
    """g = frame whose final image the destination holds; f = frame to draw.  Returns dict of per-class counts and cycles."""
    n = rows_of(f); ng = rows_of(g)
    gi = np.frombuffer(g['final'], np.uint8).reshape(200, 160)
    fx = np.frombuffer(f['exit'], np.uint8).reshape(200, 160)
    gx = np.frombuffer(g['exit'], np.uint8).reshape(200, 160)
    rc = f['rowcyc']
    r = dict(n=n, a=0, b=0, ab=0, a_only_over=0, b_only=0, Fonly=0, cyc_total=sum(rc), cyc_b=0, cyc_ab=0, cyc_a=0, rowsb=[], rowsab=[])
    for k in range(n):
        row = 199 - k
        a = k < ng and g['recs'][k] == f['recs'][k]
        b = bool((gi[row] == fx[row]).all())
        r['a'] += a; r['b'] += b; r['ab'] += (a and b)
        r['a_only_over'] += (a and not b); r['b_only'] += (b and not a)
        if k < ng and not a and g['recs'][k][:3] == f['recs'][k][:3]: r['Fonly'] += 1
        if a: r['cyc_a'] += rc[k]
        if b: r['cyc_b'] += rc[k]; r['rowsb'].append(k)
        if a and b: r['cyc_ab'] += rc[k]; r['rowsab'].append(k)
    return r
def summarize(name, pairs):
    if not pairs: return
    n = sum(p['n'] for p in pairs)
    def pct(key): return 100.0 * sum(p[key] for p in pairs) / n
    m = lambda key: st.mean(p[key] for p in pairs)
    print(f"{name:34s} frames {len(pairs):4d} rows/frame {n/len(pairs):5.1f} | a rec= {pct('a'):5.1f}% b pix= {pct('b'):5.1f}% a&b {pct('ab'):5.1f}% a&!b(overpaint) {pct('a_only_over'):4.1f}% b&!a {pct('b_only'):4.1f}% Fonly {pct('Fonly'):4.1f}% | rd_draw {m('cyc_total'):7.0f}  skip(b) {m('cyc_b'):7.0f}  skip(a&b) {m('cyc_ab'):7.0f}  skip(a) {m('cyc_a'):7.0f}  net(a&b) {m('cyc_ab')-SKIP_TEST*m('n'):7.0f}")
def load(p):
    d = pickle.load(open(p, 'rb')); F = d['frames']; nx = d['nx']; warm = d['warm']
    # frame ordinal in pass
    seen = {}
    for f in F:
        if f['rowcyc'] is not None: f['recs'] = f['recs'][:len(f['rowcyc'])]   # rd_draw stops at the A:B == 0 terminator; later stream words are leftovers
        j = seen.get(f['pass_'], 0); f['j'] = j; seen[f['pass_']] = j + 1
        f['t'] = f['pass_'] + j / (nx + 1.0)
        f['kind'] = 'main' if j == 0 else 'extra'
    return F, nx, warm
if __name__ == '__main__':
    for p in sys.argv[1:]:
        F, nx, warm = load(p)
        print('==', p.split('/')[-1], 'nx', nx)
        ok = [f for f in F if f['rowcyc'] is not None]
        byidx = {f['idx']: f for f in F}
        for kind in ('main', 'extra'):
            pairs = []
            for f in ok:
                if f['kind'] != kind: continue
                g = byidx.get(f['idx'] - 2)
                if g is None or 'final' not in g or g['buf'] != f['buf'] or g['pass_'] < 1: continue
                pairs.append(analyse_pair(g, f))
            summarize(f'actual dest (frame i-2) {kind}', pairs)
        # by pose gap (any earlier frame g, same road model) for extras
        gaps = {}
        for f in ok:
            if f['kind'] != 'extra': continue
            for d in range(1, 3 * (nx + 1) + 1):
                g = byidx.get(f['idx'] - d)
                if g is None or 'final' not in g or g['pass_'] < 1: continue
                gap = round(f['t'] - g['t'], 3)
                gaps.setdefault(gap, []).append(analyse_pair(g, f))
        for gap in sorted(gaps): summarize(f'  extra vs frame {gap:5.2f} ticks older', gaps[gap])
