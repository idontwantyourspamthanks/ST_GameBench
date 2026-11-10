#!/usr/bin/env python3
"""replica.py: bit-level Python replica of the MW2 local-terrain generator ($24d0e / $25fec / $25a8a / PRNG $27462) and of the
lighting pass ($1c996 height doubling, $1c832/$1c956 shading), checked against RAM captured by cap_rebuild.py.

Usage: python3 replica.py                (checks /tmp/terr/{entry.bin,L0..L5.bin,grid_raw.bin,grid_pre.bin,grid_shaded.bin})
"""
import struct, sys

def s16(x):
    x &= 0xffff
    return x - 0x10000 if x & 0x8000 else x

def u16(x): return x & 0xffff

def prng(st, rng):
    """$27462: st=[s0,s1] ($11048,$1104a); rng = $68f4; returns $68f6"""
    d0 = (st[0] ^ 0xfade) & 0xffff
    d1 = (st[1] ^ 0xbead) & 0xffff
    d2 = d1 * d0                                  # mulu.w d0,d2
    d2 = s16(d2) * s16(d2)                        # muls.w d2,d2 (low word squared)
    d2 &= 0xffffffff
    d0 = u16(d0 + d2)                             # add.w d2,d0
    d0 = u16(d0 + (d2 >> 16))                     # swap d2 ; add.w d2,d0
    d0 = u16(d0 + d1)                             # add.w d1,d0
    prod = s16(d0) * s16(rng)                     # muls.w $68f4,d0
    return s16((prod & 0xffffffff) >> 16)         # swap d0 ; move.w d0,$68f6

class Gen:
    def __init__(self, base_rows):
        self.src = base_rows               # 53 rows x 83 words (signed)
        self.out = None
        # $25a00
        self.v = dict(x10f14=0x20, v11036=0x20, v11034=0x40, v11032=0x80, v1102e=0, v11030=0)
        self.cell_sw = 0x40               # unused here
        self.calls = 0

    def sub_26212(self):
        v = self.v
        amp = v['v11032']; off = v['v11034']
        v['amp'] = amp; v['off'] = off
        x, y = v['v1102e'], v['v11030']
        d2 = u16(x + off); d3 = u16(y + off)
        v['s11044'] = d2; v['s11046'] = d3; v['s1103c'] = d2; v['s1103e'] = y; v['s11040'] = x; v['s11042'] = d3

    def subdivide(self, src):
        """$26186/$2616a body: 53 source rows x 83 -> out 106 rows x 166 words; returns (out, scratch history)"""
        self.sub_26212()
        v = self.v
        amp = v['amp']
        R = len(src); C = 83
        # scratch buffers: stale (unknown) at start -> 0
        prevC = [0] * 83; curC = [0] * 83
        out = [[0] * 166 for _ in range(2 * R)]
        for r in range(R):
            row = src[r]
            nxt = src[r + 1] if r + 1 < R else [0] * 84
            # ---- part 1: centres
            st = [v['s11044'], v['s11046']]
            newC = [0] * 83
            for x in range(83):
                a = row[x]; b = row[x + 1] if x + 1 < len(row) else 0
                c = nxt[x + 1] if x + 1 < len(nxt) else 0; dd = nxt[x]
                d0 = s16(a + b); d1 = s16(c + dd)
                d2 = d0
                d0 = s16(d0 + d1); d1 = s16(d1 - d2)
                if d1 < 0: d1 = s16(-d1)
                d0 = d0 >> 2; d1 = d1 >> 1                  # asr.w
                rng = u16(d1 + amp)
                rnd = prng(st, rng); self.calls += 1
                newC[x] = s16(d0 + rnd)
                st[0] = u16(st[0] + amp)
            v['s11044'] = st[0] if False else v['s11044']   # (row seed advanced below)
            v['s11046'] = u16(v['s11046'] + amp)
            curC = newC
            # ---- part 2: horizontal edges -> dest row 2r
            st = [v['s1103c'], v['s1103e']]
            for x in range(83):
                p0 = row[x]; p1 = row[x + 1] if x + 1 < len(row) else 0
                d0 = s16(p0 + prevC[x]); d1 = s16(p1 + curC[x])
                d2 = d0
                d0 = s16(d0 + d1); d1 = s16(d1 - d2)
                if d1 < 0: d1 = s16(-d1)
                d0 = d0 >> 2; d1 = d1 >> 1
                rnd = prng(st, u16(d1 + amp)); self.calls += 1
                out[2 * r][2 * x] = p0
                out[2 * r][2 * x + 1] = s16(d0 + rnd)
                st[0] = u16(st[0] + amp)
            v['s1103e'] = u16(v['s1103e'] + amp)
            # ---- part 3: vertical edges + centres -> dest row 2r+1
            st = [v['s11040'], v['s11042']]
            for x in range(83):
                p0 = row[x]; p1 = nxt[x]
                cl = curC[x - 1] if x > 0 else 0
                d0 = s16(p0 + cl); d1 = s16(p1 + curC[x])
                d2 = d0
                d0 = s16(d0 + d1); d1 = s16(d1 - d2)
                if d1 < 0: d1 = s16(-d1)
                d0 = d0 >> 2; d1 = d1 >> 1
                rnd = prng(st, u16(d1 + amp)); self.calls += 1
                out[2 * r + 1][2 * x] = s16(d0 + rnd)
                out[2 * r + 1][2 * x + 1] = curC[x]
                st[0] = u16(st[0] + amp)
            v['s11042'] = u16(v['s11042'] + amp)
            prevC = curC
        return out

    def level_step(self, X, Y):
        """$24d9e + $25fec + $26128 + $26186"""
        v = self.v
        sh = self.shift
        ox = ((X - self.acc_x) >> sh) - 0x28
        oy = ((Y - self.acc_y) >> sh) - 0x19
        ox = min(max(ox, 0), 0x50); oy = min(max(oy, 0), 0x32)
        self.acc_x += ox << sh; self.acc_y += oy << sh
        self.shift -= 1
        self.origins.append((ox, oy))
        # $25fec
        v['v11032'] = v['v11034']; v['v11034'] = v['v11036']; v['v11036'] >>= 1
        d2 = v['v11032']
        v['v1102e'] = u16(v['v1102e'] + (ox + 1) * d2)
        v['v11030'] = u16(v['v11030'] + (oy + 1) * d2)
        # $26128 crop (origin+1) -> 53 x 83 window
        win = [self.out[oy + 1 + r][ox + 1: ox + 1 + 83] for r in range(53)]
        self.out = self.subdivide(win)
        return ox, oy

    def run(self, X, Y):
        self.shift = 6; self.acc_x = 0; self.acc_y = 0; self.origins = []
        self.out = self.subdivide(self.src)           # $2616a: level 0
        self.levels = [self.out]
        for _ in range(5):
            self.level_step(X, Y)
            self.levels.append(self.out)
        return self.out

if __name__ == '__main__':
    d = open('/tmp/terr/entry.bin', 'rb').read()
    base = [list(struct.unpack('>83h', d[0x49c80 + 166 * r: 0x49c80 + 166 * r + 166])) for r in range(53)]
    X, Y = 1072, 2888                       # $66bc/$66be after the recentre ($31e2e) = values at L0..
    g = Gen(base)
    g.run(X, Y)
    def load(fn):
        b = open(fn, 'rb').read()
        return [list(struct.unpack('>166h', b[332 * r: 332 * r + 332])) for r in range(106)]
    for k in range(6):
        ref = load(f'/tmp/terr/L{k}.bin')
        mine = g.levels[k]
        bad = 0; tot = 0; badint = 0; totint = 0
        for r in range(106):
            for c in range(166):
                tot += 1
                if mine[r][c] != ref[r][c]:
                    bad += 1
                    if 2 <= r < 103 and 2 <= c < 164: badint += 1
                if 2 <= r < 103 and 2 <= c < 164: totint += 1
        print(f'level {k}: {tot - bad}/{tot} words match, interior (excluding 2-cell border): {totint - badint}/{totint}   origins so far {g.origins[:k]}')
    print('PRNG calls', g.calls)

# ---------------------------------------------------------------- stage 2: window extract, doubling, lighting
import math
def window_from_L5(L5):
    """$24d4e/$24d62: crop 100x100 words at row 1, col 31 of the 166-wide array, rows written bottom-up (Y flip), then $24d84
    stores them as grid words (height, 0)."""
    grid = [[0] * 100 for _ in range(100)]
    for i in range(100):
        grid[99 - i] = L5[1 + i][31:131]
    return grid

def shade(d2, d3, d5, isqrt=math.isqrt):
    """$1c956: returns shade 0..15 (+ d5 flag)"""
    d4 = 0x100                                        # $6792
    d6 = s16(d4 + d3); d6 = s16(2 * d6); d6 = s16(d6 - d4)
    n = s16(d2) ** 2 + s16(d3) ** 2 + d4 * d4
    ln = isqrt(n)
    q = int((d6 * 8) / ln)                            # divs.w truncates toward zero
    if q < 0: q = 0
    if q >= 16: q = 15
    return q + d5

def light(H, base_bytes=None, parity0=0):
    """$1c832 over a 100x100 grid (list of rows of heights); returns (A,B) byte grids. base_bytes = optional (A,B) preset values."""
    A = [[0] * 100 for _ in range(100)] if base_bytes is None else [r[:] for r in base_bytes[0]]
    B = [[0] * 100 for _ in range(100)] if base_bytes is None else [r[:] for r in base_bytes[1]]
    flat = [v for r in H for v in r] + [0] * 205          # the original reads linear memory: x=99 -> next row's x=0, y=99 -> bytes after the grid
    def h(x, y):
        return flat[y * 100 + x]
    for y in range(100):
        for x in range(100):
            h0 = h(x, y); hE = h(x + 1, y); hS = h(x, y + 1); hSE = h(x + 1, y + 1)
            d5 = 0x10 if ((A[y][x] << 8 | B[y][x]) & 0xf0f0) == 0 else 0
            if (x + y + parity0) & 1:
                f = d5 if (h0 < 0 or hS < 0 or hSE >= 0 and False) else 0
                f = d5 if (h0 < 0 or hS < 0 or not hSE >= 0) else 0
                A[y][x] = (A[y][x] + shade(hS - hSE, hS - h0, f)) & 0xff
                f = d5 if (h0 < 0 or hE < 0 or not hSE >= 0) else 0
                B[y][x] = (B[y][x] + shade(h0 - hE, hSE - hE, f)) & 0xff
            else:
                f = d5 if (hSE < 0 or hS < 0 or not hE >= 0) else 0
                A[y][x] = (A[y][x] + shade(hS - hSE, hSE - hE, f)) & 0xff
                f = d5 if (h0 < 0 or hE < 0 or not hS >= 0) else 0
                B[y][x] = (B[y][x] + shade(h0 - hE, hS - h0, f)) & 0xff
    return A, B

def load_grid(fn, off=0):
    d = open(fn, 'rb').read()
    H = [[struct.unpack('>h', d[off + 4 * (100 * y + x): off + 4 * (100 * y + x) + 2])[0] for x in range(100)] for y in range(100)]
    A = [[d[off + 4 * (100 * y + x) + 2] for x in range(100)] for y in range(100)]
    B = [[d[off + 4 * (100 * y + x) + 3] for x in range(100)] for y in range(100)]
    return H, A, B

def check_stage2(g):
    raw = load_grid('/tmp/terr/grid_raw.bin')
    mine = window_from_L5(g.levels[5])
    ok = sum(1 for y in range(100) for x in range(100) if mine[y][x] == raw[0][y][x])
    print(f'window extract: {ok}/10000 grid words equal captured grid after $24d0e')
    pre = load_grid('/tmp/terr/grid_pre.bin')
    dbl = [[s16(2 * v) for v in r] for r in raw[0]]
    diff = [(x, y) for y in range(100) for x in range(100) if dbl[y][x] != pre[0][y][x]]
    print(f'doubling $1c996 + pads/craters: {10000 - len(diff)}/10000 cells == 2*raw; {len(diff)} cells changed by pad/crater passes')
    sh = load_grid('/tmp/terr/grid_shaded.bin')
    return raw, pre, sh, diff

if __name__ == '__main__':
    raw, pre, sh, diff = check_stage2(g)
    # lighting on the real post-pad heights
    A, B = light(sh[0])
    badA = [(x, y) for y in range(100) for x in range(100) if A[y][x] != sh[1][y][x]]
    badB = [(x, y) for y in range(100) for x in range(100) if B[y][x] != sh[2][y][x]]
    print('shade byte A mismatches', len(badA), 'B mismatches', len(badB))
    print('first mismatches A', [(x, y, A[y][x], sh[1][y][x]) for x, y in badA[:12]])
