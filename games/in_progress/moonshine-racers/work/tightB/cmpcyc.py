"""Matched-pass cycle comparison: python3 cmpcyc.py REF.json NEW.json [...]  (rows keyed by $100e; same snapshot = same game state per pass)"""
import json, sys, statistics
def load(p): return {x['p']: x for x in json.load(open(p))}
ref = load(sys.argv[1])
for p in sys.argv[2:]:
    n = load(p); common = sorted(set(ref) & set(n))
    for nm, sel in (('no speech', [k for k in common if not ref[k]['speech']]), ('speech', [k for k in common if ref[k]['speech']])):
        if not sel: continue
        d = [n[k]['work'] - ref[k]['work'] for k in sel]
        print(f"{p.split('/')[-1][:48]:48s} {nm:10s} n {len(sel):3d} ref {statistics.mean(ref[k]['work'] for k in sel):9.0f} new {statistics.mean(n[k]['work'] for k in sel):9.0f} delta {statistics.mean(d):8.0f} ({statistics.mean(d)/160256:+.3f} VBL) min {min(d)} max {max(d)}")
