"""Montage of the look-gate screenshots with the cell labels: montage.py DIR OUT.png [cols]  (labels from mk_looks2.CELLS order)"""
import sys
from PIL import Image, ImageDraw
d, out = sys.argv[1], sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
CELLS = [(2, c, 2) for c in range(1, 9)] + [(0, 3, e) for e in range(1, 5)] + [(5, 0, 0), (1, 0, 3), (6, 4, 0)]
import os
files = sorted(f for f in os.listdir(d) if f.startswith('lvl') and f.endswith('.png') and 'b' not in f[3:-4])
files.sort(key=lambda f: int(f[3:-4]))
tiles = []
for f in files:
    i = int(f[3:-4]); b, c, e = CELLS[i] if i < len(CELLS) else (0, 0, 0)
    im = Image.open(f'{d}/{f}').convert('RGB').crop((96, 58, 736, 458)).resize((320, 200))
    ImageDraw.Draw(im).rectangle((0, 0, 190, 12), fill=(0, 0, 0)); ImageDraw.Draw(im).text((2, 1), f'cell {i}: base T{b+1} colours {c} enemies {e}', fill=(255, 255, 255))
    tiles.append(im)
rows = (len(tiles) + cols - 1) // cols
M = Image.new('RGB', (cols * 320, rows * 200))
for k, t in enumerate(tiles): M.paste(t, ((k % cols) * 320, (k // cols) * 200))
M.save(out); print(out, len(tiles))
