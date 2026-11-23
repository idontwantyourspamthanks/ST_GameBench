"""Stock vs patched comparison for scripted runs (expected relation: patched loop j == stock loop j+1 for everything causally downstream of the patched entry)."""
import sys, json
import numpy as np
from cmp_sc import load, w, player, frames, PL_LO, PL_HI
SHOT = 0x33944 + 8                      # slot 4 words: field offsets 0,0xc,..,0x6c
def shot(f): return tuple(w(f, SHOT + fld) for fld in (0x00, 0x0c, 0x18, 0x3c, 0x48, 0x54, 0x60, 0x6c))
def creatures(f): return tuple(w(f, 0x33944 + fld + 2 * s) for fld in (0x00, 0x0c, 0x18, 0x3c, 0x48, 0x54, 0x60, 0x6c) for s in range(4))
def grid(f): return f['g1'] + f['g2']
def report(stock, other):
    S, _ = load(stock); P, _ = load(other)
    n = min(len(S), len(P)) - 2
    print(f'== {other} vs {stock}: {len(S)} / {len(P)} loops after timer start, compared 0..{n-1}')
    def rel(name, fn):
        d = [j for j in range(n) if fn(S[j]) != fn(P[j])]
        sh = [j for j in d if fn(P[j]) == fn(S[j + 1])]
        un = [j for j in d if j not in sh]
        print(f'  {name:28s}: differs at the same index in {len(d):3d} loops; patched[j]==stock[j+1] in {len(sh):3d}; unexplained {len(un)} {un[:12]}')
        return d, sh, un
    rel('player vars $33a16..22', player)
    rel('shot slot (projectile)', shot)
    rel('creature slots 0-3', creatures)
    if S[0]['g1']: rel('grid cells col1/col2 rows0-15', grid)
    rel('$33918 (cells shot) + $3392c energy', lambda f: (w(f, 0x33918), w(f, 0x3392c)))
    rel('flags $338f0..$338fa', lambda f: tuple(w(f, a) for a in range(0x338f0, 0x338fc, 2)))
    # whole block, excluding timer words (separate) -> list addresses that differ at the same index but are not shifted-equal
    bad = {}
    for j in range(n):
        a, b, c = S[j]['blk'], P[j]['blk'], S[j + 1]['blk']
        for i in range(len(a)):
            if a[i] != b[i] and b[i] != c[i]: bad.setdefault(0x33900 + i, []).append(j)
    print('  block bytes that differ at the same index AND are not equal to the stock value one loop later (address: loops):')
    for ad, lj in sorted(bad.items()): print(f'     ${ad:05x}: {len(lj)} loops {lj[:10]}')
    # score-like: timer
    print('  timer words differ at same index in', sum(1 for j in range(n) if S[j]['timer'] != P[j]['timer']), 'loops; patched[j]==stock[j+1] in',
          sum(1 for j in range(n) if S[j]['timer'] != P[j]['timer'] and P[j]['timer'] == S[j + 1]['timer']))
def pixels(stock, other):
    meta = json.load(open(f'sc/{stock}.meta')); metap = json.load(open(f'sc/{other}.meta'))
    _, ts = load(stock); _, tp = load(other)
    Fs = frames(stock, ts); Fp = frames(other, tp)
    idx = {int(k): v for k, v in meta['idx_of'].items()}
    loops = [j for j in meta['caps_loops'] if j in idx and idx[j] in Fs and idx[j] in Fp and (j + 1) in idx and idx[j + 1] in Fs]
    def band(a, b, lo, hi):
        A = np.frombuffer(a, np.uint8).reshape(200, 160)[lo:hi]; B = np.frombuffer(b, np.uint8).reshape(200, 160)[lo:hi]; return int((A != B).sum())
    print(f'== pixels {other} vs {stock}: frames at loops {loops[0]}..{loops[-1]} ({len(loops)} frames)')
    print('  loop: rows20..129 patched(j) vs stock(j+1) | patched(j) vs stock(j) | rows0..19+130..199 patched(j) vs stock(j) (time-driven: must be 0)')
    tot1 = tot3 = 0; shifted_ok = 0
    for j in loops:
        p = Fp[idx[j]]; s0 = Fs[idx[j]]; s1 = Fs[idx[j + 1]]
        a = band(p, s1, 20, 130); b = band(p, s0, 20, 130); c = band(p, s0, 0, 20) + band(p, s0, 130, 200)
        tot1 += a; tot3 += c; shifted_ok += (a == 0)
        print(f'   {j:3d}: {a:6d} | {b:6d} | {c:4d}')
    print(f'  frames with 0 differing bytes in rows 20..129 at (j vs j+1): {shifted_ok} of {len(loops)}; time-driven rows (HUD+sea) patched(j) vs stock(j) differing bytes total: {tot3}')
if __name__ == '__main__':
    report(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3: pixels(sys.argv[1], sys.argv[2])
