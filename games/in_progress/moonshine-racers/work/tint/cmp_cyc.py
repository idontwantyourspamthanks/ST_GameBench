"""python3 cmp_cyc.py A.json B.json : matched-pass (same $100e) comparison, speech / no speech; also whole-window means"""
import json, sys, statistics as st
def LD(f):
    d = json.load(open(f)); return d['rows'] if isinstance(d, dict) else d
a = {r['p']: r for r in LD(sys.argv[1])}; b = {r['p']: r for r in LD(sys.argv[2])}
def m(rows): return round(st.mean(rows)) if rows else None
for nm in ('no speech', 'speech'):
    sp = nm == 'speech'
    ks = [k for k in a if k in b and a[k]['speech'] == sp and b[k]['speech'] == sp]
    d = [b[k]['work'] - a[k]['work'] for k in ks]
    if ks: print(f"{sys.argv[1].split('/')[-1]} -> {sys.argv[2].split('/')[-1]} {nm:10s} matched n {len(ks):3d} ref {m([a[k]['work'] for k in ks])} new {m([b[k]['work'] for k in ks])} delta {m(d)} ({m(d)/160256:+.3f} VBL)")
for f in sys.argv[1:3]:
    rows = LD(f)
    for nm, sp in (('no speech', False), ('speech', True)):
        w = [r['work'] for r in rows if r['speech'] == sp]
        if w: print(f"   {f.split('/')[-1]:34s} {nm:10s} n {len(w):3d} mean {m(w)} = {st.mean(w)/160256:.3f} VBL  min {min(w)} max {max(w)}")

ks = sorted(set(a) & set(b))
for lo in (0, 100, 250):
    sel = [k for k in ks if k >= ks[0] + lo]
    if sel:
        d = [b[k]['work'] - a[k]['work'] for k in sel]
        print(f"   all matched passes from key +{lo}: n {len(sel)} mean {m([a[k]['work'] for k in sel])} -> {m([b[k]['work'] for k in sel])} delta {m(d)} ({m(d)/160256:+.3f} VBL)")
