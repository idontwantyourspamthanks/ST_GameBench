"""Extra vs its own main frame (geometry reuse question) and slot-level identity.  python3 ana2.py PKL..."""
import sys, numpy as np, statistics as st
from ana import load, analyse_pair
def edge_stats(m, f):
    n = min(len(m['recs']), len(f['recs']))
    eq = fo = 0; dmax = []
    for k in range(n):
        a, b = m['recs'][k], f['recs'][k]
        if a == b: eq += 1; continue
        if a[1] == b[1] and a[2] == b[2] and a[0] == b[0]: fo += 1; continue
        sa = lambda x: x - 65536 if x > 32767 else x
        dmax.append(max(abs(sa(a[1]) - sa(b[1])), abs(sa(a[2]) - sa(b[2]))))
    return n, eq, fo, dmax, len(m['recs']), len(f['recs'])
def slot_stats(g, f):
    """for road rows of f: share of 8-byte slots of g's final image equal to f's pure road (all rows / rows with equal record)."""
    gi = np.frombuffer(g['final'], np.uint8).reshape(200, 20, 8); fx = np.frombuffer(f['exit'], np.uint8).reshape(200, 20, 8)
    n = len(f['recs']); tot = eq = 0; ra_tot = ra_eq = 0; dirty = []
    for k in range(n):
        row = 199 - k
        e = (gi[row] == fx[row]).all(axis=1)
        tot += 20; eq += int(e.sum())
        if k < len(g['recs']) and g['recs'][k] == f['recs'][k]:
            ra_tot += 20; ra_eq += int(e.sum()); dirty.append(20 - int(e.sum()))
    return tot, eq, ra_tot, ra_eq, dirty
for p in sys.argv[1:]:
    F, nx, warm = load(p); by = {f['idx']: f for f in F}
    print('==', p.split('/')[-1], 'nx', nx)
    mains = {f['pass_']: f for f in F if f['kind'] == 'main'}
    acc = {}
    for f in F:
        if f['kind'] != 'extra' or f['rowcyc'] is None: continue
        m = mains[f['pass_']]
        n, eq, fo, dm, nm, nf = edge_stats(m, f)
        d = acc.setdefault(f['j'], dict(n=0, eq=0, fo=0, dm=[], cnt=0, geom=[], draw=[], nd=[]))
        d['n'] += n; d['eq'] += eq; d['fo'] += fo; d['dm'] += dm; d['cnt'] += 1; d['geom'].append(f['geom']); d['draw'].append(f['cyc']); d['nd'].append(nf - nm)
    for j in sorted(acc):
        d = acc[j]; dm = np.array(d['dm']) if d['dm'] else np.array([0])
        print(f"  extra j={j} (f={j}/{nx+1}) vs own main: rows {d['n']/d['cnt']:.1f}/frame equal {100*d['eq']/d['n']:.1f}% F-only {100*d['fo']/d['n']:.1f}% edge-moved {100*len(d['dm'])/d['n']:.1f}% | edge shift px of moved rows: median {np.median(dm):.0f} mean {dm.mean():.1f} p90 {np.percentile(dm,90):.0f} max {dm.max()} | <=1px {100*(dm<=1).mean():.0f}% <=2px {100*(dm<=2).mean():.0f}% <=4px {100*(dm<=4).mean():.0f}% | row count diff vs main mean {st.mean(d['nd']):.2f} | rd_geom {st.mean(d['geom']):.0f} rd_draw {st.mean(d['draw']):.0f} cyc")
    # slot level, actual dest (i-2)
    T = E = RT = RE = 0; dirt = []
    for f in F:
        if f['kind'] != 'extra' or f['rowcyc'] is None: continue
        g = by.get(f['idx'] - 2)
        if g is None or 'final' not in g or g['buf'] != f['buf'] or g['pass_'] < 1: continue
        t, e, rt, re, d = slot_stats(g, f); T += t; E += e; RT += rt; RE += re; dirt += d
    dirt = np.array(dirt) if dirt else np.array([0])
    print(f"  slot-level, extra vs actual dest: all road slots equal {100*E/T:.1f}% | in rows with equal record: slots equal {100*RE/max(RT,1):.1f}%, rows with equal rec: {len(dirt)/(T/20):.3f} of rows, of those 0 dirty slots {100*(dirt==0).mean():.0f}%, mean dirty slots {dirt.mean():.1f}/20, p90 {np.percentile(dirt,90):.0f}")
