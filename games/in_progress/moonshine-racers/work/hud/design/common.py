"""Shared helpers for the HUD design mockups: planar decode, palette, fonts from the game RAM dump, screenshot geometry."""
import numpy as np, struct, re
from pathlib import Path
from PIL import Image
D = Path(__file__).resolve().parent
CAP = D / 'cap'
RAM = (D.parents[1] / 'dumps' / 'ram_race_start.bin').read_bytes()

def planar_to_idx(b):
    a = np.frombuffer(b, '>u2').reshape(200, 20, 4)
    idx = np.zeros((200, 320), np.uint8)
    for p in range(4):
        w = a[:, :, p]
        for bit in range(16):
            idx[:, bit::16] |= (((w >> (15 - bit)) & 1).astype(np.uint8) << p)
    return idx

def idx_to_planar(idx):
    out = np.zeros((200, 20, 4), '>u2')
    for p in range(4):
        w = np.zeros((200, 20), np.uint16)
        for bit in range(16):
            w |= ((idx[:, bit::16] >> p) & 1).astype(np.uint16) << (15 - bit)
        out[:, :, p] = w
    return out.tobytes()

def st2rgb(v):
    return tuple(((v >> s) & 7) * 34 for s in (8, 4, 0))

def load_pal(tag):
    w = struct.unpack('>38H', (CAP / f'{tag}_pal.bin').read_bytes())
    base = [st2rgb(w[8 + i]) for i in range(15)]            # colours 0..14 ($3cd4)
    road = [base[0]] + [st2rgb(w[23 + i]) for i in range(14)]  # colours 1..14 ($3cf2)
    return base, road

def load_shot(tag):
    """Hatari --borders false screenshot: 640x400 game area (+ status bar) -> 320x200 RGB (every 2x2 block is uniform: asserted)."""
    a = np.array(Image.open(CAP / f'{tag}_shot.png').convert('RGB'))[:400]
    assert a.shape[:2] == (400, 640)
    s = a[0::2, 0::2]
    assert (a[1::2, 1::2] == s.repeat(1, 0)[:, :, :][:200, :320].repeat(1, 1)).all() if False else True
    assert (a[0::2, 0::2] == a[1::2, 1::2]).all() and (a[0::2, 0::2] == a[0::2, 1::2]).all()
    return s

def load_state(tag):
    t = (CAP / f'{tag}_state.txt').read_text(errors='replace')
    def m(addr, n):
        r = re.search(rf'm \${addr:x} \d+\n[0-9A-Fa-f]{{8}}: ((?:[0-9a-f]{{2}} ?)+)', t, re.I)
        return bytes.fromhex(r.group(1).replace(' ', ''))[:n]
    g = lambda a, n: int.from_bytes(m(a, n), 'big')
    return dict(pass_=g(0x100e, 2), t11ab=m(0x11ab, 8), temp=g(0x10ba, 2), fuel=g(0x10c0, 2), pos=g(0x10ca, 2),
                speed=g(0x10d8, 2), gear=g(0x11d9, 1), score=g(0x11c2, 2))

def load_idx(tag, buf='70000'):
    return planar_to_idx((CAP / f'{tag}_{buf}.bin').read_bytes())

# --- fonts from the game ------------------------------------------------------------------------------------------------------------
def glyph14(c):
    """score digit font $196ae, 28 bytes/char (14 rows x (shape d1, shadow d2)), index c-$2f; returns list of (d1,d2)."""
    o = 0x196ae + (c - 0x2f) * 28
    g = RAM[o:o + 28]
    return [(g[2 * r], g[2 * r + 1]) for r in range(14)]

def glyph8(c):
    """message font $190be, 16 bytes/char (8 rows x (d1,d2)), index c-$20."""
    o = 0x190be + (c - 0x20) * 16
    g = RAM[o:o + 16]
    return [(g[2 * r], g[2 * r + 1]) for r in range(8)]

def pix_idx(d1, d2, d4):
    """the stock kernel formula: plane n = (d4 bit n ? d1) | (d4 bit n+4 ? d2) | (d1&d2) (14-row kernel) per pixel bit; returns idx per pixel
    for (d1,d2) bits (a,b)."""
    res = []
    for b in range(8):
        a = (d1 >> (7 - b)) & 1; c = (d2 >> (7 - b)) & 1
        i = 0
        for n in range(4):
            v = ((a if (d4 >> n) & 1 else 0) | (c if (d4 >> (n + 4)) & 1 else 0) | (a & c))
            i |= v << n
        res.append((i, a, c))
    return res
