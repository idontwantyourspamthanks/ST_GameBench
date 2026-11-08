#!/usr/bin/env python3
"""Decode the cockpit overlay list ($68000) from a RAM dump and report cost / opacity per region.

    python3 work/cockpit/overlay_analysis.py [ram.bin] [profile.txt]

List format (replay $30f2c): word count-1, then records in ascending destination order:
  masked  : delta.w (>=0, added to the running dst), mask.l, or1.l, or2.l   (14 B, 8 dst bytes)
            dst.l = (dst.l & mask) | or1 ; next long likewise with the SAME mask and or2
  run-copy: ~delta.w (bit15 set), n-1.w, n*8 data bytes                      (4+8n B)
Writes work/cockpit/overlay_regions.png.
"""
import collections, struct, sys
from pathlib import Path
from PIL import Image

RAM = sys.argv[1] if len(sys.argv) > 1 else 'work/dumps/ram_ingame_lobos.bin'
PROF = sys.argv[2] if len(sys.argv) > 2 else 'work/prof/walking.txt'
ram = Path(RAM).read_bytes()
W = lambda a: struct.unpack('>H', ram[a:a + 2])[0]
L = lambda a: struct.unpack('>I', ram[a:a + 4])[0]

def parse(base=0x68000):
    n = W(base) + 1; p = base + 2; pos = 0; recs = []
    for _ in range(n):
        start = p; d = W(p); p += 2
        if d & 0x8000:
            pos += (~d) & 0xffff; cnt = W(p) + 1; p += 2
            recs.append(dict(kind='copy', pos=pos, nb=cnt * 8, data=ram[p:p + cnt * 8])); p += cnt * 8; pos += cnt * 8
        else:
            pos += d
            recs.append(dict(kind='mask', pos=pos, nb=8, mask=L(p), o1=L(p + 4), o2=L(p + 8))); p += 12; pos += 8
        recs[-1]['list_bytes'] = p - start
    return recs, p

recs, end = parse()
line = lambda r: r['pos'] // 160
print(f'{len(recs)} records, list {end - 0x68000} B, dst bytes {sum(r["nb"] for r in recs)}, '
      f'{sum(r["kind"] == "copy" for r in recs)} run-copy')

# cycle model from the profile (19 calls of $30f2c in walking.txt)
prof = {}
for ln in Path(PROF).read_text().splitlines()[1:]:
    a, _, c = ln.split(); prof[int(a, 16)] = int(c)
calls = prof[0x30f30] // 16
S = lambda lo, hi: sum(v for a, v in prof.items() if lo <= a <= hi)
tot = S(0x30f2c, 0x30f70) / calls
nm = sum(r['kind'] == 'mask' for r in recs); nc = len(recs) - nm
head = (prof[0x30f3a] + prof[0x30f3c]) / calls / len(recs)
mbody = S(0x30f3e, 0x30f50) / calls / nm
cfix = (prof[0x30f5a] + prof[0x30f5c] + prof[0x30f5e] + prof[0x30f68]) / calls / nc
c8 = (prof[0x30f60] + prof[0x30f62] + prof[0x30f64]) / calls / 208
cost = lambda r: head + (mbody if r['kind'] == 'mask' else cfix + c8 * r['nb'] / 8)
frame = int(open(PROF).readline().split('=')[1].split()[0]) / calls
print(f'replay {tot:.0f} c/call = {tot / frame * 100:.2f}% of a frame ({frame:.0f} c); masked rec {head + mbody:.1f} c, '
      f'copy rec {head + cfix:.1f} c + {c8:.1f} c per 8 B group')
reg = lambda r: 'dashboard 182-199' if line(r) >= 182 else ('pillar-L 58-181' if (r['pos'] % 160) // 8 < 10 else 'pillar-R 58-181')
tab = collections.defaultdict(lambda: [0, 0, 0, 0, 0.0])
for r in recs:
    t = tab[reg(r)]; t[0] += 1; t[1] += r['nb']; t[2] += r['list_bytes']; t[3] += r['kind'] == 'copy'; t[4] += cost(r)
for k, t in sorted(tab.items()):
    print(f'{k:18s} recs {t[0]:3d} (copy {t[3]:2d}) dst {t[1]:5d} B list {t[2]:5d} B  {t[4]:7.0f} c  '
          f'{t[4] / tot * 100:4.1f}% of replay  {t[4] / frame * 100:.2f}% of frame')
print(f'other (movem save/restore, setup): {tot - sum(t[4] for t in tab.values()):.0f} c')

# pixel map: 1 opaque, 2 transparent inside a record, 0 no record, 3 partial
px = [[0] * 320 for _ in range(200)]; colour = {}
for r in recs:
    l = line(r); g = (r['pos'] % 160) // 8
    if r['kind'] == 'copy':
        for i in range(r['nb'] // 8):
            w = [int.from_bytes(r['data'][i * 8 + j * 2:i * 8 + j * 2 + 2], 'big') for j in range(4)]
            for b in range(16):
                x = (g + i) * 16 + 15 - b; px[l][x] = 1; colour[l, x] = sum(((w[p] >> b) & 1) << p for p in range(4))
    else:
        mw = [r['mask'] >> 16, r['mask'] & 0xffff] * 2; ow = [r['o1'] >> 16, r['o1'] & 0xffff, r['o2'] >> 16, r['o2'] & 0xffff]
        for b in range(16):
            x = g * 16 + 15 - b; mk = [(mw[i] >> b) & 1 for i in range(4)]; ok = [(ow[i] >> b) & 1 for i in range(4)]
            if not any(mk): px[l][x] = 1; colour[l, x] = sum(ok[p] << p for p in range(4))
            elif all(mk) and not any(ok): px[l][x] = 2
            else: px[l][x] = 3
cnt = collections.Counter((l >= 182, px[l][x]) for l in range(200) for x in range(320))
print('partial (mixed) pixels:', sum(v for (d, s), v in cnt.items() if s == 3))
op_p = sum(px[l][x] == 1 for l in range(58, 182) for x in range(320)); op_d = sum(px[l][x] == 1 for l in range(182, 200) for x in range(320))
win = 142 * 319
print(f'opaque px: pillars {op_p}, dashboard {op_d} = {(op_p + op_d) / win * 100:.1f}% of the {win}-px window; '
      f'transparent px inside records: pillars {cnt[(False, 2)]}, dashboard {cnt[(True, 2)]}')
print('colours of opaque px:', sorted(collections.Counter(colour.values()).items()))
def runs(l):
    out = []; s = None
    for x in range(321):
        v = x < 320 and px[l][x] == 1
        if v and s is None: s = x
        if not v and s is not None: out.append((s, x - 1)); s = None
    return out
for l in (58, 61, 100, 150, 181, 182, 185, 191, 192, 196, 199): print(f'line {l}: opaque x-runs {runs(l)}')
print('fewest visible px on any row (x=1..319):', min((319 - sum(px[l][x] == 1 for l in [l] for x in range(1, 320)), l) for l in range(58, 200)))
cg = collections.Counter(line(r) for r in recs if r['kind'] == 'copy' for _ in range(r['nb'] // 8))
print('run-copy (fully opaque 8-byte) groups per line:', dict(sorted(cg.items())))

S3 = 3; im = Image.new('RGB', (320 * S3, 200 * S3))
pix = im.load()
for l in range(200):
    for x in range(320):
        v = px[l][x]
        c = (40, 40, 40) if l < 58 else (((30, 160, 30) if l < 182 else (230, 130, 20)) if v == 1 else
                                         (((150, 210, 150) if l < 182 else (245, 200, 140)) if v == 2 else (150, 190, 255)))
        if l == 182: c = (255, 0, 0)
        for dy in range(S3):
            for dx in range(S3): pix[x * S3 + dx, l * S3 + dy] = c
im.save('work/cockpit/overlay_regions.png')
