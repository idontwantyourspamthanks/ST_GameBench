#!/usr/bin/env python3
"""Generator of the new HUD blob data (patch hd_stage, layout A of work/notes/hud_design.md): top strip bitmap, glyph strips, half dial images, turbo gauge
images, cell offsets, decimal table.  Fonts come from the stock game's RAM (work/dumps/ram_race_start.bin: 8x14 digit font $196ae, 8x8 message font $190be).

    python3 tools/msrhudgen.py data      # print the assembler data section (used by patches/hd_stage.s through `include`-free generation: see `emit`)
    python3 tools/msrhudgen.py mock OUT.png   # render the strip (palette A rows 0-15) for a quick look

Colours = palette A indices ($3cd4: 0:000 1:111 2:000 3:754 4:333 5:330 6:664 7:666 8:221 9:432 10:543 11:765 12:410 13:550 14:667 -> $777 by the blob).
"""
import sys, math, struct
from pathlib import Path
import numpy as np

GAME = Path(__file__).resolve().parent.parent
RAM = (GAME / "work/dumps/ram_race_start.bin").read_bytes()
BG, WHITE, GREY, DARK, YEL, DRED, SALMON, FRAME = 2, 14, 7, 4, 13, 12, 3, 7
PAL = {0: 0x000, 1: 0x111, 2: 0x000, 3: 0x754, 4: 0x333, 5: 0x330, 6: 0x664, 7: 0x666, 8: 0x221, 9: 0x432, 10: 0x543, 11: 0x765, 12: 0x410, 13: 0x550, 14: 0x777}

# layout (x in pixels; y of the 8x14 digits = 1, of the 8x8 labels = 4)
X_SCORE = [8, 16, 24, 32, 40, 48]          # 5 digits + constant 0
X_POS = [96, 104]
X_SPEED = [120, 128, 136]
X_GEAR = [192]
X_TEMP = [216, 224]
X_DIAL = 64
LABELS = [(88, '#'), (152, 'MPH'), (184, 'G'), (208, 'T')]
X_CUP = 240
GAUGE = dict(x0=264, w=28, y0=5, h=6)       # fill 264..291, rows 5..10, frame 263..292 x 4..11
GX = 256                                    # gauge group base (16-pixel groups 16..18 = x 256..303)

def glyph14(c):
    o = 0x196ae + (c - 0x2f) * 28
    g = RAM[o:o + 28]
    return [(g[2 * r], g[2 * r + 1]) for r in range(14)]

def glyph8(c):
    o = 0x190be + (c - 0x20) * 16
    g = RAM[o:o + 16]
    return [(g[2 * r], g[2 * r + 1]) for r in range(8)]

def digit_rows(ch, body, shadow):
    """8x14 digit: a only -> body, c only -> shadow, both / none -> bg (the stock kernel's d1&d2 'hole' becomes the strip colour)."""
    out = []
    for d1, d2 in glyph14(ord(ch)):
        row = []
        for b in range(8):
            a = (d1 >> (7 - b)) & 1; c = (d2 >> (7 - b)) & 1
            row.append(body if (a and not c) else shadow if (c and not a) else BG)
        out.append(row)
    return out

def label_rows(ch, body):
    out = []
    for d1, d2 in glyph8(ord(ch)):
        out.append([body if (d2 >> (7 - b)) & 1 else None for b in range(8)])
    return out

SETS = [(WHITE, DARK), (SALMON, DRED), (YEL, DRED)]          # normal, hot (temperature >= 28), highlight (score during the end-of-race bonus, $11c6)

def blank_rows():
    return [[BG] * 8 for _ in range(14)]

def strip_bytes(rows):
    """14 rows x 4 plane bytes (movep.l order: plane 0 byte first)."""
    out = bytearray()
    for row in rows:
        for p in range(4):
            v = 0
            for b in range(8):
                v = (v << 1) | ((row[b] >> p) & 1)
            out.append(v)
    return bytes(out)

def glyph_table():
    """33 strips of 64 bytes: set*11 + code (code 0-9 digits, 10 blank)."""
    t = bytearray()
    for body, shadow in SETS:
        for code in range(11):
            rows = blank_rows() if code == 10 else digit_rows(str(code), body, shadow)
            t += strip_bytes(rows).ljust(64, b'\0')
    return bytes(t)

def idx_rows_to_planar(img):
    """img: (h, 320) palette indices -> bytes, 160 per row (word per plane per 16 px group)."""
    out = bytearray()
    for row in img:
        for g in range(20):
            for p in range(4):
                v = 0
                for b in range(16):
                    v = (v << 1) | ((int(row[g * 16 + b]) >> p) & 1)
                out += struct.pack('>H', v)
    return bytes(out)

def cup_icon():
    """16x14 goblet: white rim and outline, yellow turbo fill."""
    rows = []
    for r in range(14):
        row = [BG] * 16
        if r == 0:
            for x in range(1, 15): row[x] = WHITE
        elif r < 12:
            inset = 1 + (r - 1) * 5 // 11
            for x in range(inset, 16 - inset):
                row[x] = WHITE if x in (inset, 15 - inset) or r == 11 else (YEL if r >= 3 else BG)
        else:
            for x in range(5, 11): row[x] = WHITE
        rows.append(row)
    return rows

def bar_image():
    img = np.full((16, 320), BG, np.uint8)
    def put(x, y, rows):
        for dy, row in enumerate(rows):
            for dx, v in enumerate(row):
                if v is not None: img[y + dy, x + dx] = v
    put(X_SCORE[5], 1, digit_rows('0', *SETS[0]))
    for x, txt in LABELS:
        for k, ch in enumerate(txt): put(x + 8 * k, 4, label_rows(ch, WHITE))
    put(X_CUP, 1, cup_icon())
    g = GAUGE
    img[4, g['x0'] - 1:g['x0'] + g['w'] + 1] = FRAME
    img[11, g['x0'] - 1:g['x0'] + g['w'] + 1] = FRAME
    img[5:11, g['x0'] - 1] = FRAME
    img[5:11, g['x0'] + g['w']] = FRAME
    img[5:11, g['x0']:g['x0'] + g['w']] = DARK
    return img

def gauge_table(bar):
    """29 fill levels x 24 bytes: the 3 sixteen-pixel groups x 4 planes (x 256..303) of one interior gauge row (frame sides included)."""
    t = bytearray()
    g = GAUGE
    for n in range(29):
        full = np.full((1, 320), BG, np.uint8)
        full[0, GX:GX + 48] = bar[5, GX:GX + 48]
        full[0, g['x0']:g['x0'] + n] = YEL
        t += idx_rows_to_planar(full)[GX // 16 * 8:GX // 16 * 8 + 24]
    return bytes(t)

def dial_images():
    """32 hand angles (hand = hi byte of the clock >> 3), 16x16 stopwatch icon on the strip colour; 128 bytes each (rows x 8 bytes, planar)."""
    out = bytearray()
    for n in range(32):
        im = np.full((16, 16), BG, np.uint8)
        cx, cy, r = 7.5, 9.0, 6.6
        for y in range(16):
            for x in range(16):
                d = math.hypot(x - cx, y - cy)
                if d <= r + 0.45 and y >= 2: im[y, x] = GREY if d >= r - 0.9 else WHITE      # white face, grey rim
        im[0:2, 6:10] = GREY                                   # crown
        im[2, 7:9] = GREY
        a = 2 * math.pi * (n * 8) / 256
        for t in np.linspace(0, 1, 24):
            px = int(round(cx + math.sin(a) * 4.6 * t)); py = int(round(cy - math.cos(a) * 4.6 * t))
            im[py, px] = BG                                    # black hand
        im[int(round(cy)), int(round(cx))] = BG
        full = np.full((16, 320), BG, np.uint8); full[:, 0:16] = im
        pl = idx_rows_to_planar(full)
        for r_ in range(16): out += pl[r_ * 160:r_ * 160 + 8]
    return bytes(out)

def cell_offsets():
    def off(x): xi = x // 8; return (xi >> 1) * 8 + (xi & 1) + 160
    return {k: [off(x) for x in v] for k, v in dict(score=X_SCORE, pos=X_POS, speed=X_SPEED, gear=X_GEAR, temp=X_TEMP).items()}

def bcd100():
    return bytes(b for n in range(100) for b in (n // 10, n % 10))

def render(bar_planar, path):
    from PIL import Image
    a = np.frombuffer(bar_planar, '>u2').reshape(16, 20, 4)
    idx = np.zeros((16, 320), np.uint8)
    for p in range(4):
        for bit in range(16):
            idx[:, bit::16] |= (((a[:, :, p] >> (15 - bit)) & 1).astype(np.uint8) << p)
    rgb = np.zeros((16, 320, 3), np.uint8)
    for i, v in PAL.items():
        rgb[idx == i] = [((v >> s) & 7) * 36 for s in (8, 4, 0)]
    Image.fromarray(rgb).resize((960, 48), Image.NEAREST).save(path)

def dump_dc(data, per=16):
    lines = []
    for i in range(0, len(data), per):
        lines.append("        dc.b    " + ",".join("$%02x" % b for b in data[i:i + per]))
    return "\n".join(lines)

def build():
    bar = bar_image()
    return dict(bar=idx_rows_to_planar(bar), glyphs=glyph_table(), gauge=gauge_table(bar), dial=dial_images(), cells=cell_offsets(), bcd=bcd100(), barimg=bar)

def main_():
    d = build()
    if sys.argv[1] == "mock":
        render(d['bar'], sys.argv[2])
    elif sys.argv[1] == "data":
        print(len(d['bar']), len(d['glyphs']), len(d['gauge']), len(d['dial']))



# ---------------------------------------------------------------------------------------------------------------------------------- gate model
def _cell(img, x, code):
    """code' = set*11 + digit (10 = blank): draw an 8x14 cell at (x, 1)."""
    st, c = divmod(code, 11)
    rows = blank_rows() if c == 10 else digit_rows(str(c), *SETS[st])
    for dy, row in enumerate(rows):
        for dx, v in enumerate(row): img[1 + dy, x + dx] = v

def expected_strip(sh):
    """The strip (16 x 320 palette indices) the HUD must show when the shadow struct `sh` (64 bytes of S0/S1) describes the buffer (gate model, independent of the 68000 code)."""
    img = bar_image().copy()
    for x, c in zip(X_SCORE, sh[6:12]): _cell(img, x, c)
    for x, c in zip(X_POS, sh[14:16]): _cell(img, x, c)
    for x, c in zip(X_SPEED, sh[18:21]): _cell(img, x, c)
    _cell(img, X_GEAR[0], sh[1])
    for x, c in zip(X_TEMP, sh[24:26]): _cell(img, x, c)
    n = sh[26]
    # the dial image of angle n (same generator as the table): decode from the planar table
    t = dial_images()[n * 128:(n + 1) * 128]
    for y in range(16):
        for x in range(16):
            v = 0
            for pl in range(4):
                w = (t[y * 8 + pl * 2] << 8) | t[y * 8 + pl * 2 + 1]
                v |= ((w >> (15 - x)) & 1) << pl
            img[y, X_DIAL + x] = v
    g = GAUGE
    img[5:11, g['x0']:g['x0'] + g['w']] = DARK
    img[5:11, g['x0']:g['x0'] + sh[27]] = YEL
    return img

def digits5(v):
    """the same 5 decimal digit codes conv5 produces (leading zeros -> 10)."""
    d = [(v // 10 ** k) % 10 for k in (4, 3, 2, 1, 0)]
    for i in range(4):
        if d[i] == 0: d[i] = 10
        else: break
    return d

def model_shadow(ram):
    """What the HUD must have drawn, from game RAM (bytes-like, absolute addresses): the shadow struct fields as a bytes(64)."""
    w = lambda a: (ram[a] << 8) | ram[a + 1]
    sw = lambda a: w(a) - 65536 if w(a) & 0x8000 else w(a)
    sh = bytearray(64)
    sc = w(0x11c2); st = 22 if ram[0x11c6] else 0
    dd = digits5(sc)
    sh[6:11] = bytes(c + st for c in dd); sh[11] = st
    pos = sw(0x10ca); pos = 1 if pos <= 0 else min(pos, 99); sh[14:16] = bytes(c for c in digits5(pos)[3:])
    sp = max(sw(0x10d8), 0); sh[18:21] = bytes(digits5(sp)[2:])
    sh[1] = 2 if ram[0x11d9] else 1
    t = max(sw(0x10ba), 0); t = min(t, 35); hot = 11 if t >= 28 else 0
    sh[24:26] = bytes(c + hot for c in digits5(t)[3:])
    clk = (ram[0x10ce] << 24) | (ram[0x10cf] << 16) | (ram[0x10d0] << 8) | ram[0x10d1]
    if clk & 0x80000000 or clk == 0: clk = 0
    clk = min(clk, 0xff0000)
    sh[26] = (clk >> 16 & 0xff) >> 3
    f = max(sw(0x10c0), 0); sh[27] = min(f, 28)
    return bytes(sh)

# ---------------------------------------------------------------------------------------------------------------------------------- assembler
HB = 0xBB000
ADDR = dict(BAR=0xBB800, GL=0xBC200, GAUGE=0xBCA40, CELLS=0xBCD00, BCD=0xBCD20, S0=0xBCF00, S1=0xBCF40, TMP=0xBCF80, DIAL=0xBD000)

HEADER = """; name: hd_stage
; default: yes
; site: $ef7a
; orig: 2a7810084eb9
; data: $BCF00 160
; doc: New top-bar HUD (layout A): one black 16-row strip with score, clock, race position, speed (MPH), gear, engine temperature and turbo gauge, drawn once per change; the minimap, speedometer, gear lever, thermometer, cup, big dial and the stage's cloud erase/draw are gone.
; note: GENERATED by tools/msrhudgen.py (python3 tools/msrhudgen.py emit > patches/hd_stage.s); edit the generator, not this file.  Moonshine Racers HUD rebuild, work/notes/hud_build.md.
; note: Site $ef7a (the HUD stage, called once per pass from $7b4c): `movea.l $1008.w,a5 / jsr` -> `jmp NEWHUD.l`.  NEWHUD = TOPBAR, the message ticker $11ef0 (its state machine gates the race-end flow: it must keep running),
; note: the face $f90c and the hit/sound part of the old cup routine $f620 ($11ce flag, $11cf slosh counter, sound $36).  Nothing else of the old stage is called.
; note: TOPBAR draws into the back buffer ($1008) and keeps, per buffer ($70000 / $78000), a shadow of what that buffer shows: a field is redrawn only when its value differs from the shadow of the buffer being drawn.
; note: First pass per buffer after the race init (hd_init clears the `painted` bytes; a freshly loaded patch starts with them clear): the strip bitmap (rows 0-15), then the sky colour (all planes set) over rows 16-64 of the whole width.
; note: Entries: $BB000 TOPBAR (a5 = buffer; used by the extra frames of mg_sync, and of mx_sync/mf_sync), $BB004 NEWHUD (the stage), $BB008 HIT (the $f620 sound/flag part).  Palette A colour 14 is set to $777 every pass (white: the clouds, its only other user in rows 0-73, are gone).
; note: Blob $BB000-$BB7FF code, $BB800 strip bitmap, $BC200 glyph strips (3 sets x 11 x 64 B), $BCA40 gauge rows, $BCD00 cell offsets, $BCD20 decimal pairs, $BCF00/$BCF40 shadows, $BCF80 scratch, $BD000 dial images.
"""

CODE = r"""
        org     $ef7a
        jmp     $BB004.l

        org     $BB000
        bra.w   topbar
        bra.w   newhud
        bra.w   hit

; ---- the stage ------------------------------------------------------------------------------------------------------------------
newhud: movea.l $1008.w,a5
        bsr.w   topbar
        movea.l $1008.w,a5
        jsr     $11ef0.l                ; message ticker (its state machine gates the race-end flow)
        jsr     $f90c.l                 ; talking face
        bsr.w   hit
        movea.l $1008.w,a5
        rts

; the old cup routine's non-display part: flag $11ce (hit) -> sound $36, slosh counter $11cf (exactly as $f620/$f6f8 evolve them)
hit:    move.w  $10c0.w,d2
        bpl.s   .h1
        moveq   #0,d2
.h1:    cmp.w   #28,d2
        ble.s   .h2
        moveq   #28,d2
.h2:    tst.b   $11cf.w
        bne.s   .anim
        tst.b   $11ce.w
        beq.s   .out
        movem.l d0-d7/a0-a6,-(a7)
        moveq   #$36,d0
        moveq   #2,d1
        jsr     $7bb2.l
        movem.l (a7)+,d0-d7/a0-a6
.anim:  clr.b   $11ce.w
        cmp.w   #15,d2
        bcc.s   .adv
        clr.b   $11cf.w
        rts
.adv:   moveq   #0,d0
        move.b  $11cf.w,d0
        addq.b  #1,d0
        cmp.b   #9,d0
        bcs.s   .st
        moveq   #0,d0
.st:    move.b  d0,$11cf.w
.out:   rts

; ---- TOPBAR: a5 = back buffer ----------------------------------------------------------------------------------------------------
topbar: move.w  #$0777,$3cf0.w          ; palette A colour 14 = white
        lea     S0.l,a4
        move.l  a5,d0
        btst    #15,d0
        beq.s   .sel
        lea     64(a4),a4               ; $78000: second shadow
.sel:   tst.b   (a4)
        bne.s   .ok
        bsr.w   paint
.ok:
; score: 5 digits + constant 0, colour set by $11c6
        moveq   #0,d0
        move.w  $11c2.w,d0
        moveq   #0,d1
        tst.b   $11c6.w
        beq.s   .s0
        moveq   #22,d1
.s0:    cmp.w   2(a4),d0
        bne.s   .sc
        cmp.b   4(a4),d1
        beq.s   .sdone
.sc:    move.w  d0,2(a4)
        move.b  d1,4(a4)
        lea     TMP.l,a1
        bsr.w   conv5
        clr.b   5(a1)
        lea     6(a4),a2
        lea     CELLS.l,a3
        moveq   #5,d7
        bsr.w   cells
.sdone:
; race position (clamped 1..99), 2 digits
        moveq   #0,d0
        move.w  $10ca.w,d0
        bgt.s   .p1
        moveq   #1,d0
.p1:    cmp.w   #99,d0
        ble.s   .p2
        moveq   #99,d0
.p2:    cmp.w   12(a4),d0
        beq.s   .pdone
        move.w  d0,12(a4)
        lea     TMP.l,a1
        bsr.w   conv5
        lea     3(a1),a1
        lea     14(a4),a2
        lea     CELLS+12.l,a3
        moveq   #1,d7
        moveq   #0,d1
        bsr.w   cells
.pdone:
; speed: high word of $10d8, 3 digits
        moveq   #0,d0
        move.w  $10d8.w,d0
        bpl.s   .v1
        moveq   #0,d0
.v1:    cmp.w   16(a4),d0
        beq.s   .vdone
        move.w  d0,16(a4)
        lea     TMP.l,a1
        bsr.w   conv5
        lea     2(a1),a1
        lea     18(a4),a2
        lea     CELLS+16.l,a3
        moveq   #2,d7
        moveq   #0,d1
        bsr.w   cells
.vdone:
; gear: $11d9 = 0 -> 1, else 2
        moveq   #1,d0
        tst.b   $11d9.w
        beq.s   .g1
        moveq   #2,d0
.g1:    cmp.b   1(a4),d0
        beq.s   .gdone
        lea     TMP.l,a1
        move.b  d0,(a1)
        lea     1(a4),a2
        lea     CELLS+22.l,a3
        moveq   #0,d7
        moveq   #0,d1
        bsr.w   cells
.gdone:
; engine temperature $10ba clamped 0..35, hot colours from 28
        moveq   #0,d0
        move.w  $10ba.w,d0
        bpl.s   .t1
        moveq   #0,d0
.t1:    cmp.w   #35,d0
        ble.s   .t2
        moveq   #35,d0
.t2:    cmp.w   22(a4),d0
        beq.s   .tdone
        move.w  d0,22(a4)
        moveq   #0,d1
        cmp.w   #28,d0
        blt.s   .t3
        moveq   #11,d1
.t3:    lea     TMP.l,a1
        bsr.w   conv5
        lea     3(a1),a1
        lea     24(a4),a2
        lea     CELLS+24.l,a3
        moveq   #1,d7
        bsr.w   cells
.tdone:
; clock dial: hand = hi byte of $10ce >> 3 (32 images)
        move.l  $10ce.w,d0
        bgt.s   .d1
        moveq   #0,d0
.d1:    cmp.l   #$ff0000,d0
        blt.s   .d2
        move.l  #$ff0000,d0
.d2:    swap    d0
        lsr.w   #3,d0
        cmp.b   26(a4),d0
        beq.s   .ddone
        move.b  d0,26(a4)
        lsl.w   #7,d0
        lea     DIAL.l,a1
        adda.w  d0,a1
        lea     32(a5),a0
        moveq   #15,d7
.dr:    move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     152(a0),a0
        dbra    d7,.dr
.ddone:
; turbo gauge: $10c0 clamped 0..28
        move.w  $10c0.w,d0
        bpl.s   .u1
        moveq   #0,d0
.u1:    cmp.w   #28,d0
        ble.s   .u2
        moveq   #28,d0
.u2:    cmp.b   27(a4),d0
        beq.s   .udone
        move.b  d0,27(a4)
        mulu.w  #24,d0
        lea     GAUGE.l,a1
        adda.w  d0,a1
        movem.l (a1),d0-d5
        lea     128+5*160(a5),a0
        movem.l d0-d5,(a0)
        movem.l d0-d5,160(a0)
        movem.l d0-d5,320(a0)
        movem.l d0-d5,480(a0)
        movem.l d0-d5,640(a0)
        movem.l d0-d5,800(a0)
.udone: rts

; ---- first pass in a buffer: strip bitmap, sky over rows 16-64, shadows invalid ---------------------------------------------------
paint:  movea.l a5,a0
        lea     BAR.l,a1
        lea     2560(a0),a3
.b:     movem.l (a1)+,d0-d7
        movem.l d0-d7,(a0)
        lea     32(a0),a0
        cmpa.l  a3,a0
        blo.s   .b
        moveq   #-1,d0
        moveq   #-1,d1
        moveq   #-1,d2
        moveq   #-1,d3
        moveq   #-1,d4
        moveq   #-1,d5
        moveq   #-1,d6
        moveq   #-1,d7
        lea     7840(a0),a3             ; rows 16-64 (49 rows)
        movea.l a3,a1
.f:     movem.l d0-d7,-(a1)
        cmpa.l  a0,a1
        bhi.s   .f
        lea     2(a4),a0
        moveq   #14,d7
.i:     move.l  d0,(a0)+                ; bytes 2-61 invalid ($ff)
        dbra    d7,.i
        move.b  d0,1(a4)
        st      (a4)
        rts

; ---- d0.w (0..65535) -> 5 decimal digit codes at (a1), leading zeros = blank (10) except the last -----------------------------------
conv5:  divu    #10000,d0
        move.b  d0,(a1)
        swap    d0
        andi.l  #$ffff,d0
        divu    #100,d0
        lea     BCD.l,a2
        move.w  d0,d2
        add.w   d2,d2
        move.w  (a2,d2.w),d3
        move.b  d3,2(a1)
        lsr.w   #8,d3
        move.b  d3,1(a1)
        swap    d0
        add.w   d0,d0
        move.w  (a2,d0.w),d3
        move.b  d3,4(a1)
        lsr.w   #8,d3
        move.b  d3,3(a1)
        moveq   #3,d2
        moveq   #10,d3
        movea.l a1,a2
.l:     tst.b   (a2)
        bne.s   .e
        move.b  d3,(a2)+
        dbra    d2,.l
.e:     rts

; ---- draw the cells whose code (+ set offset d1) differs from the shadow: a1 codes, a2 shadow, a3 cell offsets, d7 = cells-1 --------
cells:  moveq   #0,d2
        move.b  (a1)+,d2
        add.b   d1,d2
        cmp.b   (a2),d2
        beq.s   .skip
        move.b  d2,(a2)
        lsl.w   #6,d2
        lea     GL.l,a6
        adda.w  d2,a6
        move.w  (a3),d3
        lea     (a5,d3.w),a0
"""

def emit():
    d = build()
    out = [HEADER]
    out.append("; ---- palette: A colour 14 ($3cf0) = $777\nTMP     equ     $BCF80\nS0      equ     $BCF00\nBAR     equ     $BB800\nGL      equ     $BC200\nGAUGE   equ     $BCA40\nCELLS   equ     $BCD00\nBCD     equ     $BCD20\nDIAL    equ     $BD000\n")
    code = CODE
    rows = []
    for k in range(14):
        rows.append("        move.l  (a6)+,d0\n        movep.l d0,%d(a0)\n" % (160 * k))
    code += "".join(rows)
    code += """.skip:  addq.l  #1,a2
        addq.l  #2,a3
        dbra    d7,cells
        rts
"""
    out.append(code)
    out.append("\n        org     $BB800\n" + dump_dc(d['bar']))
    out.append("\n        org     $BC200\n" + dump_dc(d['glyphs'], 16))
    out.append("\n        org     $BCA40\n" + dump_dc(d['gauge'], 24))
    c = d['cells']
    words = c['score'] + c['pos'] + c['speed'] + c['gear'] + c['temp']
    out.append("\n        org     $BCD00\n        dc.w    " + ",".join(str(w) for w in words))
    out.append("\n        org     $BCD20\n" + dump_dc(d['bcd'], 20))
    out.append("\n        org     $BD000\n" + dump_dc(d['dial'], 16))
    return "\n".join(out) + "\n"

if __name__ == "__main__":
    if sys.argv[1] == "emit":
        sys.stdout.write(emit())
    else:
        main_()
