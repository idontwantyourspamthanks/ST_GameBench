"""Decode the buffers saved by vblshots.py: python3 decode.py DIR  -> DIR/<vbl>.png (the DISPLAYED buffer with the palette at that VBL) + DIR/summary.txt"""
import sys, re, glob
from pathlib import Path
from PIL import Image
D = Path(sys.argv[1])
def regs(log):
    m = re.search(r"FF8200:\s+((?:[0-9a-f]{2} ){16})", log, re.I); v = bytes.fromhex(m.group(1).replace(" ", ""))
    base = (v[1] << 16) | (v[3] << 8)
    pal = []
    for a in ("FF8240", "FF8250"):
        m = re.search(a + r":\s+((?:[0-9a-f]{2} ){16})", log, re.I); pal += [int.from_bytes(bytes.fromhex(m.group(1).replace(" ", ""))[i:i+2], "big") for i in range(0, 16, 2)]
    return base, pal
def rgb(v): return (((v >> 8) & 7) * 36 + (v >> 11 & 1) * 0, ((v >> 4) & 7) * 36, (v & 7) * 36)
rows = []
for f in sorted(D.glob("*.log"), key=lambda p: int(p.stem)):
    n = int(f.stem); base, pal = regs(f.read_text())
    buf = (D / f"{n}_70000.bin").read_bytes() + (D / f"{n}_78000.bin").read_bytes()
    off = base - 0x70000
    scr = buf[off:off + 32000]
    im = Image.new("RGB", (320, 200))
    for y in range(200):
        for xb in range(20):
            o = y * 160 + xb * 8
            w = [int.from_bytes(scr[o + 2 * i:o + 2 * i + 2], "big") for i in range(4)]
            for b in range(16):
                im.putpixel((xb * 16 + b, y), rgb(pal[sum(((w[i] >> (15 - b)) & 1) << i for i in range(4))]))
    im.save(D / f"{n}.png")
    rows.append(f"{n} base ${base:x} pal {' '.join(f'{p:03x}' for p in pal[:16])} nonblack_rows_194_199 {sum(1 for y in range(194,200) for x in range(320) if im.getpixel((x,y)) != (0,0,0))}")
(D / "summary.txt").write_text("\n".join(rows) + "\n"); print("\n".join(rows))
