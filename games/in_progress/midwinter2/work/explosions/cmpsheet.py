import sys
from PIL import Image, ImageDraw
from bufimg import *
from pathlib import Path
# usage: cmpsheet.py out.png which k1,k2,... dirA dirB [dirC]
out, which, ks = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
dirs = [Path(d) for d in sys.argv[4:]]
rows = []
for k in ks:
    row = []
    for d in dirs:
        buf = (d / f'f{k:02d}_{which}.bin').read_bytes()
        pal = pal_from(bytes.fromhex('000000300430004000250411054000500333044407400777003605220650' + '0057')) if False else pal_from(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/explosions/win_pal.bin','rb').read())
        im = render(buf, pal).crop((0, 28, 320, 130)).resize((640, 204), Image.NEAREST)
        ImageDraw.Draw(im).text((3, 3), f'{d.name} f{k:02d} {which}', fill=(255, 255, 255))
        row.append(im)
    rows.append(row)
W, H = 640, 204
s = Image.new('RGB', (W * len(dirs), H * len(rows)))
for r, row in enumerate(rows):
    for c, im in enumerate(row): s.paste(im, (c * W, r * H))
s.save(out)
