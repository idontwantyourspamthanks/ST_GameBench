import re, sys, collections
def frames(path):
    cur = None; frames = []; st = {}
    for ln in open(path, errors='replace'):
        m = re.match(r"write col addr=ff82([0-9a-f]{2}) col=([0-9a-f]+) video_cyc_w=\d+ line_cyc_w=(\d+) @ nHBL=(\d+)/video_hbl_w=(\d+) pc=([0-9a-f]+)", ln)
        if not m: continue
        reg = int(m.group(1), 16); col = int(m.group(2), 16); lc = int(m.group(3)); hbl = int(m.group(5)); pc = int(m.group(6), 16)
        if pc in (0xd544,) and reg == 0x40:   # first palette write of the VBL palette-A copy = a new frame
            cur = {'ch15': [], 'palB': [], 'A': {}}; frames.append(cur); st = {}
        if cur is None: continue
        if reg == 0x5e:
            if st.get(0x5e) != col: cur['ch15'].append((hbl, col, lc // 16))
            st[0x5e] = col
        elif reg in (0x42, 0x44, 0x46, 0x48, 0x4a, 0x4c, 0x4e, 0x50, 0x52, 0x54, 0x56, 0x58, 0x5a):
            if pc in (0xd6c0, 0xd6c4, 0xd6c8, 0xd6cc, 0xd6d0, 0xd6d4, 0xd6d8, 0xd63a, 0xd63e, 0xd642, 0xd646, 0xd64a, 0xd64e, 0xd652): cur['palB'].append((hbl, reg, col, lc // 16))
    return frames
def sig(f): return (tuple((h, c) for h, c, l in f['ch15']), tuple(sorted(set(h for h, r, c, l in f['palB']))))
a = frames(sys.argv[1]); b = frames(sys.argv[2])
sa = collections.Counter(sig(f) for f in a[1:-1]); sb = collections.Counter(sig(f) for f in b[1:-1])
print(sys.argv[1], 'frames', len(a), 'distinct colour15-change signatures', len(sa)); print(sys.argv[2], 'frames', len(b), 'distinct', len(sb))
print('signature sets equal:', set(sa) == set(sb))
for s in sa: print('  ref', s, 'x', sa[s], '| cand x', sb.get(s))
# timing within the line of the effective colour-15 changes
def lcs(fr): 
    d = collections.defaultdict(list)
    for f in fr[1:-1]:
        for h, c, l in f['ch15']: d[(h, c)].append(l)
    return d
la, lb = lcs(a), lcs(b)
for k in sorted(la): print('  change line', k[0], 'col %03x' % k[1], 'line-cycle/16 ref', sorted(set(la[k])), 'cand', sorted(set(lb.get(k, []))))
pa = collections.Counter((h, l) for f in a[1:-1] for h, r, c, l in f['palB']); pb = collections.Counter((h, l) for f in b[1:-1] for h, r, c, l in f['palB'])
print('palette-B write lines/cycle buckets ref', sorted(pa)[:20], 'cand', sorted(pb)[:20])
