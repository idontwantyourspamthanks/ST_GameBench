; name: pop2_spr
; default: yes
; site: $213b0
; orig: 727844015342
; data: $88200 32256
; note: Item 2 (work/notes/display.md): masked 32 px sprite blits, ported from Powermonger's p4_spr.  $213b0 is the main variant of the sprite blitter $2122e
; note: (3 screen columns fully on screen: 8.75 % of a busy frame's cycles; Powermonger's routine at $124a8 has the same bytes `7278 4401 5342`): a0 = screen address
; note: of column c, row y (the clip front end $2122e has added y*160 + (x & $fff0)/2), a1 = sprite rows (20 B each = mask M0 P0..P3 | M1 Q0..Q3, already clipped
; note: at the top), d0 = shift s = x & 15, d2 = rows.  The original: per row and plane ((D & Ma) | Pa) & Mb | Pb on the three words (c, c+1, c+2), Ma/Pa/Mb/Pb the ror.l-shifted
; note: words (ones fill for the masks, zero fill for the planes); about 770 cycles per row.  Both new paths use the equivalent form D & Mc | Pc (Mc = Ma & Mb,
; note: Pc = (Pa & Mb) | Pb: exact by Boolean algebra).
; note: BLT.l ($88200) = $b17e000m: m = 0 or anything else = auto (first call: a bus-error-safe probe of the blitter's endmask registers, an ST has none), 1 = blitter,
; note: 2 = pre-shifted cache, 3 = the original code (the last three for tests: p2abtest.py --poke).
; note: A. BLITTER (STE, Mega STE; HOG): per plane, pass 1 D &= mask (LOP 1, source = the mask words), pass 2 D |= plane (LOP 7); skew s, NFSR (SKEW bit 6), source xinc 10,
; note: source yinc 10 (20 B per row), xcount 3, dest xinc 8, yinc 144, endmask1 = $ffff >> s and endmask3 = $ffff << (16-s) in BOTH passes (the bits outside the sprite come from the
; note: shifter's previous word and must not be written).  8 passes, each at most rows x 3 words x ~12 cycles (900 cycles at 25 rows, 1,200 at 33): the CPU runs 5-8 instructions between
; note: passes, so an interrupt waits at most two passes (work/notes/display.md; Powermonger buserr.md: a burst longer than one IKBD byte, 10,240 cycles, loses bytes).
; note: B. PRE-SHIFTED CACHE (CPU path: the plain ST): the shifted result per (a1, s) is built once, 36 B per row (3 mask longs + 6 plane longs), the draw is movem + 5 and.l +
; note: 5 or.l + movem + a sixth long (~325 cycles/row).  The cache entry also keeps a COPY of the source rows (20 B per row) and every hit first compares the rows being drawn
; note: with it (cmpm, ~110 cycles/row), so a sheet that is reloaded, patched or built on the fly is rebuilt instead of drawn stale: exact for any data.  16 slots of 1,856 B (<= 33
; note: rows) in 4 sets x 4 ways at $88400, tags at $88220, lazy init behind a magic word (the area is not in the payload image: no initial value is assumed).  s = 0, rows > 33 and
; note: a1 outside $20000-$7b37f take the original code.
; note: Registers as the original leaves them: a0 += 160*rows, a1 += 20*rows, d0 = s, d1 = $88, d2.w = $ffff, a2-a6 and the high word of d2 untouched, d3-d7 clobbered.
BLT     equ     $88200                  ; long: $b17e000m
HDR     equ     $88210                  ; long: magic
TAGS    equ     $88220                  ; 4 sets x 80 B = 320 B -> $88360
SCR     equ     $88360                  ; scratch: the ten rotated source longs of a row (40 B)
SLOTS   equ     $88400
SLOTSZ  equ     1856
SRCOFF  equ     1188                    ; 33 rows x 36 B
MAGIC   equ     $50525330               ; 'PRS0'
SPR     equ     PB+$4000
PRE     equ     PB+$4600
BUILD   equ     PB+$4a00
INIT    equ     PB+$5200
PROBE   equ     PB+$4300
SPR16   equ     PB+$5400
        org     $213b0
        jmp     SPR.l

        org     PB+$4000
spr:    move.l  BLT.l,d1
        cmpi.l  #$b17e0001,d1
        beq.s   .go
        cmpi.l  #$b17e0002,d1
        beq.w   PRE
        cmpi.l  #$b17e0003,d1
        beq.w   .cpu                    ; 3 = the original code (test mode)
        jsr     PROBE.l                 ; anything else (first call, or junk): BLT = 1 or 2
        cmpi.l  #$b17e0001,BLT.l
        bne.w   PRE
.go:    tst.w   d2
        beq.w   .cpu                    ; 0 rows (the original runs 65,536 of them): the original
        cmpi.w  #64,d2
        bhi.w   .cpu                    ; absurd row counts: the original
        move.w  #10,$ffff8a20.w         ; source X inc
        move.w  #10,$ffff8a22.w         ; source Y inc
        move.w  #8,$ffff8a2e.w          ; dest X inc
        move.w  #144,$ffff8a30.w        ; dest Y inc
        move.w  #3,$ffff8a36.w          ; X count
        move.b  #2,$ffff8a3a.w          ; HOP = source
        move.b  #1,$ffff8a3b.w          ; LOP = S AND D
        move.w  d0,d1
        ori.b   #$40,d1
        move.b  d1,$ffff8a3d.w          ; NFSR + skew
        moveq   #-1,d5
        move.w  d5,d6
        lsr.w   d0,d6
        move.w  d6,$ffff8a28.w          ; endmask 1 = $ffff >> s
        move.w  d5,$ffff8a2a.w
        moveq   #16,d7
        sub.w   d0,d7
        move.w  d5,d6
        lsl.w   d7,d6
        move.w  d6,$ffff8a2c.w          ; endmask 3 = $ffff << (16-s)  (0 for s = 0)
        move.l  a1,d3                   ; sprite rows
        move.l  a0,d4                   ; screen
        moveq   #3,d7
.a:     move.l  d3,$ffff8a24.w
        move.l  d4,$ffff8a32.w
        move.w  d2,$ffff8a38.w
        move.b  #$c0,$ffff8a3c.w        ; start, HOG
        addq.l  #2,d4
        dbra    d7,.a
        move.b  #7,$ffff8a3b.w          ; LOP = S OR D (same endmasks)
        addq.l  #2,d3                   ; plane 0 words
        subq.l  #8,d4
        moveq   #3,d7
.o:     move.l  d3,$ffff8a24.w
        move.l  d4,$ffff8a32.w
        move.w  d2,$ffff8a38.w
        move.b  #$c0,$ffff8a3c.w
        addq.l  #2,d3
        addq.l  #2,d4
        dbra    d7,.o
        move.w  d2,d3                   ; the original's final registers
        lsl.w   #5,d3
        adda.w  d3,a0                   ; rows*32
        lsl.w   #2,d3
        adda.w  d3,a0                   ; + rows*128
        move.w  d2,d3
        add.w   d3,d3
        add.w   d3,d3
        move.w  d3,d4
        add.w   d3,d3
        add.w   d3,d3
        add.w   d4,d3                   ; rows*20
        adda.w  d3,a1
        moveq   #$78,d1
        neg.b   d1
        move.w  #-1,d2
        rts
.cpu:   moveq   #$78,d1                 ; the three replaced instructions
        neg.b   d1
        subq.w  #1,d2
        jmp     $213b6.l

        org     PB+$4300
; lazy probe: BLT = 1 if the blitter's endmask registers read back, else 2.  Bus-error safe; a2-a4 are saved (the caller keeps pointers in them).
probe:  movem.l a2-a4,-(a7)
        move.l  #$b17e0000,d4
        moveq   #2,d3
        movea.l a7,a2                   ; where the bus error handler resets the stack
        movea.l $8.w,a3
        lea     .berr(pc),a4
        move.l  a4,$8.w
        move.w  #$5aa5,$ffff8a28.w
        cmpi.w  #$5aa5,$ffff8a28.w
        bne.s   .no
        move.w  #$a55a,$ffff8a2a.w
        cmpi.w  #$a55a,$ffff8a2a.w
        bne.s   .no
        btst    #7,$ffff8a3c.w          ; BUSY must be clear
        bne.s   .no
        moveq   #1,d3
        bra.s   .no
.berr:  movea.l a2,a7
.no:    move.l  a3,$8.w
        or.l    d3,d4
        move.l  d4,BLT.l
        movem.l (a7)+,a2-a4
        rts

        org     PB+$4600
pre:    tst.w   d0
        beq.w   .cpu                    ; s = 0
        tst.w   d2
        beq.w   .cpu
        cmpi.w  #33,d2
        bhi.w   .cpu
        cmpa.l  #$20000,a1
        bcs.w   .cpu
        cmpa.l  #$7b380,a1
        bcc.w   .cpu
        movem.l d0/d2/a1-a4,-(a7)       ; d0 = s, d2 = rows, a1 = rows address are restored at the end; a2-a4 belong to the callers
        movea.l a1,a4
        cmpi.l  #MAGIC,HDR.l
        beq.s   .ini
        jsr     INIT.l
.ini:   move.l  a1,d1
        lsr.l   #3,d1
        add.w   d1,d1
        add.w   d0,d1
        move.w  d1,d3
        lsr.w   #4,d3
        eor.w   d3,d1
        andi.w  #3,d1                   ; set
        mulu    #80,d1
        lea     TAGS.l,a2
        adda.w  d1,a2                   ; set record: +0 rr.w, +2.. 4 entries {a1.l, data.l, s.w, rows.w}
        lea     2(a2),a3
        moveq   #3,d3
.w:     cmpa.l  (a3),a1
        bne.s   .n
        cmp.w   8(a3),d0
        beq.s   .found
.n:     lea     12(a3),a3
        dbra    d3,.w
        move.w  (a2),d3                 ; miss: round-robin victim
        move.w  d3,d4
        addq.w  #1,d4
        cmpi.w  #4,d4
        bcs.s   .rr
        moveq   #0,d4
.rr:    move.w  d4,(a2)
        mulu    #12,d3
        lea     2(a2),a3
        adda.w  d3,a3
        move.l  a1,(a3)
        move.w  d0,8(a3)
        clr.w   10(a3)                  ; nothing built yet
.found: cmp.w   10(a3),d2
        bhi.s   .rebuild                ; more rows wanted than built
        movea.l 4(a3),a2                ; verify: the rows being drawn against the copy the entry was built from
        lea     SRCOFF(a2),a2
        move.w  d2,d3
        subq.w  #1,d3
.vl:    cmpm.l  (a1)+,(a2)+
        bne.s   .bad
        cmpm.l  (a1)+,(a2)+
        bne.s   .bad
        cmpm.l  (a1)+,(a2)+
        bne.s   .bad
        cmpm.l  (a1)+,(a2)+
        bne.s   .bad
        cmpm.l  (a1)+,(a2)+
        bne.s   .bad
        dbra    d3,.vl
        bra.s   .draw
.bad:   movea.l a4,a1
.rebuild:
        move.w  d2,10(a3)               ; (re)build the entry for this many rows
        movea.l 4(a3),a2
        lea     SRCOFF(a2),a2
        movea.l a4,a1
        move.w  d2,d7
        subq.w  #1,d7
.cp:    move.l  (a1)+,(a2)+             ; keep a copy of the source rows
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        dbra    d7,.cp
        movea.l a4,a1
        move.w  d2,d7
        jsr     BUILD.l
.draw:  movea.l 4(a3),a3                ; the cached rows
        move.w  d2,d3
        mulu    #160,d3
        lea     (a0,d3.l),a2            ; end of the destination rows
.row:   movem.l (a3)+,d0-d2
        movem.l (a0),d3-d7
        and.l   d0,d3
        and.l   d0,d4
        and.l   d1,d5
        and.l   d1,d6
        and.l   d2,d7
        or.l    (a3)+,d3
        or.l    (a3)+,d4
        or.l    (a3)+,d5
        or.l    (a3)+,d6
        or.l    (a3)+,d7
        movem.l d3-d7,(a0)
        move.l  20(a0),d3
        and.l   d2,d3
        or.l    (a3)+,d3
        move.l  d3,20(a0)
        lea     160(a0),a0
        cmpa.l  a2,a0
        bne.s   .row
        movem.l (a7)+,d0/d2/a1-a4       ; the caller's s, rows, a1, a2-a4
        move.w  d2,d3                   ; a1 += 20*rows
        add.w   d3,d3
        add.w   d3,d3
        move.w  d3,d4
        add.w   d3,d3
        add.w   d3,d3
        add.w   d4,d3
        adda.w  d3,a1
        moveq   #$78,d1
        neg.b   d1
        move.w  #-1,d2
        rts
.cpu:   moveq   #$78,d1                 ; the three replaced instructions
        neg.b   d1
        subq.w  #1,d2
        jmp     $213b6.l

; build: a1 = sprite rows, d0 = s, d7 = rows, a3 = the cache entry (data pointer at 4(a3)).  Clobbers d1, d3-d7, a1, a2; keeps a3.
        org     PB+$4a00
build:  move.l  a3,-(a7)
        movea.l 4(a3),a2                ; output
        lea     SCR.l,a3                ; scratch: the ten rotated source longs of a row
        subq.w  #1,d7
.b:     moveq   #-1,d3                  ; group a: mask (ones fill) and four planes (zero fill), each ror.l by s
        move.w  (a1)+,d3
        ror.l   d0,d3
        move.l  d3,(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,4(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,8(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,12(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,16(a3)
        moveq   #-1,d3                  ; group b
        move.w  (a1)+,d3
        ror.l   d0,d3
        move.l  d3,20(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,24(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,28(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,32(a3)
        moveq   #0,d4
        move.w  (a1)+,d4
        ror.l   d0,d4
        move.l  d4,36(a3)
        ; masks: M0' = Ma.lo, M1' = Ma.hi & Mb.lo, M2' = Mb.hi, each in both halves
        move.w  2(a3),d3
        move.w  d3,d4
        swap    d4
        move.w  d3,d4
        move.l  d4,(a2)+
        move.w  22(a3),d1               ; Mb.lo
        move.w  0(a3),d3
        and.w   d1,d3
        move.w  d3,d4
        swap    d4
        move.w  d3,d4
        move.l  d4,(a2)+
        move.w  20(a3),d3
        move.w  d3,d4
        swap    d4
        move.w  d3,d4
        move.l  d4,(a2)+
        ; planes, screen order.  column 0 = Pa.lo, column 1 = Pa.hi & Mb.lo | Pb.lo, column 2 = Pb.hi
        move.w  6(a3),d4                ; L0 = c0p0:c0p1
        swap    d4
        move.w  10(a3),d4
        move.l  d4,(a2)+
        move.w  14(a3),d4               ; L1 = c0p2:c0p3
        swap    d4
        move.w  18(a3),d4
        move.l  d4,(a2)+
        move.w  4(a3),d5                ; c1p0
        and.w   d1,d5
        or.w    26(a3),d5
        move.w  8(a3),d6                ; c1p1
        and.w   d1,d6
        or.w    30(a3),d6
        swap    d5
        move.w  d6,d5
        move.l  d5,(a2)+                ; L2
        move.w  12(a3),d5               ; c1p2
        and.w   d1,d5
        or.w    34(a3),d5
        move.w  16(a3),d6               ; c1p3
        and.w   d1,d6
        or.w    38(a3),d6
        swap    d5
        move.w  d6,d5
        move.l  d5,(a2)+                ; L3
        move.w  24(a3),d4               ; L4 = c2p0:c2p1
        swap    d4
        move.w  28(a3),d4
        move.l  d4,(a2)+
        move.w  32(a3),d4               ; L5 = c2p2:c2p3
        swap    d4
        move.w  36(a3),d4
        move.l  d4,(a2)+
        dbra    d7,.b
        movea.l (a7)+,a3
        rts

; init: tags cleared, data pointers assigned (slot i at SLOTS + SLOTSZ*i, 4 ways per set), then the magic.  Clobbers d3, d4, a2, a3.
        org     PB+$5200
init:   lea     TAGS.l,a2
        lea     SLOTS.l,a3
        moveq   #3,d3
.s:     clr.w   (a2)+                   ; round-robin counter
        moveq   #3,d4
.e:     clr.l   (a2)+                   ; tag
        move.l  a3,(a2)+                ; data pointer
        clr.w   (a2)+                   ; s
        clr.w   (a2)+                   ; rows built
        lea     SLOTSZ(a3),a3
        dbra    d4,.e
        lea     30(a2),a2               ; record stride 80: 2 + 4*12 = 50, 30 pad
        dbra    d3,.s
        move.l  #MAGIC,HDR.l
        rts

; ---- the 16 px variant ($212b4, patch pop2_spr16: it only holds the site, the code is here): rows of 10 B (mask M, planes P0..P3), 2 screen columns, row stride 160.
; Blitter only (xcount 2, NFSR: one source word per row feeds both destination words, source yinc 10, dest yinc 152); the plain-ST path is the original code.
; Needs pop2_spr's BLT word and probe (the pair ships together).  Final registers as the original: a0 += 160*rows, a1 += 10*rows, d0 = s, d1 = $90, d2.w = $ffff.
        org     PB+$5400
spr16:  move.l  BLT.l,d1
        cmpi.l  #$b17e0001,d1
        beq.s   .go
        cmpi.l  #$b17e0002,d1
        beq.w   .cpu
        cmpi.l  #$b17e0003,d1
        beq.w   .cpu
        jsr     PROBE.l
        cmpi.l  #$b17e0001,BLT.l
        bne.w   .cpu
.go:    tst.w   d2
        beq.w   .cpu
        cmpi.w  #64,d2
        bhi.w   .cpu
        move.w  #10,$ffff8a20.w         ; source X inc (unused: one read per row)
        move.w  #10,$ffff8a22.w         ; source Y inc
        move.w  #8,$ffff8a2e.w          ; dest X inc
        move.w  #152,$ffff8a30.w        ; dest Y inc
        move.w  #2,$ffff8a36.w          ; X count
        move.b  #2,$ffff8a3a.w          ; HOP = source
        move.b  #1,$ffff8a3b.w          ; LOP = S AND D
        move.w  d0,d1
        ori.b   #$40,d1
        move.b  d1,$ffff8a3d.w          ; NFSR + skew
        moveq   #-1,d5
        move.w  d5,d6
        lsr.w   d0,d6
        move.w  d6,$ffff8a28.w          ; endmask 1 = $ffff >> s
        move.w  d5,$ffff8a2a.w
        moveq   #16,d7
        sub.w   d0,d7
        move.w  d5,d6
        lsl.w   d7,d6
        move.w  d6,$ffff8a2c.w          ; endmask 3 = $ffff << (16-s)
        move.l  a1,d3
        move.l  a0,d4
        moveq   #3,d7
.a:     move.l  d3,$ffff8a24.w
        move.l  d4,$ffff8a32.w
        move.w  d2,$ffff8a38.w
        move.b  #$c0,$ffff8a3c.w
        addq.l  #2,d4
        dbra    d7,.a
        move.b  #7,$ffff8a3b.w          ; LOP = S OR D
        addq.l  #2,d3
        subq.l  #8,d4
        moveq   #3,d7
.o:     move.l  d3,$ffff8a24.w
        move.l  d4,$ffff8a32.w
        move.w  d2,$ffff8a38.w
        move.b  #$c0,$ffff8a3c.w
        addq.l  #2,d3
        addq.l  #2,d4
        dbra    d7,.o
        move.w  d2,d3                   ; a0 += rows * 160
        lsl.w   #5,d3
        adda.w  d3,a0
        lsl.w   #2,d3
        adda.w  d3,a0
        move.w  d2,d3                   ; a1 += rows * 10
        add.w   d3,d3
        move.w  d3,d4
        add.w   d3,d3
        add.w   d3,d3
        add.w   d4,d3
        adda.w  d3,a1
        moveq   #$70,d1
        neg.b   d1
        move.w  #-1,d2
        rts
.cpu:   moveq   #$70,d1                 ; the three replaced instructions
        neg.b   d1
        subq.w  #1,d2
        jmp     $212ba.l
