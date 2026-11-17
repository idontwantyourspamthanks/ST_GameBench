#!/usr/bin/env python3
"""Mockups of the speech bar (second black strip under the top bar), pixel-exact 320x200, saved 3x nearest.
Real frames: the shipped-HUD buffer captures work/hud/build/shots/{drv,drvsp,gno,gsp}_70000.bin (rows 16-64 of every frame are cleared to the sky,
exactly what hd_stage paints; the strip, text and face are then drawn by sbart.py with the game's own message font and the game's own face sprites)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbart import *
from PIL import ImageDraw, ImageFont

OUT = HERE
FONT = ImageFont.load_default()


def up(a, k=3):
    return Image.fromarray(a).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)


def caption(im, text, h=16):
    out = Image.new('RGB', (im.width, im.height + h), (20, 20, 20))
    out.paste(im, (0, h))
    ImageDraw.Draw(out).text((4, 2), text, fill=(255, 255, 255), font=FONT)
    return out


def frame(fr, text, n, face, h=STRIP_H):
    I = fr.clean()
    draw_strip(I, text, n, face, h=h)
    return fr.render(I)


def stock(fr):
    return fr.render(fr.idx)


MSG = dict((t, t) for _, t in messages())
T_TYPING = "Maybe you'd better\rpatrol the road for\rmoonshiners Pa."
T_LONG = "If you crash that\rthere motor again,\rI'll never get my\rprecious moonshine!"
T_SHORT = "Crazy fool!"
T_RACE = "Let's go Billy Joe!"
T_TWO = "Moonshine ain't for\rspreading all over\rthe road you idiot!"

if __name__ == '__main__':
    drvsp = Frame('drvsp'); drv = Frame('drv'); gsp = Frame('gsp'); gno = Frame('gno')
    # 1. typing / held / idle on the driving frame; the stock frame on top for the comparison
    n_typing = len("Maybe you'd better\rpatrol the r")
    scenes = [
        ('typing', drvsp, T_TYPING, n_typing, 0x2c, 'message typing (31 of 49 chars), mouth open'),
        ('held', drvsp, T_TYPING, len(T_TYPING), 0x2b, 'message held (2 lines, wrapped greedily at 37 columns)'),
        ('long', drvsp, T_LONG, len(T_LONG), 0x23, 'longest message (4 game lines -> 2 strip lines)'),
        ('short', drv, T_SHORT, len(T_SHORT), 0x21, 'short message'),
        ('idle', drv, None, 0, None, 'no message: empty strip (the sky keeps rows 42-64)'),
        ('standing', gsp, T_RACE, len(T_RACE), 0x2c, 'standing (time-out state), message held'),
    ]
    rows = []
    for name, fr, text, n, face, cap in scenes:
        a = frame(fr, text, n, face)
        Image.fromarray(a).save(OUT / f'raw_{name}.png')
        im = up(a)
        im.save(OUT / f'mock_{name}.png')
        print(name, 'ok')
    # 1b. annotated: what one typing pass draws into one buffer (green = drawn this pass, cyan = static strip, magenta = the sky rows that stay)
    cells = layout(T_TYPING)
    a = frame(drvsp, T_TYPING, n_typing, 0x2c)
    im = up(a).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov); k = 3
    dr.rectangle((0, 16 * k, 320 * k - 1, 42 * k - 1), outline=(0, 200, 255, 255), width=2)
    for i in [j for j in range(n_typing) if cells[j] is not None][-2:]:
        r, c = cells[i]
        x0 = TEXT_X0 + 8 * c; y0 = LINE_Y[r]
        dr.rectangle((x0 * k - 1, y0 * k - 1, (x0 + 8) * k, (y0 + 8) * k), outline=(0, 255, 0, 255), width=2)
    from gen_sb import difft
    dr.rectangle((FACE_X * k - 1, (FACE_Y + 11) * k - 1, (FACE_X + 16) * k, (FACE_Y + 19) * k), outline=(0, 255, 0, 255), width=2)
    dr.rectangle((0, 42 * k, 320 * k - 1, 65 * k - 1), outline=(255, 0, 255, 255), width=2)
    caption(Image.alpha_composite(im, ov).convert('RGB'), 'what a typing pass draws into one buffer: green = the characters this buffer lacks (the last 2 printable ones here) + the face mouth rows (2 of 24), cyan = the static strip (rows 16-41), magenta = the sky that stays (rows 42-64)').save(OUT / 'mock_annot.png')
    # 2. before / after sheet (stock shipped HUD with a message above, strip layout below) on the driving + speech frame
    st = stock(drvsp)
    a = frame(drvsp, T_TYPING, n_typing, 0x2c)
    sheet = Image.new('RGB', (960, 2 * (81 * 3 + 16)))
    sheet.paste(caption(up(st[:81]), 'BEFORE (shipped default): message typed into the sky, face 32x48, box erase of 49 rows'), (0, 0))
    sheet.paste(caption(up(a[:81]), 'AFTER (sb): second black strip rows 16-41 (26 rows), text 8x8 white, face 16x24, sky rows 42-64 kept'), (0, 81 * 3 + 16))
    sheet.save(OUT / 'mock_before_after.png')
    # 3. face states: all 22 frames half size (x6) with the full size beside them (x3) on the black strip colour
    cell_w, cell_h = 16 * 6 + 8, 24 * 6 + 8
    cols = 11
    sheetf = Image.new('RGB', (cols * cell_w, 2 * cell_h * 2 // 1), (0, 0, 0))
    rgb = np.array(drvsp.base, np.uint8)
    def to_rgb(I):
        return np.array([[rgb[v] if v < 15 else drvsp.sky[30] for v in row] for row in I], np.uint8)
    for k, idx in enumerate(FACE_IDS):
        f16 = face16(idx)
        f32 = face32(idx)
        r, c = divmod(k, cols)
        img16 = Image.fromarray(to_rgb(f16)).resize((16 * 6, 24 * 6), Image.NEAREST)
        sheetf.paste(img16, (c * cell_w + 4, r * 2 * cell_h + 4))
        img32 = Image.fromarray(to_rgb(np.where(f32 == 15, BG, f32))).resize((32 * 2, 48 * 2), Image.NEAREST)
        sheetf.paste(img32, (c * cell_w + 4, r * 2 * cell_h + 4 + 24 * 6 + 4 - 48 * 2 + 48 * 2 if False else r * 2 * cell_h + cell_h + 4))
    sheetf.save(OUT / 'mock_faces.png')
    # 4. wrap check: every message of the game fits in 2 strip lines at 37 columns
    bad = 0
    for _, t in messages():
        cells = layout(t)
        if any(c is None and t[i] not in ' \r' for i, c in enumerate(cells)):
            bad += 1
            print('OVERFLOW', repr(t))
    print('messages', len(messages()), 'overflowing', bad)
