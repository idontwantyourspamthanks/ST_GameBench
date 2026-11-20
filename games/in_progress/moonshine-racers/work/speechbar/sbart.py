"""Speech-bar artwork + frame renderer shared by the mockups and the patch generator (MSRSpeechBar).
Fonts / face sprites come from the game RAM dump (work/dumps/ram_race_start.bin); frames from the shipped-HUD captures work/hud/build/shots."""
import sys, re, struct, collections
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'work/hud/design'))
from common import planar_to_idx, idx_to_planar, glyph8, RAM

SHOTS = ROOT / 'work/hud/build/shots'

# ---------------------------------------------------------------- layout (shared with the generator)
STRIP_Y0 = 16            # first strip row (the bar owns rows 0-15)
STRIP_H = 26             # rows 16..41
BG = 2                   # strip colour (black, plane 1 only) = the bar's colour
BODY = 14                # text body (palette A colour 14 = $777 white, set every pass by hd_stage)
SHADOW = 4               # text shadow ($333)
TEXT_X0 = 8              # first text cell x (px)
TEXT_W = 37              # columns per line
TEXT_L = 2               # lines
LINE_Y = (20, 30)        # first pixel row of each text line (8 rows each)
FACE_X = 304             # face 16x24, one 16-px group
FACE_Y = 17


def glyph_rows(ch, body=BODY, shadow=SHADOW, bg=BG):
    """8 rows x 8 px colour indices of one message-font glyph on the strip background."""
    rows = []
    for d1, d2 in glyph8(ord(ch)):
        r = []
        for b in range(8):
            a = (d1 >> (7 - b)) & 1
            c = (d2 >> (7 - b)) & 1
            r.append(body if c else (shadow if a else bg))
        rows.append(r)
    return rows


def face32(idx):
    """full-size face sprite (48 x 32 colour indices, 15 = transparent). Data layout: per row 4 planes x 2 groups (plane-major)."""
    o = 0x1b076 + 14 * idx
    ptr = int.from_bytes(RAM[o:o + 4], 'big')
    a = np.frombuffer(RAM[ptr:ptr + 768], '>u2').reshape(48, 4, 2)
    out = np.zeros((48, 32), np.uint8)
    for g in range(2):
        for p in range(4):
            w = a[:, p, g]
            for bit in range(16):
                out[:, g * 16 + bit] |= (((w >> (15 - bit)) & 1).astype(np.uint8) << p)
    return out


PAL_A = [(0, 0, 0), (1, 1, 1), (0, 0, 0), (7, 5, 4), (3, 3, 3), (3, 3, 0), (6, 6, 4), (6, 6, 6), (2, 2, 1), (4, 3, 2), (5, 4, 3), (7, 6, 5), (4, 1, 0), (5, 5, 0), (7, 7, 7)]   # palette A colours 0-14 ($3cd4.., colour 14 = $777)


def face16(idx, bg=BG):
    """half-size face: each 2x2 block with >= 2 opaque pixels -> the palette-A colour nearest to the mean RGB of its opaque pixels (all 15 colours
    are candidates); fewer opaque pixels -> background"""
    f = face32(idx)
    pal = np.array(PAL_A, float)
    out = np.full((24, 16), bg, np.uint8)
    for y in range(24):
        for x in range(16):
            op = [int(f[2 * y + a, 2 * x + b]) for a in (0, 1) for b in (0, 1) if f[2 * y + a, 2 * x + b] != 15]
            if len(op) < 2:
                continue
            m = pal[op].mean(axis=0)
            out[y, x] = int(np.argmin(((pal - m) ** 2).sum(axis=1)))
    return out


FACE_IDS = list(range(0x21, 0x37))


def messages():
    """every message record of the game RAM: text (with $0d line ends)"""
    res = []
    for m in re.finditer(rb'\x0e\x03\xb8\x14', RAM):
        s = m.end()
        e = RAM.index(b'\0', s)
        res.append((m.start(), RAM[s:e].decode('latin1')))
    return res


def layout(text, W=TEXT_W, L=TEXT_L):
    """per character index: (line, col) or None (separator / overflow).  Greedy word wrap, a $0d counts as a space; mirrors the asm."""
    cells = []
    col = row = 0
    ws = True
    for i, ch in enumerate(text):
        if ch in ' \r':
            if col != 0 and col < W:
                col += 1
            cells.append(None)
            ws = True
            continue
        if ws:
            wl = 0
            while i + wl < len(text) and text[i + wl] not in ' \r':
                wl += 1
            if col > 0 and col + wl > W:
                row += 1
                col = 0
        ws = False
        if col >= W:
            row += 1
            col = 0
        cells.append((row, col) if row < L else None)
        col += 1
    return cells


# ---------------------------------------------------------------- frames
class Frame:
    """a captured buffer of the shipped HUD (colour indices) + its per-row colours (palette A / road palette, colour 15 sky per row)"""
    def __init__(self, tag, buf='70000'):
        self.tag = tag
        self.idx = planar_to_idx((SHOTS / f'{tag}_{buf}.bin').read_bytes())
        w = struct.unpack('>38H', (SHOTS / f'{tag}_pal.bin').read_bytes())
        st2 = lambda v: tuple(((v >> s) & 7) * 36 for s in (8, 4, 0))
        self.base = [st2(w[8 + i]) for i in range(15)]
        self.road = [self.base[0]] + [st2(w[23 + i]) for i in range(14)]
        self.png = np.array(Image.open(SHOTS / f'{tag}_{buf}.png').convert('RGB'))[::3, ::3]
        self.sky = []
        for y in range(200):
            xs = np.nonzero(self.idx[y] == 15)[0]
            self.sky.append(tuple(int(v) for v in self.png[y, xs[0]]) if len(xs) else (self.sky[-1] if self.sky else (68, 170, 204)))
        # rows 0-64 are rendered from the indices with palette A (colour 15 = the row's sky colour); rows >= 65 are the captured pixels (road palette)
        assert (self.render(self.idx) == self.png).all(), tag

    def render(self, idx):
        out = self.png.copy()
        for y in range(65):
            lut = np.array([self.base[i] if i < 15 else self.sky[y] for i in range(16)], np.uint8)
            out[y] = lut[idx[y]]
        return out

    def clean(self):
        """frame without any message pixel: rows 16-64 all sky (what hd_stage paints)"""
        I = self.idx.copy()
        I[16:65, :] = 15
        return I


def put(I, x, y, rows):
    for dy, r in enumerate(rows):
        for dx, v in enumerate(r):
            I[y + dy, x + dx] = v


def draw_strip(I, text=None, n=0, face=None, W=TEXT_W, L=TEXT_L, h=STRIP_H):
    """black strip rows 16..16+h-1 + the first n characters of text + the face index"""
    I[STRIP_Y0:STRIP_Y0 + h, :] = BG
    if text is not None:
        cells = layout(text, W, L)
        for i in range(min(n, len(text))):
            c = cells[i]
            if c is None:
                continue
            r, col = c
            put(I, TEXT_X0 + 8 * col, LINE_Y[r], glyph_rows(text[i]))
    if face is not None:
        f = face16(face)
        I[FACE_Y:FACE_Y + 24, FACE_X:FACE_X + 16] = f
    return I
