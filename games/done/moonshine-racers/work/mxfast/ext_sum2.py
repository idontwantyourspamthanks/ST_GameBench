"""Racing-phase summary of steer_mf.py mode=pass records: python3 ext_sum2.py a.json b.json ...
racing = records after the restart (pass key wraps) with $100e >= 130.  extras of pass i are visible in record i+1 (NEXTRA); tick length = VBL difference between consecutive pass starts."""
import json, sys, collections, statistics as st
for f in sys.argv[1:]:
    d = json.load(open(f)); R = d['rows']
    rs = [i for i, (a, b) in enumerate(zip(R, R[1:])) if b['p'] + 20 < a['p']]
    i0 = (rs[-1] + 1) if rs else 0
    per = []
    for a, b in zip(R[i0:], R[i0 + 1:]):
        if b['p'] == a['p'] + 1 and a['p'] >= 130: per.append((a['p'], b['nextra'], b['vbl'] - a['vbl']))
    n = len(per)
    h = collections.Counter(e for _, e, _ in per)
    tl = [t for _, _, t in per]
    late = sum(1 for t in tl if t > 5); vlate = sum(1 for t in tl if t >= 7)
    fr = (R[-1]['frames'] - R[i0]['frames']); dv = R[-1]['vbl'] - R[i0]['vbl']; npass = len(R) - 1 - i0
    print(f"{f.split('/')[-1]:22s} racing ticks {n:4d}  extras/tick hist {dict(sorted(h.items()))}  share>=1 {100*(n-h.get(0,0))/n:5.1f} %  mean {sum(e for _,e,_ in per)/n:.3f}  tick len mean {st.mean(tl):.3f} VBL  >5: {100*late/n:.1f} %  >=7: {100*vlate/n:.1f} %  passes/s {npass*50/dv:.3f} displayed fps {(npass+fr)*50/dv:.2f}")
