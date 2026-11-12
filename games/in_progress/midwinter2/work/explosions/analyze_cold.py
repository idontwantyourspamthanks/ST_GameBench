import sys, struct
from pathlib import Path
from idxcount import idx_hist
from bufimg import render, pal_from
from PIL import Image, ImageDraw
d = Path(sys.argv[1]); out = sys.argv[2]
PAL = pal_from(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/explosions/win_pal.bin', 'rb').read())
ks = sorted(int(p.name[1:4]) for p in d.glob('f*_vbl.bin'))
rows = []; prev = None
for k in ks:
    clk = int.from_bytes((d / f'f{k:03d}_vbl.bin').read_bytes(), 'big')
    o = []
    for w in ('60000', '70000'):
        b = (d / f'f{k:03d}_{w}.bin').read_bytes()
        h = idx_hist(b); o.append((h[10], h[11]))
    ty = int.from_bytes((d / f'f{k:03d}_ty.bin').read_bytes(), 'big')
    rows.append((k, clk, o, ty))
print('flip clock(1/300s) type | orange/white in rows 58-179: buf60000  buf70000')
for k, clk, o, ty in rows:
    print(f'{k:3d} {clk:8d} {ty:2d} | {o[0][0]:5d}/{o[0][1]:4d}  {o[1][0]:5d}/{o[1][1]:4d}')
clks = [r[1] for r in rows]
span = (clks[-1] - clks[0]) / 300.0
print(f'flips {len(rows)} over {span:.2f} s of emulated time (tick_vbl clock) = ' + (f'{len(rows)/span:.1f} flips/s' if span else 'n/a (stock: no tick_vbl clock)'))
# distinct-buffer redraw check: consecutive-flip pixel differences
import itertools
def rd(k, w): return (d / f'f{k:03d}_{w}.bin').read_bytes()
nch = 0
for k1, k2 in zip(ks, ks[1:]):
    a, b = rd(k1, '60000'), rd(k2, '60000'); c, e = rd(k1, '70000'), rd(k2, '70000')
    if a != b or c != e: nch += 1
print(f'flip pairs with any change in either buffer: {nch}/{len(ks)-1}')
# sheet: every ~n-th flip, display both buffers
sel = ks[::max(1, len(ks) // 12)][:12]
ims = []
for k in sel:
    for w in ('60000', '70000'):
        im = render(rd(k, w), PAL).crop((0, 28, 320, 130)).resize((480, 153), Image.NEAREST)
        ImageDraw.Draw(im).text((3, 3), f'{d.name} f{k:03d} {w}', fill=(255, 255, 255)); ims.append(im)
S = Image.new('RGB', (480 * 4, 153 * ((len(ims) + 3) // 4)))
for i, im in enumerate(ims): S.paste(im, ((i % 4) * 480, (i // 4) * 153))
S.save(out)
