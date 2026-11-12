import re, glob, sys
rows = []
for f in sorted(glob.glob('logs/*.log')):
    t = open(f).read()
    m = re.search(r'^config (\S+) (\w) (\w+)', t, re.M)
    if not m or 'SUMMARY' not in t: continue
    w = {int(k): (int(x), int(z), int(s), int(v)) for k, v, x, z, s in re.findall(r'^walk(\d+)\s+vbl=(\d+) x=(\d+) z=(\d+) speed=(\d+)', t, re.M)}
    if 0 not in w or 7 not in w: continue
    d = re.search(r'idle\s+vbl=\d+ .*', t)
    rows.append((f.split('/')[-1][:-4], m.group(1).split('/')[-1], m.group(2), m.group(3), w[0][1], w[7][1], w[7][1]-w[0][1], max(v[2] for v in w.values()), w[7][3]-w[0][3], 'YES' if w[7][1]-w[0][1] > 50 else 'NO', 'defaults' if 'FWD' in t and False else ''))
print('log                  build  mode machine   z(walk0) z(walk7) dz    maxspeed dVBL moves')
for r in rows: print('%-20s %-6s %-4s %-8s %7d %7d %6d %6d %5d  %s' % r[:10])
