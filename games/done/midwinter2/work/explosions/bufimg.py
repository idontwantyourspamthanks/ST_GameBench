"""Render ST low-res screen dumps (32000 B, 4 interleaved planes) to PNG; make contact sheets."""
import sys, struct
from pathlib import Path
from PIL import Image, ImageDraw
def pal_from(b):
    w = struct.unpack('>16H', b[:32]); p = []
    for v in w:
        def c(n): return ((n & 7) << 1 | (n >> 3 & 1)) * 17
        p.append((c(v >> 8 & 15), c(v >> 4 & 15), c(v & 15)))
    return p
def render(buf, pal):
    im = Image.new('RGB', (320, 200)); px = im.load()
    for y in range(200):
        for xb in range(20):
            o = y * 160 + xb * 8
            ws = struct.unpack('>4H', buf[o:o + 8])
            for bit in range(16):
                i = sum(((ws[p] >> (15 - bit)) & 1) << p for p in range(4))
                px[xb * 16 + bit, y] = pal[i]
    return im
def sheet(dirp, k0, k1, which, out, ncol=4, crop=(0, 28, 320, 130), scale=2, labels=True):
    dirp = Path(dirp); ims = []
    for k in range(k0, k1 + 1):
        f = dirp / f'f{k:02d}_{which}.bin'
        if not f.exists(): continue
        pal = pal_from((dirp / f'f{k:02d}_pal.bin').read_bytes()) if (dirp / f'f{k:02d}_pal.bin').exists() else pal_from(bytes.fromhex('000000300430004000250411054000500333044407400777003605220650' + '0057'))
        im = render(f.read_bytes(), pal).crop(crop)
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        if labels:
            ImageDraw.Draw(im).text((3, 3), f'{dirp.name} f{k:02d} {which}', fill=(255, 255, 255))
        ims.append(im)
    w, h = ims[0].size; nrow = (len(ims) + ncol - 1) // ncol
    s = Image.new('RGB', (w * ncol, h * nrow))
    for i, im in enumerate(ims): s.paste(im, ((i % ncol) * w, (i // ncol) * h))
    s.save(out)
if __name__ == '__main__':
    d, k0, k1, which, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    sheet(d, k0, k1, which, out, ncol=int(sys.argv[6]) if len(sys.argv) > 6 else 3)
