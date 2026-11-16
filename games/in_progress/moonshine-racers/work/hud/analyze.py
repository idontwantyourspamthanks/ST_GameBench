import sys, pickle, json
sys.path.insert(0, 'work/hud')
from hudlab import *
from pathlib import Path
RES = OUT / 'res'
def lw(scene, cfg):
    return load(f"skip_{scene}_{cfg}")
def win(p, lo, hi):
    return [k for k in sorted(p) if lo <= k <= hi]
def mean(p, ks, key='work'):
    return sum((p[k]['work'] if key == 'work' else p[k]['stage'].get(key, 0)) for k in ks) / len(ks)
def state_diff(scene, cfg, base='stock', ignore=()):
    a = pickle.load(open(RES / f"gate_{scene}_{base}.pkl", 'rb')); b = pickle.load(open(RES / f"gate_{scene}_{cfg}.pkl", 'rb'))
    common = sorted(set(a) & set(b))
    where = {}
    for k in common:
        for ad, x in a[k].items():
            if ad in b[k] and b[k][ad] != x and ad not in ignore:
                where.setdefault(ad, []).append(k)
    return len(common), where
def ranges(addrs):
    out = []; s = sorted(addrs)
    for x in s:
        if out and x == out[-1][1] + 1: out[-1][1] = x
        else: out.append([x, x])
    return out
def fmt_ranges(where):
    r = ranges(where.keys())
    return ' '.join(f"${a:04x}" if a == b else f"${a:04x}-${b:04x}" for a, b in r)

def shot(scene, cfg, N):
    d = RES / f"shots_{scene}_{cfg}"
    f = int.from_bytes((d / f"s{N:x}_1004.bin").read_bytes(), 'big')
    return {b: (d / f"s{N:x}_{b}.bin").read_bytes() for b in ('70000', '78000')}, f
def pixdiff(scene, cfg, N, base='stock'):
    a, fa = shot(scene, base, N); b, fb = shot(scene, cfg, N)
    out = {}
    for buf in ('70000', '78000'):
        x, y = a[buf], b[buf]
        idx = [i for i in range(32000) if x[i] != y[i]]
        if not idx: out[buf] = (0, None); continue
        ys = [i // 160 for i in idx]; xs = [(i % 160) // 8 * 16 for i in idx]
        out[buf] = (len(idx), (min(xs), min(ys), max(xs) + 15, max(ys)))
    return out, (fa, fb)
def clusters(scene, cfg, N, buf=None, base='stock'):
    """connected row/col clusters of differing 16px-groups: list of (bbox, bytes)"""
    a, fa = shot(scene, base, N); b, fb = shot(scene, cfg, N)
    buf = buf or ('70000' if fa == 0x70000 else '78000')
    x, y = a[buf], b[buf]
    cells = {}
    for i in range(32000):
        if x[i] != y[i]:
            cells.setdefault((i // 160 // 4, (i % 160) // 8), 0); cells[(i // 160 // 4, (i % 160) // 8)] += 1
    # merge cells (4 rows x 16 px) by flood fill
    seen = set(); out = []
    for c in cells:
        if c in seen: continue
        st = [c]; seen.add(c); grp = []
        while st:
            r, k = st.pop(); grp.append((r, k))
            for dr in (-1, 0, 1):
                for dk in (-1, 0, 1):
                    n = (r + dr, k + dk)
                    if n in cells and n not in seen: seen.add(n); st.append(n)
        rs = [g[0] for g in grp]; ks = [g[1] for g in grp]
        out.append(((min(ks) * 16, min(rs) * 4, max(ks) * 16 + 15, max(rs) * 4 + 3), sum(cells[g] for g in grp)))
    return sorted(out)

BOX = {'thermometer': (0, 18, 31, 64), 'minimap': (16, 15, 95, 64), 'dial': (80, 16, 111, 46), 'position': (80, 49, 111, 62), 'score': (32, 1, 79, 14),
       'face': (272, 17, 303, 64), 'text': (112, 16, 271, 64), 'cup': (0, 172, 31, 199), 'speedo': (256, 151, 319, 174), 'gear': (272, 180, 303, 194)}
def boxbytes(buf, box):
    x0, y0, x1, y1 = box
    return [(y * 160 + c) for y in range(y0, y1 + 1) for c in range((x0 // 16) * 8, (x1 // 16) * 8 + 8)]
def series_changes(base, N0, count):
    """per element: bytes changed between the displayed frames of pass N and N+1 (inside the element box), mean over the pairs"""
    d = RES / base
    fr = []
    for N in range(N0, N0 + count):
        f = int.from_bytes((d / f"s{N:x}_1004.bin").read_bytes(), 'big')
        fr.append((d / f"s{N:x}_{'70000' if f == 0x70000 else '78000'}.bin").read_bytes())
    out = {}
    for name, box in BOX.items():
        idx = boxbytes(None, box)
        ch = [sum(1 for i in idx if fr[j][i] != fr[j + 1][i]) for j in range(len(fr) - 1)]
        out[name] = ch
    return out
