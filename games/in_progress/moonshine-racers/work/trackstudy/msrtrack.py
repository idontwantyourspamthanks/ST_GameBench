#!/usr/bin/env python3
"""Moonshine Racers track decoder (read-only study tool).  Source of truth: MS2 (flat sector space: file offset = d1*512)
and the per-level descriptor tables in the game's RAM ($27ee,$291a,$28de,$28a2,$2866,$282a, 15 levels, 4-byte ptrs to (start,len) word pairs).
Track block (RAM $58c00, table $28a2) = six streams back to back:
  S0 curve   : (count, delta)  words, count 0 terminates      -> $23c0 ring $1bbc : v += delta per step
  S1 left    : (count, target) words                           -> $1bb0 ring $13b0 : byte slews 1/step toward target
  S2 right   : (count, target) words                           -> $1bb4 ring $17b0
  S3 hill    : (count, accel)  words (signed)                  -> $27da ring $23c8 : slope += accel, height += slope; byte = h>>16 clamp 0..127
  S4 objects : first word = distance to 1st object, then (type, lateral, gap) words, gap 0 ends          -> $133a
  S5 types   : 12-byte entries (ff00, kind, w2, sprite, w4, w5)                                       -> $1342
"""
import struct, sys, os, json
G = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
RAM = open(f'{G}/work/dumps/ram_race_start.bin', 'rb').read()
MS2 = open(f'{G}/originals/MOONSHR/FILES/MS2', 'rb').read()
NLEV = 15
TABLES = {'obj_img': 0x27ee, 'minimap_hdr': 0x291a, 'minimap_bmp': 0x28de, 'track': 0x28a2, 'gfx5a400': 0x2866, 'gfx60800': 0x282a}

def L(a): return struct.unpack('>I', RAM[a:a+4])[0]
def descr(table, lev):
    p = L(TABLES[table] + 4*lev)
    return struct.unpack('>HH', RAM[p:p+4])         # (start sector, length in sectors)

def block(lev):
    s, n = descr('track', lev)
    return s, n, MS2[s*512:(s+n)*512]

def parse(lev):
    s, n, b = block(lev)
    W = lambda o: struct.unpack('>H', b[o:o+2])[0]
    S = lambda o: struct.unpack('>h', b[o:o+2])[0]
    o = 0; out = {'sector': s, 'nsect': n}
    for name in ('curve', 'left', 'right', 'hill'):
        lst = []
        while W(o) != 0:
            lst.append((W(o), S(o+2))); o += 4
        out[name] = lst; o += 2
    out['obj_first'] = W(o); o += 2          # initial gap
    objs = []
    # entries (type, lateral, gap)
    while True:
        t, lat, gap = W(o), S(o+2), W(o+4); o += 6
        objs.append((t, lat, gap))
        if gap == 0: break
    out['objs'] = objs
    out['types_off'] = o
    out['used_before_types'] = o
    out['block_len'] = n*512
    return out, b

if __name__ == '__main__':
    for lev in range(NLEV):
        t, b = parse(lev)
        print(lev, 'sect', hex(t['sector']), 'n', t['nsect'], 'streams', len(t['curve']), len(t['left']), len(t['right']), len(t['hill']), 'objs', len(t['objs']),
              'sumcurve', sum(c for c,_ in t['curve']), 'left', sum(c for c,_ in t['left']), 'right', sum(c for c,_ in t['right']), 'hill', sum(c for c,_ in t['hill']),
              'objsum', t['obj_first']+sum(g for _,_,g in t['objs']), 'types@', t['types_off'], 'of', t['block_len'])

import numpy as np
def minimap(lev):
    s, n = descr('minimap_hdr', lev)
    b = MS2[s*512:(s+n)*512]
    h = struct.unpack('>6H', b[:12]); N = h[1]
    x, y = h[4], h[5]; pts = [(x, y, 0)]; dist = 0
    for i in range(N):
        byte = b[12+(i >> 1)]
        nib = byte >> 4 if i & 1 else byte & 15
        d1 = nib & 0xc; d2 = nib & 3
        dx = -1 if d1 == 8 else (1 if d1 == 4 else 0)
        dy = -1 if d2 == 2 else (1 if d2 == 1 else 0)
        diag = (dx != 0 and dy != 0)
        # f2e2: step is taken only when d5 (stage distance) reached; d5 = ff only if dx!=0 -> then (d5&2): +6 (diag len) ; else +4
        # model: diag when x changes AND y changes
        dist += h[3] if diag else h[2]
        x += dx; y += dy; pts.append((x, y, dist))
    return dict(len=h[0], n=N, straight=h[2], diag=h[3], x0=h[4], y0=h[5], pts=np.array(pts, dtype=float))

def curve_arrays(t, upto=32768):
    c = []; v = 0
    for n, d in t['curve']:
        for _ in range(n):
            v += d; c.append(v)
    return np.array(c, dtype=float)

def ring_arrays(stream, kind):
    """expand a (count,value) stream to one value per unit"""
    out = []
    if kind == 'slew':          # byte value slews 1/step toward target; start = first target (d2 of first pair)
        v = stream[0][1]
        for n, tgt in stream:
            for _ in range(n):
                out.append(v)
                if v < tgt: v += 1
                elif v > tgt: v -= 1
        return np.array(out, dtype=float)
    if kind == 'hill':
        d2 = 0; d3 = 0
        for n, a in stream:
            for _ in range(n):
                d3 += d2; d2 += a
                h = max(d3, 0) >> 16
                out.append(min(h, 127))
        return np.array(out, dtype=float)
