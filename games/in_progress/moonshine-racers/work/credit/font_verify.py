"""Pixel-verify the font data (disk A $310be) against text the game itself draws: scan the dumped screens (work/credit/fontcap) for 8x8 cells that equal a font glyph
(covered pixels = edge|body bytes; edge pixels one colour, body pixels one colour) and print the text lines found."""
import re, glob, collections
from pathlib import Path
D = Path("work/credit/fontcap")
disk = open("work/floppy/disk_a.st", "rb").read()
font = disk[0x310BE:0x310BE + 95 * 16]
glyphs = {chr(32 + i): font[i * 16:i * 16 + 16] for i in range(95)}
cov = {}
for c, g in glyphs.items():
    if c == " ": continue
    cov.setdefault(tuple((g[2 * r] | g[2 * r + 1]) for r in range(8)), []).append(c)
for k in range(9):
    log = (D / f"{k}.txt").read_text()
    m = re.search(r"FF8200:\s+((?:[0-9a-f]{2} ){16})", log, re.I); v = bytes.fromhex(m.group(1).replace(" ", ""))
    base = (v[1] << 16) | (v[3] << 8)
    buf = (D / f"{k}_70000.bin").read_bytes() + (D / f"{k}_78000.bin").read_bytes()
    scr = buf[base - 0x70000:base - 0x70000 + 32000]
    def pix(x, y):
        o = y * 160 + (x // 16) * 8; b = 15 - (x % 16)
        return sum(((int.from_bytes(scr[o + 2 * i:o + 2 * i + 2], "big") >> b) & 1) << i for i in range(4))
    lines = {}; exact = 0; cells = 0
    for y in range(0, 193):
        row = []
        for cx in range(40):
            cellrows = tuple(sum((1 if pix(cx * 8 + bit, y + r) else 0) << (7 - bit) for bit in range(8)) for r in range(8))
            if cellrows in cov:
                g = glyphs[cov[cellrows][0]]
                ec, bc = set(), set()
                for r in range(8):
                    for bit in range(8):
                        e = g[2 * r] >> (7 - bit) & 1; b = g[2 * r + 1] >> (7 - bit) & 1
                        p = pix(cx * 8 + bit, y + r)
                        if e: ec.add(p)
                        elif b: bc.add(p)
                row.append((cx, cov[cellrows][0], len(ec) <= 1 and len(bc) <= 1))
        if len(row) >= 8: lines[y] = row
    if lines:
        y0 = min(lines)
        for y, row in sorted(lines.items()):
            if y == y0 or (y - 1) not in lines:
                s = "".join(c for _, c, _ in row)
                print(f"screen {k} (displayed buffer ${base:x}) y={y}: {len(row)} cells equal to a font glyph, two-colour rule holds for {sum(1 for _,_,ok in row if ok)}: {s!r}")
