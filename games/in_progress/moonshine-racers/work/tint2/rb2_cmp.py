"""python3 rb2_cmp.py REF.txt CAND.txt ... : palette-write traces of rastercheck.py (video_color).
Per file: frames (VBL palette-A copy at pc $d544 starts a frame), distinct signatures = (effective colour-15 changes (line, colour), lines of the palette-B switch writes),
for every (line, colour) change the exact line-cycle (0-511) of the write: count, min, median, p99, max; the same for the palette-B switch writes by line.
Then, against the first file: signature sets (candidate subset of / equal to the reference), and the largest line-cycle per change vs the reference."""
import re, sys, collections, statistics
def frames(path):
    cur = None; fr = []; st = {}
    for ln in open(path, errors="replace"):
        m = re.match(r"write col addr=ff82([0-9a-f]{2}) col=([0-9a-f]+) video_cyc_w=\d+ line_cyc_w=(\d+) @ nHBL=(\d+)/video_hbl_w=(\d+) pc=([0-9a-f]+)", ln)
        if not m: continue
        reg = int(m.group(1), 16); col = int(m.group(2), 16); lc = int(m.group(3)); hbl = int(m.group(5)); pc = int(m.group(6), 16)
        if pc == 0xd544 and reg == 0x40:
            cur = {"ch15": [], "palB": []}; fr.append(cur); st = {}
        if cur is None: continue
        if reg == 0x5e:
            if st.get(0x5e) != col: cur["ch15"].append((hbl, col, lc))
            st[0x5e] = col
        elif reg in (0x42, 0x44, 0x46, 0x48, 0x4a, 0x4c, 0x4e, 0x50, 0x52, 0x54, 0x56, 0x58, 0x5a):
            if pc in (0xd6c0, 0xd6c4, 0xd6c8, 0xd6cc, 0xd6d0, 0xd6d4, 0xd6d8, 0xd63a, 0xd63e, 0xd642, 0xd646, 0xd64a, 0xd64e, 0xd652): cur["palB"].append((hbl, reg, col, lc))
    return fr[1:-1]
def sig(f): return (tuple((h, c) for h, c, l in f["ch15"]), tuple(sorted(set(h for h, r, c, l in f["palB"]))))
def pct(v, p): v = sorted(v); return v[min(len(v) - 1, int(len(v) * p))]
res = []
for path in sys.argv[1:]:
    fr = frames(path); sg = collections.Counter(sig(f) for f in fr)
    ch = collections.defaultdict(list); pb = collections.defaultdict(list)
    for f in fr:
        for h, c, l in f["ch15"]: ch[(h, c)].append(l)
        for h, r, c, l in f["palB"]: pb[h].append(l)
    res.append((path, fr, sg, ch, pb))
    print(f"== {path}: frames {len(fr)}, distinct signatures {len(sg)}")
    for s, n in sg.most_common(): print(f"   x{n:5d} colour-15 changes {s[0]} palette-B switch lines {s[1]}")
    for k in sorted(ch):
        v = ch[k]; print(f"   colour-15 change line {k[0]:3d} col {k[1]:03x}: n {len(v):5d} line-cycle min {min(v)} median {int(statistics.median(v))} p99 {pct(v, .99)} max {max(v)}")
    for k in sorted(pb):
        v = pb[k]; print(f"   palette-B switch writes line {k:3d}: n {len(v):5d} line-cycle min {min(v)} median {int(statistics.median(v))} p99 {pct(v, .99)} max {max(v)}")
ref = res[0]
for path, fr, sg, ch, pb in res[1:]:
    sa, sb = set(ref[2]), set(sg)
    print(f"-- {path} vs {ref[0]}: candidate signatures subset of reference: {sb <= sa} (candidate {len(sb)}, reference {len(sa)}, only in candidate {len(sb - sa)}); equal: {sa == sb}")
    worst = 0
    for k in sorted(set(ch) & set(ref[3])):
        d = max(ch[k]) - max(ref[3][k]); worst = max(worst, d)
    print(f"   largest (candidate max - reference max) line-cycle over the common colour-15 changes: {worst}")
    for k in sorted(set(pb) & set(ref[4])):
        print(f"   palette-B line {k}: reference max {max(ref[4][k])} candidate max {max(pb[k])}")
