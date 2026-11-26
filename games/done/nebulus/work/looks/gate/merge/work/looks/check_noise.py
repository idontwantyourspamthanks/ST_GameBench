"""Same-build control for the flags-0 stock sequence: level-start dumps (run_look.py stock, 8 levels) of 2 un-hooked (old) and 2 hooked (new) runs.
usage: check_noise.py R old1 old2 new1 new2 N  -> per pair (old1-old2 = noise, new1-new2 = noise, old1-new1, old2-new2, old1-new2, old2-new1): per level count of differing bytes in
$33900..$33a80 (game vars), $3ad90..$3adb0 (timer) and the strict regions (palette, raster, skyline, eye frames, balls, grid); every |delta| is listed."""
import sys
R, o1, o2, n1, n2, N = sys.argv[1:7]; N = int(N)
STRICT = [('palette', 0x351ac, 0x20), ('raster', 0x40398, 8), ('skyline', 0x100e0, 0x1000), ('eyes', 0x24be0, 0xaf00), ('balls', 0x14560, 0x400), ('grid', 0x327f0, 0x1000)]
SOFT = [('vars $33900..', 0x33900, 0x180), ('timer $3ad90..', 0x3ad90, 0x20)]
def rd(run, i): return open(f'{R}/stock_{run}/lvl{i}.bin', 'rb').read()
def cmp(a, b):
    res = {}; maxd = 0
    for n, ad, ln in STRICT + SOFT:
        d = [k for k in range(ad, ad + ln) if a[k] != b[k]]
        res[n] = d
        if n.startswith(('vars', 'timer')):
            for k in d: maxd = max(maxd, abs(a[k] - b[k]))
    return res, maxd
tot = {}
for name, x, y in (('old1~old2 (noise, un-hooked)', o1, o2), ('new1~new2 (noise, hooked)', n1, n2), ('old1~new1', o1, n1), ('old2~new2', o2, n2), ('old1~new2', o1, n2), ('old2~new1', o2, n1)):
    print(f'== {name}')
    strict = 0; soft = 0; mx = 0; addrs = set()
    for i in range(N):
        r, m = cmp(rd(x, i), rd(y, i))
        s = sum(len(r[n]) for n, _, _ in STRICT); v = len(r['vars $33900..']); t = len(r['timer $3ad90..'])
        strict += s; soft += v + t; mx = max(mx, m)
        for n in ('vars $33900..', 'timer $3ad90..'): addrs.update(r[n])
        print(f'  level {i}: strict regions {s} B differ | vars {v} B | timer {t} B | max |delta| {m}' + ('  vars@' + ' '.join(f'${k:x}' for k in r['vars $33900..'][:8]) if v else '') + ('  timer@' + ' '.join(f'${k:x}' for k in r['timer $3ad90..'][:6]) if t else ''))
    print(f'  TOTAL strict {strict} B, soft {soft} B over {N} levels, max |delta| {mx}, distinct soft addresses {len(addrs)}')
