import sys, json, statistics as st
sys.path.insert(0,'work/triple')
from parse import *
from collections import Counter
path = sys.argv[1]
ev = parse(path)
V = CYC
# tags: 1 loop top, 2 7a88, 3 newsync entry (main end), 4 any flip, 5 extra flip call, 6 extra start, 7 wait loop, 8 first write, 9 main guard, 10 latch (absent), 17 tick end
T = lambda e: e[1]*V + e[2]
ticks = []  # list of dicts, split at tag 17 (tick end = sleep exit)
cur = None
prev_end = None
for e in ev:
    t = T(e)
    if e[0] == 17:
        if cur is not None:
            cur['end'] = t; cur['mem'] = e[3]; ticks.append(cur)
        cur = dict(start=t, ev=[])
        continue
    if cur is not None:
        cur['ev'].append((e[0], t))
res = []
for tk in ticks:
    ev_ = tk['ev']; d = {}
    t1 = [t for g, t in ev_ if g == 1]; t3 = [t for g, t in ev_ if g == 3]
    if not t1 or not t3: continue
    d['top'] = t1[0] - tk['start']; d['main_end'] = t3[0] - tk['start']
    # main pre/wait
    t9 = [t for g, t in ev_ if g == 9]; t8 = [t for g, t in ev_ if g == 8]
    t2 = [t for g, t in ev_ if g == 2]
    d['t7a88'] = t2[0] - tk['start'] if t2 else None
    d['main_guard'] = t9[0] - tk['start'] if t9 else None
    d['main_first'] = t8[0] - tk['start'] if t8 else None
    # extras
    ex = []
    t6 = [t for g, t in ev_ if g == 6]
    for s in t6:
        # wait loop hits after s until the next 8
        after = [(g, t) for g, t in ev_ if t >= s]
        w = [t for g, t in after if g == 7]
        f8 = [t for g, t in after if g == 8]
        f5 = [t for g, t in after if g == 5]
        if not (w and f8 and f5): continue
        ex.append(dict(start=s - tk['start'], w0=w[0] - tk['start'], w1=w[-1] - tk['start'] if True else 0, nw=sum(1 for t in w if t < f8[0]), first=f8[0] - tk['start'], flip=f5[0] - tk['start']))
    d['ex'] = ex; d['len'] = tk['end'] - tk['start']
    d['nextra'] = (tk['mem'].get(0xb8f32, 0) << 8) | tk['mem'].get(0xb8f33, 0)
    d['pass'] = (tk['mem'].get(0x100e, 0) << 8) | tk['mem'].get(0x100f, 0)
    d['dext'] = (tk['mem'].get(0xb8f24, 0) << 8) | tk['mem'].get(0xb8f25, 0)
    d['speech'] = tk['mem'].get(0x11ab, 0) != 0
    res.append(d)
json.dump(res, open(path.replace('.json.log', '_ticks.json'), 'w'))
print('ticks', len(res))
lens = Counter(round(d['len']/V, 2) for d in res)
print('tick length VBL', sorted(lens.items())[:10])
