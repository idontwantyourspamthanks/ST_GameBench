#!/usr/bin/env python3
"""HUD layout mockups (pixel-exact 320x200, saved scaled 3x nearest).  Source frames = Hatari captures of the snapshots (capture.py):
colour indices from the dumped planar buffer ($70000), palette from the game's own tables ($3cd4 base, $3cf2 road, colour 15 = per-row sky
gradient taken from the screenshot).  Fonts = the game's own glyph tables ($196ae 8x14 digits, $190be 8x8 message font)."""
import sys, collections
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from common import *
from PIL import ImageDraw, ImageFont

RES = D.parent / 'res'
SKIPALL = {'drv': ('shots_race_start_f1c0+efc6+f214+f3b6+f430+f53c+11ef0+f90c+f620+f76a+f7f0+f22c+f134', 's70'),
           'drvsp': ('shots_race_start_f1c0+efc6+f214+f3b6+f430+f53c+11ef0+f90c+f620+f76a+f7f0+f22c+f134', 'sa0'),
           'gsp': ('shots_race_grid_f1c0+efc6+f214+f3b6+f430+f53c+11ef0+f90c+f620+f76a+f7f0+f22c+f134', 'se60'),
           'gno': ('shots_race_grid_f1c0+efc6+f214+f3b6+f430+f53c+11ef0+f90c+f620+f76a+f7f0+f22c+f134', 'se30')}
STOCK_BOXES = {'thermometer': (0, 9, 31, 64), 'minimap': (16, 15, 95, 64), 'dial': (80, 16, 111, 46), 'position': (80, 49, 111, 62),
               'score': (32, 1, 79, 14)}
TEXT_BOX = (112, 16, 271, 64); FACE_BOX = (272, 17, 303, 64)
SKY = 15

class Frame:
    def __init__(s, tag):
        s.tag = tag
        s.base, s.road = load_pal(tag)
        s.shot = load_shot(tag)
        s.st = load_state(tag)
        s.idx = load_idx(tag)                                  # displayed buffer ($ff8201/03 = $70000 in every capture)
        d, p = SKIPALL[tag]
        s.skip = planar_to_idx((RES / d / f'{p}_70000.bin').read_bytes())
        # palette switch row (colours 1-14 base -> road): first row >= 60 where the road palette explains the screenshot better, 3 rows in a row
        def rate(y, pal):
            m = n = 0
            for i in range(1, 15):
                xs = np.nonzero(s.idx[y] == i)[0]
                if len(xs):
                    n += len(xs); m += int((s.shot[y, xs] == np.array(pal[i])).all(axis=1).sum())
            return m / max(n, 1)
        s.sw = next(y for y in range(60, 198) if all(rate(y + k, s.road) > rate(y + k, s.base) for k in range(3)))
        # colour 15 per row (sky gradient / later bands) from the screenshot
        sky = []
        for y in range(200):
            xs = np.nonzero(s.idx[y] == 15)[0]
            if len(xs):
                c = collections.Counter(map(tuple, s.shot[y, xs])).most_common(1)[0][0]
                sky.append(tuple(int(v) for v in c))
            else:
                sky.append(sky[-1] if sky else (68, 170, 204))
        s.sky = sky
    def pal(s, y):
        return s.base if y < s.sw else s.road
    def render(s, idx=None):
        idx = s.idx if idx is None else idx
        out = np.zeros((200, 320, 3), np.uint8)
        for y in range(200):
            p = s.pal(y)
            lut = np.array([p[i] if i < 15 else s.sky[y] for i in range(16)], np.uint8)
            out[y] = lut[idx[y]]
        return out
    def stripped(s, bottom=True):
        """stock frame with every stock HUD element removed: top elements -> sky, clouds -> sky, bottom items -> the road (skip-all buffer)."""
        I = s.idx.copy()
        for (x0, y0, x1, y1) in STOCK_BOXES.values():
            I[y0:y1 + 1, x0:x1 + 1] = SKY
        cl = I[0:73] == 14
        if s.st['t11ab'][0] != 0:                            # a message is on screen: keep the portrait pixels (the face sprite may use colour 14)
            cl[17:65, 272:304] = False
        I[0:73][cl] = SKY
        if bottom:
            I[120:] = s.skip[120:]
        return I

# ----------------------------------------------------------------------------------------------------------------------------------- art
def dec14(ch, bg, d4=0xcd):
    """8x14 digit -> list of rows of idx (None = bg); stock kernel colours: shape-only 13, shadow-only 12 (d4=$cd); $c7 = end-bonus colours."""
    out = []
    for d1, d2 in glyph14(ord(ch)):
        row = []
        for i, a, c in pix_idx(d1, d2, d4):
            row.append(bg if (a and c) else i)
        out.append(row)
    return out

def dec8(ch, d4, bg=None):
    """8x8 message-font glyph: pixel = (d4 bit n ? d1) | (d4 bit n+4 ? d2) per plane; no pixel -> None (transparent)."""
    out = []
    for d1, d2 in glyph8(ord(ch)):
        row = []
        for b in range(8):
            a = (d1 >> (7 - b)) & 1; c = (d2 >> (7 - b)) & 1
            if not (a or c):
                row.append(bg); continue
            i = 0
            for n in range(4):
                i |= (((a if (d4 >> n) & 1 else 0) | (c if (d4 >> (n + 4)) & 1 else 0))) << n
            row.append(i)
        out.append(row)
    return out
LABEL = 0xb8      # the ticker's colours: cream body (idx 11) + dark outline (idx 8)
VALUE = 0xdc      # yellow body (13) + dark red outline (12), same as the score digits

class Canvas:
    def __init__(s, fr, I):
        s.fr = fr; s.rgb = fr.render(I); s.boxes = []
    def put(s, x, y, rows, bg=None):
        """rows: list of lists of idx (0..14 palette, 15 = sky, None = transparent)."""
        for dy, row in enumerate(rows):
            yy = y + dy
            if not 0 <= yy < 200: continue
            p = s.fr.pal(yy)
            for dx, i in enumerate(row):
                if i is None: continue
                s.rgb[yy, x + dx] = s.fr.sky[yy] if i == 15 else p[i]
    def rect(s, x0, y0, x1, y1, i):
        s.put(x0, y0, [[i] * (x1 - x0 + 1)] * (y1 - y0 + 1))
    def text8(s, x, y, txt, d4=LABEL, bg=None):
        for k, ch in enumerate(txt):
            if ch != ' ': s.put(x + 8 * k, y, dec8(ch, d4, bg))
    def digits14(s, x, y, txt, bg, d4=0xcd):
        for k, ch in enumerate(txt):
            if ch != ' ': s.put(x + 8 * k, y, dec14(ch, bg, d4))
            else: s.put(x + 8 * k, y, [[bg] * 8] * 14)

def num(n, w, blank=True):
    t = str(n).rjust(w)
    return t[-w:]

def cup_icon(w, h, bg):
    """small goblet: tan body (6) with dark outline (8) and rim (3), w x h."""
    rows = []
    for r in range(h):
        inset = int(round((w // 2 - 2) * r / max(h - 1, 1) * 0.8))
        row = [bg] * w
        for x in range(inset, w - inset):
            edge = x in (inset, w - inset - 1) or r in (0, h - 1)
            row[x] = 8 if edge else (3 if r == 1 else 6)
        rows.append(row)
    return rows

def dial_half(fr, hi, bg):
    """32x31 stock dial (taken from the grid frame, hand removed) -> 16x16 by 2x2 majority, plus a 4-px hand at the clock angle."""
    g = load_idx('gno')
    face = g[16:48, 80:112].copy()
    face[face == 12] = 7; face[(face == 2)] = 7          # remove the stock hand (black 2 / shadow 12 inside the face)
    face[:, :] = np.where(np.arange(32)[None, :] % 1 == 0, face, face)
    out = []
    for y in range(16):
        row = []
        for x in range(16):
            blk = [face[2 * y + a, 2 * x + b] for a in (0, 1) for b in (0, 1)]
            cnt = collections.Counter(blk)
            sky_n = cnt.get(15, 0)
            if sky_n >= 2: row.append(bg)
            else:
                c = [k for k, v in cnt.most_common() if k != 15]
                dark = [k for k in c if k in (4, 8, 1)]
                row.append(dark[0] if dark and cnt[dark[0]] >= 1 and len(c) > 1 and c[0] == 7 and cnt[dark[0]] >= 2 else c[0])
        out.append(row)
    import math
    a = 2 * math.pi * (0x80 - hi) / 256
    cx, cy = 7.5, 7.5
    for t in np.linspace(0, 1, 20):
        px = int(round(cx + math.sin(a) * 4.5 * t)); py = int(round(cy + math.sin(a + math.pi / 2) * 4.5 * t))
        out[py][px] = 2
    return out

def hi_of(st):
    return ((st['pass_'] * 0x2798) >> 16) & 0xff

def bar_gauge(cv, x, y, w, h, level, full=28, bar_bg=2):
    cv.rect(x - 1, y - 1, x + full, y + h, 7)                    # frame (palette 7 grey)
    cv.rect(x, y, x + full - 1, y + h - 1, 8)                    # empty
    if level: cv.rect(x, y, x + level - 1, y + h - 1, 13)         # fuel

# ----------------------------------------------------------------------------------------------------------------------------------- layouts
def layout_A(fr):
    st = fr.st; cv = Canvas(fr, fr.stripped()); BG = 2
    cv.rect(0, 0, 319, 15, BG); F = []      # (name, box, kind)
    F.append(('bar background (static, once per buffer)', (0, 0, 319, 15), 'static'))
    sc = str(st['score']).rjust(5)
    cv.digits14(8, 1, sc, BG); cv.digits14(48, 1, '0', BG)
    F += [('SCORE 5 digits', (8, 1, 47, 14), 'dyn'), ('score last 0 (static)', (48, 1, 55, 14), 'static')]
    cv.put(64, 0, dial_half(fr, hi_of(st), BG)); F.append(('DIAL 16x16', (64, 0, 79, 15), 'dyn'))
    cv.text8(88, 4, '#', LABEL, BG); cv.digits14(96, 1, num(st['pos'], 2), BG); F += [("'#' (static)", (88, 4, 95, 11), 'static'), ('POSITION 2 digits', (96, 1, 111, 14), 'dyn')]
    cv.digits14(120, 1, num(st['speed'], 3), BG); cv.text8(152, 4, 'MPH', LABEL, BG); F += [('SPEED 3 digits', (120, 1, 143, 14), 'dyn'), ('MPH (static)', (152, 4, 175, 11), 'static')]
    cv.text8(184, 4, 'G', LABEL, BG); cv.digits14(192, 1, '1' if st['gear'] == 0 else '2', BG); F += [('G (static)', (184, 4, 191, 11), 'static'), ('GEAR 1 digit', (192, 1, 199, 14), 'dyn')]
    cv.text8(208, 4, 'T', LABEL, BG); cv.digits14(216, 1, num(st['temp'], 2), BG); F += [('T (static)', (208, 4, 215, 11), 'static'), ('TEMP 2 digits', (216, 1, 231, 14), 'dyn')]
    cv.put(240, 1, cup_icon(16, 14, BG)); bar_gauge(cv, 264, 5, 28, 6, st['fuel']); F += [('cup icon (static)', (240, 1, 255, 14), 'static'), ('TURBO gauge fill', (264, 5, 291, 10), 'dyn'), ('gauge frame (static)', (263, 4, 292, 11), 'static')]
    return cv, F, dict(name='A', h=16)

def layout_B(fr):
    st = fr.st; cv = Canvas(fr, fr.stripped()); BG = 4
    cv.rect(0, 0, 319, 9, BG); F = [('thin bar background (static)', (0, 0, 319, 9), 'static')]
    cv.text8(8, 1, 'SCORE', LABEL, BG); cv.text8(56, 1, str(st['score']).rjust(5), VALUE, BG); cv.text8(96, 1, '0', VALUE, BG)
    F += [('SCORE (static label)', (8, 1, 47, 8), 'static'), ('SCORE 5 digits', (56, 1, 95, 8), 'dyn'), ('score last 0', (96, 1, 103, 8), 'static')]
    cv.text8(112, 1, 'MPH', LABEL, BG); cv.text8(144, 1, num(st['speed'], 3), VALUE, BG)
    F += [('MPH (static)', (112, 1, 135, 8), 'static'), ('SPEED 3 digits', (144, 1, 167, 8), 'dyn')]
    cv.text8(184, 1, 'GEAR', LABEL, BG); cv.text8(224, 1, '1' if st['gear'] == 0 else '2', VALUE, BG)
    F += [('GEAR (static)', (184, 1, 215, 8), 'static'), ('GEAR digit', (224, 1, 231, 8), 'dyn')]
    cv.text8(248, 1, 'TEMP', LABEL, BG); cv.text8(288, 1, num(st['temp'], 2), VALUE, BG)
    F += [('TEMP (static)', (248, 1, 279, 8), 'static'), ('TEMP 2 digits', (288, 1, 303, 8), 'dyn')]
    # hanging cluster on the sky (static background = sky, nothing masked)
    cv.put(0, 12, dial_half(fr, hi_of(st), SKY)); F.append(('DIAL 16x16 (on sky)', (0, 12, 15, 27), 'dyn'))
    cv.text8(24, 14, 'POS', LABEL); cv.text8(48, 14, num(st['pos'], 2), VALUE)
    F += [('POS (static, sky)', (24, 14, 47, 21), 'static'), ('POSITION 2 digits', (48, 14, 63, 21), 'dyn')]
    cv.put(24, 22, cup_icon(8, 8, SKY)); bar_gauge(cv, 40, 24, 28, 4, st['fuel'])
    F += [('cup icon (static)', (24, 22, 31, 29), 'static'), ('TURBO gauge fill', (40, 24, 67, 27), 'dyn'), ('gauge frame (static)', (39, 23, 68, 28), 'static')]
    return cv, F, dict(name='B', h=10)

def layout_C(fr):
    st = fr.st; cv = Canvas(fr, fr.stripped()); BG = 2
    cv.rect(0, 0, 111, 33, BG); F = [('panel background 112x34 (static)', (0, 0, 111, 33), 'static')]
    cv.text8(8, 1, 'SCORE', LABEL, BG); cv.text8(56, 1, str(st['score']).rjust(5), VALUE, BG); cv.text8(96, 1, '0', VALUE, BG)
    F += [('SCORE 5 digits', (56, 1, 95, 8), 'dyn')]
    cv.text8(8, 9, 'SPD', LABEL, BG); cv.text8(40, 9, num(st['speed'], 3), VALUE, BG); cv.text8(72, 9, 'G', LABEL, BG); cv.text8(80, 9, '1' if st['gear'] == 0 else '2', VALUE, BG)
    F += [('SPEED 3 digits', (40, 9, 63, 16), 'dyn'), ('GEAR digit', (80, 9, 87, 16), 'dyn')]
    cv.text8(8, 17, 'TMP', LABEL, BG); cv.text8(40, 17, num(st['temp'], 2), VALUE, BG); cv.text8(64, 17, '#', LABEL, BG); cv.text8(72, 17, num(st['pos'], 2), VALUE, BG)
    F += [('TEMP 2 digits', (40, 17, 55, 24), 'dyn'), ('POSITION 2 digits', (72, 17, 87, 24), 'dyn')]
    cv.put(8, 25, cup_icon(8, 8, BG)); bar_gauge(cv, 24, 27, 28, 4, st['fuel'])
    F += [('TURBO gauge fill', (24, 27, 51, 30), 'dyn')]
    cv.put(96, 9, dial_half(fr, hi_of(st), BG)); F.append(('DIAL 16x16', (96, 9, 111, 24), 'dyn'))
    return cv, F, dict(name='C', h=34)

LAYOUTS = {'A': layout_A, 'B': layout_B, 'C': layout_C}

def up(a, k=3):
    return Image.fromarray(a).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)

def annotate(cv, F, k=3):
    im = up(cv.rgb, k).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for name, (x0, y0, x1, y1), kind in F:
        col = (0, 255, 0, 255) if kind == 'dyn' else (0, 200, 255, 255)
        if kind == 'static' and (x1 - x0 > 100 or y1 - y0 > 20 and 'background' in name):
            d.rectangle((x0 * k, y0 * k, (x1 + 1) * k - 1, (y1 + 1) * k - 1), outline=(0, 200, 255, 255))
        elif kind == 'dyn':
            d.rectangle((x0 * k - 1, y0 * k - 1, (x1 + 1) * k, (y1 + 1) * k), outline=col)
    return Image.alpha_composite(im, ov).convert('RGB')


FONT = ImageFont.load_default()
def caption(im, text, h=16):
    out = Image.new('RGB', (im.width, im.height + h), (20, 20, 20)); out.paste(im, (0, h))
    ImageDraw.Draw(out).text((4, 2), text, fill=(255, 255, 255), font=FONT)
    return out

TITLES = {'A': 'A: full 16-row strip, big digits', 'B': 'B: thin 10-row strip (8x8 game font) + cluster on the sky', 'C': 'C: compact 112x34 panel (not a full-width bar)'}
if __name__ == '__main__':
    out = D
    names = {'drv': 'driving, no speech (race_start pass 0x70)', 'drvsp': 'driving, speech typing + face (race_start pass 0xa0)',
             'gsp': 'standing, speech held + face (race_grid pass 0xe60)', 'gno': 'standing, no speech (race_grid pass 0xe30)'}
    for tag in ['drv', 'drvsp', 'gsp', 'gno']:
        fr = Frame(tag)
        stock = fr.render()
        Image.fromarray(stock).save(out / 'ref' / f'{tag}_stock320.png')
        print(tag, 'switch row', fr.sw, 'pass', hex(fr.st['pass_']), fr.st)
        rows = [caption(up(stock[:81]), 'STOCK HUD  - ' + names[tag])]
        for L, fn in LAYOUTS.items():
            cv, F, meta = fn(fr)
            up(cv.rgb).save(out / f'layout_{L}_{tag}.png')
            caption(annotate(cv, F), TITLES[L] + '  [green = redrawn on change, cyan = static background]  - ' + names[tag]).save(out / f'layout_{L}_{tag}_annot.png')
            rows.append(caption(up(cv.rgb[:81]), TITLES[L] + ' - ' + names[tag]))
        strip = Image.new('RGB', (960, sum(r.height for r in rows)))
        y = 0
        for r in rows: strip.paste(r, (0, y)); y += r.height
        strip.save(out / f'strip_{tag}.png')
        Image.fromarray(stock).resize((960, 600), Image.NEAREST).save(out / f'stock_{tag}.png')
    import shutil
    for L in LAYOUTS: shutil.copy(out / f'layout_{L}_drvsp.png', out / f'layout_{L}.png')
