#!/usr/bin/env python3
"""Generator of the sb_* patches (speech bar: the message text and the talking face drawn into a second black strip under the top bar).
    python3 work/speechbar/gen_sb.py [outdir]        (default work/speechbar/patches; copy the generated files to patches/ when verified)
Data tables (font strips, face frames, frame-difference table) come from sbart.py = the game's own message font and face sprites; the layout constants live there.
Patches: sb_bar (entry hook $f90c, all tables, text/face code, state data), sb_face (hook $f994: face frame draw, only the rows that differ), sb_facestat (same site: one
frame per message, VISIBLE: the mouth does not move), sb_glyph ($120a4 rts), sb_erase ($12086 rts)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbart import *

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'patches'
assert TEXT_L == 2 and LINE_Y == (20, 30)

# ---- addresses (all inside the payload image, blob area A gaps; work/notes/speechbar.md section 4)
DATA = 0xBA900                 # 1088 B zero-initialised state ($BA900-$BAD3F); NOT $B2800-$B2FFF: the floppy build puts its site table at $B2820 (build --floppy: "image overlap")
FONT = 0xB3290                 # 91 glyphs x 32 B  ($B3290-$B3DEF)
FACE_A = (0xB4460, 15)         # face frames 0..14 ($B4460-$B4F9F)
FACE_B = (0xB5A00, 7)          # face frames 15..21 ($B5A00-$B5F3F)
CODE = 0xB6040                 # main code (sbent first) ... ends before TABS
TABS = 0xB6440                 # FTAB (22 longs) + DIFFT (22 x 7 words), ends $B65CB
FACEC = 0xB6600                # sb_face code
FACESC = 0xB6780               # sb_facestat code
FIRST_CH, N_CH = 0x20, 91      # ' ' .. 'z'
FACE_BYTES = 192
ROWSTEP = (LINE_Y[1] - LINE_Y[0]) * 160            # 1600
CELL0 = LINE_Y[0] * 160                            # byte offset of text line 0, row 0


def font_bytes():
    out = bytearray()
    assert (BG, BODY, SHADOW) == (2, 14, 4)        # bg 0010, body 1110, shadow 0100
    for c in range(FIRST_CH, FIRST_CH + N_CH):
        for d1, d2 in glyph8(c):
            out += bytes([0, (~d1 | d2) & 0xff, (d1 | d2) & 0xff, d2 & 0xff])     # plane 0..3 bytes
    return bytes(out)


FACES = {i: face16(i) for i in FACE_IDS}


def face_bytes(idx):
    f = FACES[idx]
    out = bytearray()
    for y in range(24):
        for p in range(4):
            w = 0
            for b in range(16):
                w |= ((int(f[y, b]) >> p) & 1) << (15 - b)
            out += w.to_bytes(2, 'big')
    assert len(out) == FACE_BYTES
    return bytes(out)


def dc_b(data, per=16):
    return '\n'.join('        dc.b    ' + ','.join('$%02x' % b for b in data[i:i + per]) for i in range(0, len(data), per))


def face_ptrs():
    return [(FACE_A[0] + FACE_BYTES * k) if k < FACE_A[1] else (FACE_B[0] + FACE_BYTES * (k - FACE_A[1])) for k in range(len(FACE_IDS))]


def difft():
    """per old frame a (0..21) and delta d = new - old in -3..+3: word = r0 << 8 | (rows - 1) of the rows that differ; $ffff = identical pictures; d = 0 unused ($ffff)."""
    out = []
    for a, ia in enumerate(FACE_IDS):
        for d in range(-3, 4):
            b = a + d
            if d == 0 or not 0 <= b < len(FACE_IDS):
                out.append(0xffff)
                continue
            rows = np.nonzero((FACES[ia] != FACES[FACE_IDS[b]]).any(axis=1))[0]
            out.append(0xffff if len(rows) == 0 else (int(rows.min()) << 8) | (int(rows.max() - rows.min())))
    return out


COLO = [CELL0 + (((TEXT_X0 // 8 + c) >> 1) * 8 + ((TEXT_X0 // 8 + c) & 1)) for c in range(TEXT_W + 1)]
FACE_OFF = FACE_Y * 160 + (FACE_X // 16) * 8
STRIP_OFF = STRIP_Y0 * 160
EQU = f'''W       equ     {TEXT_W}
DATA    equ     ${DATA:X}
S0      equ     DATA
S1      equ     DATA+16
LM      equ     DATA+32
CELL    equ     DATA+64                ; 256 longs: glyph offset << 16 | cell
FONT    equ     ${FONT:X}
FTAB    equ     ${TABS:X}
DIFFT   equ     ${TABS + 88:X}
FDRAW   equ     $@FDRAW@
'''


def code():
    g = []
    A = g.append
    A(f'''
; ---- entry: replaces `movea.l $1008.w,a5 / moveq #0,d0` at the start of the face routine $f90c (called after the ticker in every HUD stage, also in the extra frames).
; Registers: the stock face path clobbers d0-d7 a0-a4 a6 (its sprite kernel), its callers rely on nothing but a5 = $1008: this code uses exactly those and keeps a5.
sbent:  movea.l $1008.w,a5              ; the buffer being drawn
        cmpi.l  #$0000ffff,{STRIP_OFF}(a5)     ; sentinel: planes 0/1 of the first strip word = $0000 $ffff in the black strip; $ffff $ffff in the sky the HUD paints over rows 16-64; 0 in a cleared screen
        bne.w   repaint
back:   move.l  a5,d0
        lea     S0.l,a0                 ; this buffer's shadow: +0 message drawn (word, 0 = none), +2 characters drawn, +4 face frame drawn (0 = none), +6 dirty text lines (bit 0/1)
        btst    #15,d0
        beq.s   .s0
        lea     S1.l,a0
.s0:    tst.b   $11ab.w                 ; the ticker: 0 = no message on screen (idle, or the erase passes), 1 = typing, >= 2 = held
        bne.s   active
none:   tst.w   (a0)
        bne.s   endmsg
        tst.w   4(a0)
        beq.s   out
endmsg:   bsr     clrtext                 ; the message ended: this buffer still shows it -> solid fill of the dirty text lines and the face box, once
        tst.w   4(a0)
        beq.s   .nf
        bsr     clrface
.nf:    clr.l   (a0)
        clr.w   4(a0)
out:    moveq   #0,d0                   ; the displaced `moveq #0,d0`; continue in the face routine
        jmp     $f912.l

active: move.w  $11a8.w,d1              ; message record address (low word); the text starts 4 bytes behind it (x, y, colour, hold)
        beq.s   none
        move.w  $11a4.w,d2              ; ticker text pointer (low word of $11a2): characters typed so far = pointer - text start
        sub.w   d1,d2
        subq.w  #4,d2
        cmp.w   (a0),d1
        bne.s   work
        cmp.w   2(a0),d2
        beq.s   out                     ; this buffer already shows exactly this: nothing to do
work:   cmp.w   #256,d2
        bcs.s   .nok
        moveq   #0,d2
.nok:   moveq   #0,d3
        move.w  d1,d3
        addq.l  #4,d3
        movea.l d3,a2                   ; a2 = the message text
        lea     LM.l,a3                 ; shared layout state: +0 message, +2 characters laid out, +4 column, +6 line offset (0 / {ROWSTEP}), +8 at-word-start flag
        cmp.w   (a3),d1
        bne.s   .newl
        cmp.w   2(a3),d2
        bcc.s   .lay
.newl:  move.w  d1,(a3)
        clr.w   2(a3)
        clr.w   4(a3)
        clr.w   6(a3)
        move.w  #1,8(a3)
.lay:   movem.w 2(a3),d4-d7            ; characters laid out, column, line offset, at-word-start (sign-extended words)
        cmp.w   d2,d4
        bcc.w   .draw
        lea     CELL.l,a4
        lea     COLO(pc),a1
.lc:    moveq   #0,d0
        move.b  (a2,d4.w),d0
        cmp.b   #$20,d0
        beq.s   .sep
        cmp.b   #$0d,d0
        beq.s   .sep
        tst.w   d7                      ; a word starts here: does it fit on this line?
        beq.s   .inw
        moveq   #0,d7
        tst.w   d5
        beq.s   .inw
        move.w  d4,d1
.wl:    addq.w  #1,d1
        move.b  (a2,d1.w),d3
        beq.s   .wle
        cmp.b   #$20,d3
        beq.s   .wle
        cmp.b   #$0d,d3
        bne.s   .wl
.wle:   sub.w   d4,d1                   ; word length
        add.w   d5,d1
        cmp.w   #W,d1
        bls.s   .inw
        add.w   #{ROWSTEP},d6           ; wrap
        moveq   #0,d5
.inw:   cmp.w   #W,d5
        bcs.s   .fit
        add.w   #{ROWSTEP},d6
        moveq   #0,d5
.fit:   move.w  d4,d3
        lsl.w   #2,d3
        cmp.w   #{ROWSTEP * 2},d6
        bcc.s   .skip
        sub.b   #{FIRST_CH},d0          ; not a glyph of the table: no cell
        cmp.b   #{N_CH},d0
        bcc.s   .skip
        lsl.w   #5,d0                   ; glyph strip offset
        swap    d0
        move.w  d5,d1
        add.w   d1,d1
        move.w  (a1,d1.w),d1
        add.w   d6,d1
        move.w  d1,d0                   ; long = glyph offset << 16 | cell (byte offset of the glyph in the buffer)
        move.l  d0,(a4,d3.w)
        bra.s   .nx
.skip:  clr.l   (a4,d3.w)
.nx:    addq.w  #1,d5
        bra.s   .adv
.sep:   move.w  d4,d3
        lsl.w   #2,d3
        clr.l   (a4,d3.w)
        tst.w   d5
        beq.s   .s1
        cmp.w   #W,d5
        bcc.s   .s1
        addq.w  #1,d5
.s1:    moveq   #1,d7
.adv:   addq.w  #1,d4
        cmp.w   d2,d4
        bcs.w   .lc
        movem.w d4-d7,2(a3)
.draw:  move.w  (a3),d1                 ; message (the layout state holds it)
        cmp.w   (a0),d1
        bne.s   .chg
        move.w  2(a0),d4
        cmp.w   d2,d4
        bls.s   .dl0
.chg:   movem.l d1-d2/a2-a3,-(a7)      ; this buffer shows another message (or more than the current one): wipe its lines first (clrtext clobbers the pattern registers)
        bsr     clrtext
        movem.l (a7)+,d1-d2/a2-a3
        move.w  d1,(a0)
        clr.w   2(a0)
        clr.w   4(a0)                   ; and its face (a new message brings its own)
.dl0:   move.w  2(a0),d4
        cmp.w   d2,d4
        bcc.s   .dend
        lea     CELL.l,a4
        lea     FONT.l,a6
.dl:    move.w  d4,d3
        lsl.w   #2,d3
        move.l  (a4,d3.w),d0
        beq.s   .dn
        lea     (a5,d0.w),a3
        swap    d0
        lea     (a6,d0.w),a1
''')
    for r in range(8):
        A(f'        move.l  (a1)+,d0\n        movep.l d0,{r * 160}(a3)')
    A(f'''.dn:    addq.w  #1,d4
        cmp.w   d2,d4
        bcs.s   .dl
.dend:  move.w  d2,2(a0)
        moveq   #1,d0                   ; dirty lines: line 0 always; line 1 when the layout has reached it
        tst.w   LM+6.l
        beq.s   .m0
        moveq   #3,d0
.m0:    or.b    d0,6(a0)
        bra     out

; ---- pattern registers: the black strip colour (index 2: plane 1 only) = per 16 pixels the words 0000 ffff 0000 0000 = the longs $0000ffff, 0 alternating
patload: move.l #$0000ffff,d0
        moveq   #0,d1
        move.l  d0,d2
        move.l  d1,d3
        move.l  d0,d4
        move.l  d1,d5
        movea.l d0,a1
        movea.l d1,a2
        movea.l d0,a3
        movea.l d1,a4
        rts

; ---- solid fill of the dirty text lines of this buffer (a0 = shadow, a5 = buffer); clobbers d0-d7 a1-a4 a6
clrtext: move.b 6(a0),d6
        beq.s   .ret
        clr.b   6(a0)
        bsr.s   patload
        btst    #0,d6
        beq.s   .l1
        lea     {CELL0}(a5),a6
        bsr.s   fill8
.l1:    btst    #1,d6
        beq.s   .ret
        lea     {CELL0 + ROWSTEP}(a5),a6
        bsr.s   fill8
.ret:   rts
fill8:  moveq   #7,d7                   ; 8 rows x 152 bytes (groups 0-18)
.r:     movem.l d0-d5/a1-a4,(a6)
        movem.l d0-d5/a1-a4,40(a6)
        movem.l d0-d5/a1-a4,80(a6)
        movem.l d0-d5/a1-a2,120(a6)
        lea     160(a6),a6
        dbra    d7,.r
        rts

; ---- the face box (16x24 at x {FACE_X}, group {FACE_X // 16}) -> black
clrface: lea    {FACE_OFF}(a5),a6
        move.l  #$0000ffff,d0
        moveq   #0,d1
        moveq   #23,d7
.f:     move.l  d0,(a6)
        move.l  d1,4(a6)
        lea     160(a6),a6
        dbra    d7,.f
        rts

; ---- the strip was overpainted (race start / restart, first pass into a buffer): rows {STRIP_Y0}-{STRIP_Y0 + STRIP_H - 1} black, shadows of this buffer cleared.
; The OTHER buffer (the one on screen) is checked too: the race restart paints sky into it as well (measured: race_drive restart, the displayed buffer's strip was all sky for the whole first pass),
; and a displayed buffer is only redrawn one pass later.
repaint: bsr     patload
        lea     {STRIP_OFF}(a5),a6
        bsr     fillstrip
        move.l  a5,d6                   ; d6, not d0: d0-d5 hold the fill pattern
        lea     S0.l,a0
        btst    #15,d6
        beq.s   .z
        lea     S1.l,a0
.z:     clr.l   (a0)
        clr.l   4(a0)
        bchg    #15,d6                  ; the other buffer
        movea.l d6,a6
        lea     {STRIP_OFF}(a6),a6
        cmpi.l  #$0000ffff,(a6)
        beq     back
        bsr     fillstrip               ; (pattern registers are still loaded)
        lea     S0.l,a0
        btst    #15,d6
        beq.s   .y
        lea     S1.l,a0
.y:     clr.l   (a0)
        clr.l   4(a0)
        bra     back
fillstrip: moveq #{STRIP_H - 1},d7
.r:     movem.l d0-d5/a1-a4,(a6)
        movem.l d0-d5/a1-a4,40(a6)
        movem.l d0-d5/a1-a4,80(a6)
        movem.l d0-d5/a1-a4,120(a6)
        lea     160(a6),a6
        dbra    d7,.r
        rts

; ---- full face frame: a1 = frame (192 B), a3 = destination (row 0 of the box); 24 rows x 8 bytes
fdraw:
''')
    for r in range(24):
        A('        move.l  (a1)+,(a3)+\n        move.l  (a1)+,(a3)+\n        lea     152(a3),a3' if r < 23 else '        move.l  (a1)+,(a3)+\n        move.l  (a1)+,(a3)+\n        rts')
    A('''
COLO:   dc.w    ''' + ','.join(str(v) for v in COLO) + '\n')
    return '\n'.join(g)


def facecode():
    return f'''
; ---- face hook: reached from $f994 with d0 = the sprite index of this pass (face state machine and RNG have run as stock), a5 = the buffer; replaces the stock 32x48 sprite draw.
; Registers: d0-d3 d7 a0-a3 (the stock path clobbers all of them).
sbface: cmp.w   #{FACE_IDS[0]},d0
        blo.w   .x
        cmp.w   #{FACE_IDS[-1]},d0
        bhi.w   .x
        move.l  a5,d1
        lea     S0.l,a0
        btst    #15,d1
        beq.s   .s0
        lea     S1.l,a0
.s0:    move.w  4(a0),d1                ; frame this buffer shows (0 = none)
        cmp.w   d1,d0
        beq.w   .x
        move.w  d0,4(a0)
        sub.w   #{FACE_IDS[0]},d0       ; new frame 0..{len(FACE_IDS) - 1}
        move.w  d0,d2
        add.w   d2,d2
        add.w   d2,d2
        lea     FTAB.l,a1
        movea.l (a1,d2.w),a1            ; frame data
        lea     {FACE_OFF}(a5),a3
        tst.w   d1
        beq.s   .full
        sub.w   #{FACE_IDS[0]},d1       ; old frame
        move.w  d0,d2
        sub.w   d1,d2                   ; delta
        addq.w  #3,d2
        cmp.w   #6,d2
        bhi.s   .full                   ; not a neighbour: draw everything
        move.w  d1,d3
        lsl.w   #4,d1
        add.w   d3,d3
        sub.w   d3,d1                   ; old * 14
        add.w   d2,d2
        add.w   d2,d1
        lea     DIFFT.l,a2
        move.w  (a2,d1.w),d2            ; r0 << 8 | rows - 1
        cmp.w   #$ffff,d2
        beq.w   .x                      ; identical pictures
        move.w  d2,d3
        lsr.w   #8,d3                   ; r0
        move.w  d3,d1
        lsl.w   #3,d1
        adda.w  d1,a1                   ; frame row r0 (8 bytes per row)
        lsl.w   #5,d3
        move.w  d3,d1
        lsl.w   #2,d1
        add.w   d1,d3                   ; r0 * 160
        adda.w  d3,a3
        and.w   #$ff,d2                 ; rows - 1
.r:     move.l  (a1)+,(a3)+
        move.l  (a1)+,(a3)+
        lea     152(a3),a3
        dbra    d2,.r
.x:     rts
.full:  bra     fdraw_
'''


def facestatcode():
    return f'''
; ---- face hook, one frame per message and buffer (VISIBLE: the mouth does not move): draws only when this buffer shows no face
sbfaces: cmp.w  #{FACE_IDS[0]},d0
        blo.s   .x
        cmp.w   #{FACE_IDS[-1]},d0
        bhi.s   .x
        move.l  a5,d1
        lea     S0.l,a0
        btst    #15,d1
        beq.s   .s0
        lea     S1.l,a0
.s0:    tst.w   4(a0)
        bne.s   .x
        move.w  d0,4(a0)
        sub.w   #{FACE_IDS[0]},d0
        add.w   d0,d0
        add.w   d0,d0
        lea     FTAB.l,a1
        movea.l (a1,d0.w),a1
        lea     {FACE_OFF}(a5),a3
        bra     fdraw_
.x:     rts
'''


def asm_len(org, src, equ):
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / 's.s').write_text(equ + f'        org ${org:X}\n' + src)
        r = subprocess.run(['vasmm68k_mot', '-Fbin', '-m68000', '-quiet', '-o', str(Path(td) / 's.bin'), str(Path(td) / 's.s')], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        return (Path(td) / 's.bin').read_bytes()


def fdraw_addr():
    """address of the label fdraw inside the main code blob (the tool assembles every org segment on its own, so cross-blob calls need the absolute address)"""
    src = code()
    b = asm_len(CODE, src, EQU.replace('$@FDRAW@', '0'))
    # fdraw is the 24-row unrolled copy: find its first instruction bytes (move.l (a1)+,(a3)+ twice, lea 152(a3),a3)
    pat = bytes.fromhex('26d926d947eb0098')
    i = b.find(pat)
    assert i > 0 and b.find(pat, i + 1) > i
    return CODE + i, len(b)


def emit_bar():
    fd, size = fdraw_addr()
    assert CODE + size <= TABS, hex(CODE + size)
    equ = EQU.replace('$@FDRAW@', '$%X' % fd)
    hdr = f'''; name: sb_bar
; default: no
; site: $f90c
; orig: 2a7810087000
; data: ${DATA:X} 1088
; requires: hd_stage hd_init hd_clouds sb_glyph sb_erase
; conflicts: ta_face ta_facestat ta_glyph ta_erase ta_init mr_map mr_digit tb_blit tb_blit11 tb_blit13 tb_blit15
; doc: Speech bar (VISIBLE): the message text and the talking face are drawn into a second black strip under the top bar (rows {STRIP_Y0}-{STRIP_Y0 + STRIP_H - 1}, {STRIP_H} rows) instead of into the sky; only changed pieces are drawn, per buffer. Needs a face hook: sb_face or sb_facestat.
; note: GENERATED by work/speechbar/gen_sb.py (edit the generator).  work/notes/speechbar.md.  Site $f90c (start of the face routine, called after the ticker `$11ef0` in the HUD stage and in the extra frames of mx_sync): `movea.l $1008.w,a5 / moveq #0,d0` -> `jmp ${CODE:X}.l`.
; note: The ticker's state machine ($11ab/$11b1/$11b2, $11a2 text pointer, $11a8 message) runs exactly as stock; only its two drawing routines are replaced (sb_glyph: the per-character glyph draw, sb_erase: the 49-row box restore).
; note: sbent shows the CURRENT ticker state in the buffer it is called for: message = text[0 .. $11a2) wrapped greedily into {TEXT_L} lines of {TEXT_W} columns (8x8 game font, white body, grey shadow, x {TEXT_X0}), face = sb_face's frame.  A per-buffer shadow (message, characters drawn, face frame, dirty lines) makes a piece drawn only when THAT buffer lacks it.
; note: The strip is repainted (rows {STRIP_Y0}-{STRIP_Y0 + STRIP_H - 1} black) when the sentinel long (planes 0/1 of the first word of row {STRIP_Y0}) is not $0000ffff: hd_stage's PAINT (race start/restart, first pass per buffer) makes it $ffffffff, a screen clear $00000000.  Needs hd_init (clears hd_stage's painted flags), not ta_init (requires ta_erase, which conflicts).
; note: Blobs: code ${CODE:X}, tables ${TABS:X} (face pointers, frame-difference rows), font strips ${FONT:X} (91 x 32 B), face frames ${FACE_A[0]:X} (15) and ${FACE_B[0]:X} (7), 192 B each, state data ${DATA:X}.
'''
    tabs = ''.join(f'        dc.l    ${p:X}\n' for p in face_ptrs()) + ''.join(f'        dc.w    ${w:04X}\n' for w in difft())
    body = equ + f'''
        org     $f90c
        jmp     ${CODE:X}.l

        org     ${FONT:X}
{dc_b(font_bytes(), 32)}

        org     ${FACE_A[0]:X}
''' + dc_b(b''.join(face_bytes(i) for i in FACE_IDS[:FACE_A[1]]), 24) + f'\n\n        org     ${FACE_B[0]:X}\n' + dc_b(b''.join(face_bytes(i) for i in FACE_IDS[FACE_A[1]:]), 24) + f'''

        org     ${TABS:X}
{tabs}
        org     ${CODE:X}
''' + code().replace('$@FDRAW@', '0') + '\n'
    return hdr + body, fd


def emit_face(fd):
    equ = EQU.replace('$@FDRAW@', '$%X' % fd) + f'fdraw_  equ     ${fd:X}\n'
    src = facecode()
    n = len(asm_len(FACEC, src, equ))
    assert FACEC + n <= FACESC, hex(FACEC + n)
    return f'''; name: sb_face
; default: no
; site: $f994
; orig: 41f90001b076
; requires: sb_bar
; conflicts: ta_face ta_facestat sb_facestat
; doc: Speech bar part 2: the talking face (stock: a 32x48 sprite drawn every active pass) is drawn as a 16x24 frame into the strip, only when the buffer shows another frame, and only the rows that differ between the two frames.
; note: GENERATED by gen_sb.py.  Site $f994 = `lea $1b076.l,a0` inside the face routine $f90c, reached with d0 = this pass's sprite index (face state machine and RNG have run exactly as stock): `jmp ${FACEC:X}.l`; the blob returns as the stock routine's rts.
{equ}
        org     $f994
        jmp     ${FACEC:X}.l

        org     ${FACEC:X}
{src}'''


def emit_facestat(fd):
    equ = EQU.replace('$@FDRAW@', '$%X' % fd) + f'fdraw_  equ     ${fd:X}\n'
    src = facestatcode()
    n = len(asm_len(FACESC, src, equ))
    assert FACESC + n <= 0xB6800, hex(FACESC + n)
    return f'''; name: sb_facestat
; default: no
; site: $f994
; orig: 41f90001b076
; requires: sb_bar
; conflicts: ta_face ta_facestat sb_face
; doc: Speech bar part 2 (VISIBLE alternative): one face frame per message and buffer (the frame of the first pass), the mouth does not move: about 0.5 k cycles per typing pass cheaper than sb_face.
; note: GENERATED by gen_sb.py.  Same site as sb_face ($f994, the sprite draw inside the stock face routine; its state machine and RNG still run as stock).
{equ}
        org     $f994
        jmp     ${FACESC:X}.l

        org     ${FACESC:X}
{src}'''


def emit_glyph():
    return '''; name: sb_glyph
; default: no
; site: $120a4
; orig: 2a781008
; requires: sb_bar
; doc: Speech bar part 3: the ticker's per-character glyph draw (and its occupancy-map write) is dropped; the text is drawn by sb_bar from the ticker state.
; note: GENERATED by gen_sb.py.  Site $120a4 = start of the ticker's glyph routine (callers: `bsr.w $120a4` at $11fde and $12022 inside $11ef0; nothing else): `rts` (nop padded).  The caller's state ($11ae, $11a6, $11af) evolves as stock.
        org     $120a4
        rts
'''


def emit_erase():
    return '''; name: sb_erase
; default: no
; site: $12086
; orig: 7070
; requires: sb_bar
; doc: Speech bar part 4: the ticker's 49-row message-box restore (2 passes of 35 k cycles per message) is dropped; sb_bar clears the strip's text lines and face box once per buffer.
; note: GENERATED by gen_sb.py.  Site $12086 = start of the box restore (callers: `bsr.w $12086` at $11fc4 and the fall-through from $12082 in $11ef0, both followed by the ticker's own state updates): `rts`.
        org     $12086
        rts
'''


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    bar, fd = emit_bar()
    (OUT / 'sb_bar.s').write_text(bar)
    (OUT / 'sb_face.s').write_text(emit_face(fd))
    (OUT / 'sb_facestat.s').write_text(emit_facestat(fd))
    (OUT / 'sb_glyph.s').write_text(emit_glyph())
    (OUT / 'sb_erase.s').write_text(emit_erase())
    print('wrote', OUT, 'fdraw', hex(fd))
