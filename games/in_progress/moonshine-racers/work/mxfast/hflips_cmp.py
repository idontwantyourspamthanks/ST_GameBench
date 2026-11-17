"""python3 hflips_cmp.py REFDIR CANDDIR : per pass the two screen buffers (main frame + extra of that pass) compared as an unordered pair (the buffer parity at the capture instant can differ by one flip between runs: the pair is the same frames)"""
import sys, os
a, b = sys.argv[1], sys.argv[2]
ks = sorted(int(f[1:-6]) for f in os.listdir(a) if f.endswith('_a.bin') and os.path.exists(f'{b}/{f}'))
nbad = 0; nfl = 0; swapped = 0; bad = []
rd = lambda d, k, s: open(f'{d}/f{k}_{s}.bin', 'rb').read()
for k in ks:
    xa, xb, ya, yb = rd(a, k, 'a'), rd(a, k, 'b'), rd(b, k, 'a'), rd(b, k, 'b')
    if (xa, xb) == (ya, yb): pairs = [(xa, ya), (xb, yb)]
    elif (xa, xb) == (yb, ya): pairs = [(xa, yb), (xb, ya)]; swapped += 1
    else: pairs = [(xa, ya), (xb, yb)]
    for i, (x, y) in enumerate(pairs):
        nfl += 1
        if x != y:
            d = [j for j in range(len(x)) if x[j] != y[j]]; rows = sorted(set(j // 160 for j in d))
            nbad += 1; bad.append((k, i, len(d), rows[0], rows[-1]))
print(f'{a} vs {b}: passes {len(ks)} (buffer pair swapped in {swapped}), frames compared {nfl} (main + extra of each pass), differing {nbad}', bad[:12])
