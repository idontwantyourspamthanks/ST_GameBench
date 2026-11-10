#!/usr/bin/env python3
"""decode_fill.py: decode the $38cd0 fill-selector tables ($3ba5a/$3baea byte maps, $3b85a word offsets, $3ac1a 28-byte records)
for every (fog band 0..3, colour byte) and print the 16-pixel colour pattern of the interior fill for even/odd rows."""
import struct, sys
from collections import OrderedDict
d = open('/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/dumps/ram_ingame_lobos.bin','rb').read()
PAL = [d[0x4a6a+2*i:0x4a6a+2*i+2].hex() for i in range(16)]
def rec(off):
    a = 0x3ac1a + off
    r1, r2 = struct.unpack('>ii', d[a:a+8]); d4, d5 = struct.unpack('>HH', d[a+8:a+12])
    a3, a4, a5, a6 = struct.unpack('>IIII', d[a+12:a+28])
    return a, (0x38cd0 + r1, 0x38cd0 + r2), d4, d5, (a3, a4, a5, a6)
def pix(l1, l2):
    # l1 = planes0,1 ; l2 = planes 2,3 (move.l a3,(a2)+ ; move.l a4,(a2)+)
    p = [l1 >> 16, l1 & 0xffff, l2 >> 16, l2 & 0xffff]
    return [sum(((p[k] >> (15 - x)) & 1) << k for k in range(4)) for x in range(16)]
def entry(mode, band, c):
    tbl = 0x3baea if mode else 0x3ba5a
    b = d[tbl + c]
    idx = b + band * 64
    off = struct.unpack('>H', d[0x3b85a + 2 * idx:0x3b85a + 2 * idx + 2])[0]
    return idx, off
if __name__ == '__main__':
    mode = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    seen = OrderedDict()
    for band in range(4):
        print(f'--- fog band {band} (mode table {"$3baea" if mode else "$3ba5a"})')
        runs = []
        for c in range(0, 144):
            idx, off = entry(mode, band, c)
            runs.append((c, idx, off))
        # compress consecutive colours with equal record
        i = 0
        while i < len(runs):
            j = i
            while j + 1 < len(runs) and runs[j + 1][2] == runs[i][2]: j += 1
            a, tg, d4, d5, p = rec(runs[i][2])
            pe = pix(p[0], p[1]); po = pix(p[2], p[3])
            print(f'colour {runs[i][0]:3d}..{runs[j][0]:3d}  rec@{a:05x} idx {runs[i][1]:3d} d4/d5 {d4:04x}/{d5:04x} even-row px {"".join("%x" % v for v in pe)} odd-row px {"".join("%x" % v for v in po)}')
            i = j + 1
