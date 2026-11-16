"""Offline copy of the game's terrain height function $5068 ($1fcf4 -> $1fbec, $1fc24) on a dumped 100x100 grid ($40040, 4 B per cell)."""
import struct, re, sys
class Grid:
    def __init__(self, ram):
        self.g = [[struct.unpack('>h', ram[0x40040 + (r*100+c)*4: 0x40040 + (r*100+c)*4 + 2])[0] for c in range(100)] for r in range(100)]
    def h(self, X, Y):
        d0 = X - 0x6400; d1 = -(Y - 0x6400)
        d5 = d0 & 0x1ff; d6 = d1 & 0x1ff; cx = (d0 >> 9) + 50; cy = (d1 >> 9) + 50; d7 = (cx + cy) & 1
        g = self.g; h1 = g[cy][cx]; h2 = g[cy+1][cx]; h3 = g[cy+1][cx+1]; h4 = g[cy][cx+1]
        if d7:
            if d5 - d6 >= 0: return ((d5*(h4-h1) + d6*(h3-h4)) >> 9) + h1
            return ((d5*(h3-h2) + d6*(h2-h1)) >> 9) + h1
        if d5 + d6 - 0x200 >= 0: return ((d5*(h3-h2) + (d6-0x200)*-(h4-h3)) >> 9) + h2
        return ((d5*(h4-h1) + d6*(h2-h1)) >> 9) + h1
def rows(path):
    out = []
    for l in open(path):
        if not l.startswith('vbl'): continue
        t = l.split(); d = {}
        for k in ('PH', 'X', 'Y', 'H', 'alt', 'ter', 'spd', 'INT'):
            d[k] = int(t[t.index(k) + 1])
        out.append(d)
    return out
if __name__ == '__main__':
    g = Grid(open('snap/crawler_ram.bin', 'rb').read())
    for f in sys.argv[1:]:
        rs = rows(f); ok = n = 0; errs = []; saw = []
        for r in rs:
            t = g.h(r['X'], r['Y'])
            if r['PH'] == 1:
                n += 1; ok += (t == r['ter'])
            else:
                errs.append(r['alt'] - (t + 50))
        print(f, f'PH1 rows: model==$34936 {ok}/{n}; extra frames {len(errs)}: shown alt - (terrain(pred XY)+50): min {min(errs)} max {max(errs)} mean|e| {sum(abs(e) for e in errs)/len(errs):.1f}; |e|>10: {sum(abs(e)>10 for e in errs)}')
        if '-v' in sys.argv: print(errs)
