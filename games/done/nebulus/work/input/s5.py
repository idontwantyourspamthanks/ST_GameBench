"""K1: stand shots (right, left after a turn, right after turning back); K2: shootable block; K3: jump into a wall. usage: s5.py <scenario> <tag> <live> [noen]"""
from scripted2 import *
import sys
REF = parse_flips(open('sc/s1/log.txt').read())
def timeline(points, end):
    """points {loop: value} -> per-loop value list [0..end]"""
    v = []; cur = 0
    for j in range(end + 1):
        cur = points.get(j, cur); v.append(cur)
    return v
def k1():
    p = {}
    for a in (18, 40, 85, 125):
        p[a] = 0x80; p[a + 3] = 0x00
    p[58] = 0x04; p[60] = 0x00           # Left tap: turn to face left
    p[105] = 0x08; p[107] = 0x00         # Right tap: turn back
    return p, 150
def k2():
    p = {}
    for a in (20, 45, 70):
        p[a] = 0x80; p[a + 3] = 0x00
    return p, 110
def k3():
    p = {j: 0x08 for j in range(45, 46)}           # Right held
    p[55] = 0x88; p[59] = 0x08                      # fire+right 4 loops at x~11-12: jump toward the (poked) solid pillar at x 16..23
    p[75] = 0x00; p[80] = 0x08; p[84] = 0x88; p[88] = 0x08   # again from the pillar's foot
    p[110] = 0x00
    return p, 115
SC = {'k1': k1, 'k2': k2, 'k3': k3}
if __name__ == '__main__':
    scen, tag, live = sys.argv[1], sys.argv[2], sys.argv[3]
    noen = len(sys.argv) > 4 and sys.argv[4] == 'noen'
    p, end = SC[scen]()
    tl = timeline(p, end)
    caps_loops = set()
    if noen:
        caps_loops = set(range(16, 46)) | set(range(56, 76)) | set(range(84, 96)) if scen == 'k1' else set(range(18, 60)) if scen == 'k2' else set()
    spec = {j: tl[j] for j in range(end + 1) if (j in p or j in caps_loops)}
    ev = build_script(REF, spec)
    # map cap loops -> event indexes after dedupe (event i has loop = key order)
    keys = sorted(spec)
    # rebuild mapping: events are in order of spec keys, deduped when triples coincide
    seen = []; idx_of = {}
    i0 = next(i for i, f in enumerate(REF) if f['timer'] != (32, 0, 0))
    last = None; n = -1
    for j in keys:
        i = i0 + j
        cnt = {}
        for f in REF: cnt[f['timer']] = cnt.get(f['timer'], 0) + 1
        while cnt[REF[i]['timer']] != 1: i += 1
        if REF[i]['timer'] != last: n += 1; last = REF[i]['timer']
        idx_of[j] = n
    caps = [idx_of[j] for j in sorted(caps_loops) if j in idx_of]
    extra = []
    if noen: extra.append('w $3792c $4e $75')
    if scen == 'k2': extra += ['w $328f2 $82 $82', 'w $329f2 $82 $82']
    if scen == 'k3': extra += ['w $329f2 $81 $81 $81']
    fl, txt = run(tag, ev, caps=caps, live=(LIVE[live] + extra), tail_s=3.0, max_wait=70)
    json.dump({'caps_loops': sorted(caps_loops), 'idx_of': {str(k): v for k, v in idx_of.items()}}, open(f'sc/{tag}.meta', 'w'))
    open(f'sc/{tag}.tok', 'w').write(' '.join(tokens(txt)))
    print(tag, len(fl))
