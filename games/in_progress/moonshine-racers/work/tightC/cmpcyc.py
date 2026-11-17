import json, sys, statistics
a = {r['p']: r for r in json.load(open(sys.argv[1]))}; b = {r['p']: r for r in json.load(open(sys.argv[2]))}
c = sorted(set(a) & set(b))
d = [a[p]['work'] - b[p]['work'] for p in c]
sp = [a[p]['work'] - b[p]['work'] for p in c if not a[p]['speech']]
print(f'{sys.argv[1]} -> {sys.argv[2]}: common passes {len(c)} mean base {statistics.mean(a[p]["work"] for p in c):.0f} mean saved {statistics.mean(d):.0f} (min {min(d)} max {max(d)})')
