#!/usr/bin/env python3
"""shots_png.py TAG: render ab/raw_TAG/ (shots.py output) to ab/TAG_flipNN.png (320x200, ST palette $ff8240 of the hit, nibble RGB with the STE low bit)."""
import sys
from cs import *
from PIL import Image
# the game fades its palette from frame to frame (night/day cycle); one fixed palette (that of before flip 08, the bright one) is used for every frame so the pictures compare
PAL = parse_hits((HERE / 'ab/raw_before/log.txt').read_text(errors='replace'), 0x66e6)[8]
tag = sys.argv[1]; raw = HERE / 'ab' / f'raw_{tag}'
rows = parse_hits((raw / 'log.txt').read_text(errors='replace'), 0x66e6)
for k, r in enumerate(rows):
    base = rd(r, 0x67a6, 4)
    buf = (raw / f'b{base:x}_{k:02d}.bin').read_bytes()
    pal = [rd(PAL, 0xff8240 + 2 * j) for j in range(16)]
    rgb = [tuple(((((p >> s) & 7) << 1) | (((p >> s) >> 3) & 1)) * 17 for s in (8, 4, 0)) for p in pal]
    im = Image.new('RGB', (320, 200)); px = im.load()
    for y in range(200):
        for xb in range(20):
            o = y * 160 + xb * 8
            w = [(buf[o + 2 * p] << 8) | buf[o + 2 * p + 1] for p in range(4)]
            for b in range(16):
                c = sum(((w[p] >> (15 - b)) & 1) << p for p in range(4)); px[xb * 16 + b, y] = rgb[c]
    im.save(HERE / 'ab' / f'{tag}_flip{k:02d}.png')
print(len(rows), 'frames', [hex(rd(r, 0xff8240 + 2 * j)) for r in rows[:1] for j in range(16)])
