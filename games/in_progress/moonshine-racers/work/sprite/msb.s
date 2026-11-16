; Blitter sprite kernels, prototype for the unit harness (interior case; everything else falls back to the stock entry).
; Contract = the stock FULL entries ($12994.. via the tables $399c..): d0 = x, d1 = y, d7 = rows, a1 = bitmap rows (2P bytes per 16 px column), a5 = screen base.
; Result = the stock kernel's: (D & ~M) | S per plane, M = OR of the data planes, S shifted right by x & 15, 4th plane (absent from the data) only masked.
; BUDGET = max HOG bytes-cycles per blit pass (rows are split so that rows * n * 12 <= BUDGET).
        ifnd    BUDGET
BUDGET  equ     1800
        endc
BL      equ     $ffff8a00
TMP     equ     $E1000                  ; mask rows (c words per row, contiguous)
        org     $C2000
; descriptors: P*2, dest byte offsets of the P data planes, P (loop count)
d7_:    dc.w    6,0,2,4,0,3
d11_:   dc.w    6,0,2,6,0,3
d13_:   dc.w    6,0,4,6,0,3
d15_:   dc.w    8,0,2,4,6,4
cht:    dc.w    0,BUDGET/12,BUDGET/24,BUDGET/36,BUDGET/48,BUDGET/60

STUB    macro   ; name, cols, desc, orig entry
\1:     moveq   #\2,d4
        lea     \3(pc),a2
        move.l  #\4,d3
        bra.w   common
        endm
        STUB   s_n7c1,1,d7_,$12994
        STUB   s_n7c2,2,d7_,$12f60
        STUB   s_n7c3,3,d7_,$13662
        STUB   s_n7c4,4,d7_,$13f6e
        STUB   s_n11c1,1,d11_,$12a98
        STUB   s_n11c2,2,d11_,$130e2
        STUB   s_n11c3,3,d11_,$1384c
        STUB   s_n11c4,4,d11_,$141cc
        STUB   s_n13c1,1,d13_,$12bac
        STUB   s_n13c2,2,d13_,$1327e
        STUB   s_n13c3,3,d13_,$13a5e
        STUB   s_n13c4,4,d13_,$1445c
        STUB   s_n15c1,1,d15_,$12ce0
        STUB   s_n15c2,2,d15_,$1345a
        STUB   s_n15c3,3,d15_,$13cc8
        STUB   s_n15c4,4,d15_,$1475a

fb:     movea.l d3,a0                   ; stock entry (registers untouched except d2-d6)
        jmp     (a0)

common: tst.w   d0
        bmi.s   fb
        tst.w   d1
        bmi.s   fb
        move.w  #200,d2
        sub.w   d1,d2
        ble.s   fb
        cmp.w   d2,d7
        ble.s   .r
        move.w  d2,d7
.r:     tst.w   d7
        ble.s   fb
        moveq   #15,d6
        and.w   d0,d6                   ; s
        move.w  d0,d2
        lsr.w   #4,d2                   ; X0
        move.w  d4,d5
        tst.w   d6
        beq.s   .n0
        addq.w  #1,d5                   ; n = dest words per row (whole sprite)
.n0:    move.w  d2,d0
        add.w   d5,d0
        cmpi.w  #20,d0
        bgt.s   fb
        ; dest = a5 + y*160 + X0*8 ; $100c = that offset (the stock stores it)
        move.w  d1,d3
        lsl.w   #5,d3
        move.w  d3,d0
        add.w   d3,d3
        add.w   d3,d3
        add.w   d0,d3                   ; y*160
        lsl.w   #3,d2
        add.w   d2,d3
        move.w  d3,$100c.l
        lea     (a5,d3.w),a3
        move.w  (a2),d3                 ; 2P
        mulu.w  d4,d3                   ; d3 = row bytes (all columns)
        move.l  a6,-(a7)
        cmpi.w  #3,d4
        bcc.s   .many
        bsr.s   grp                     ; 1 or 2 columns: one group
        movea.l (a7)+,a6
        rts
.many:  ; 3 or 4 columns: the first two columns are one plane-major pair, every further column is a single (P words interleaved).
        ; Each group is drawn as an independent shifted sprite: the word two groups share holds the spill bits of one and the
        ; low bits of the next, disjoint, so (D & ~Ma | Sa) & ~Mb | Sb = D & ~(Ma | Mb) | Sa | Sb.
        movem.l d4/d7/a1/a3,-(a7)
        moveq   #2,d4
        bsr.s   grp
        movem.l (a7)+,d4/d7/a1/a3
        move.w  (a2),d0
        add.w   d0,d0
        adda.w  d0,a1                   ; 4P bytes: the pair
        lea     16(a3),a3
        subq.w  #3,d4                   ; singles left - 1
.sg:    movem.l d4/d7/a1/a3,-(a7)
        moveq   #1,d4
        bsr.s   grp
        movem.l (a7)+,d4/d7/a1/a3
        move.w  (a2),d0
        adda.w  d0,a1                   ; 2P bytes: one single column
        addq.l  #8,a3
        dbra    d4,.sg
        movea.l (a7)+,a6
        rts

; grp: draw d4 columns (1 or 2) of the rows (d7) at a1 -> a3, shift d6, d3 = bytes per sprite row, a2 = descriptor.  Clobbers d0-d2, d5, d7, a0, a1, a3, a4, a6.
grp:    move.w  d4,d5
        tst.w   d6
        beq.s   .g0
        addq.w  #1,d5                   ; n
.g0:    lea     cht(pc),a0
        add.w   d5,d5
        move.w  (a0,d5.w),d1            ; max rows per blit pass
        lsr.w   #1,d5
        moveq   #-1,d0
        lsr.w   d6,d0
        move.w  d0,-(a7)                ; em1
        moveq   #-1,d0
        tst.w   d6
        beq.s   .e3
        moveq   #16,d2
        sub.w   d6,d2
        lsl.w   d2,d0
.e3:    move.w  d0,-(a7)                ; em3
        move.w  d6,d0
        tst.w   d6
        beq.s   .sk
        ori.w   #$40,d0
.sk:    move.w  d0,-(a7)                ; skew byte
chunk:  move.w  d7,d2                   ; rows of this chunk
        cmp.w   d1,d2
        ble.s   .c1
        move.w  d1,d2
.c1:    movem.l d1/d7,-(a7)
        ; --- mask build: T = OR of the data planes (aligned, no skew), P passes.  Row = P planes of `cols` words each (plane-major).
        move.w  d4,d0
        add.w   d0,d0
        movea.w d0,a4                   ; plane step = 2 * cols
        move.w  d3,d0
        sub.w   a4,d0
        addq.w  #2,d0                   ; src yinc = row bytes - 2 * (cols - 1)
        move.l  #$00020000,d1
        move.w  d0,d1
        move.l  d1,BL+$20.w             ; src xinc = 2 : yinc
        move.l  #$00020002,BL+$2e.w     ; dst xinc = yinc = 2
        moveq   #-1,d0
        move.l  d0,BL+$28.w             ; endmask 1, 2
        move.w  d0,BL+$2c.w             ; endmask 3
        move.w  d4,BL+$36.w             ; xcount = cols
        move.w  #$0203,BL+$3a.w         ; HOP = source, LOP = S
        clr.b   BL+$3d.w
        move.w  10(a2),d7
        subq.w  #1,d7                   ; P - 1
        movea.l a1,a0
        move.l  a0,BL+$24.w
        move.l  #TMP,BL+$32.w
        move.w  d2,BL+$38.w
        move.b  #$c0,BL+$3c.w           ; start, HOG
        move.b  #7,BL+$3b.w             ; LOP = S | D for the other planes
.mb:    adda.l  a4,a0
        move.l  a0,BL+$24.w
        move.l  #TMP,BL+$32.w
        move.w  d2,BL+$38.w
        move.b  #$c0,BL+$3c.w
        subq.w  #1,d7
        bne.s   .mb
        ; --- mask apply: D &= ~M on the 4 dest planes (skew s)
        move.l  #$00020002,BL+$20.w     ; source = TMP rows: xinc = yinc = 2
        move.w  #168,d0
        move.w  d5,d1
        lsl.w   #3,d1
        sub.w   d1,d0                   ; dst yinc = 160 - 8 * (n - 1)
        move.l  #$00080000,d1
        move.w  d0,d1
        move.l  d1,BL+$2e.w             ; dst xinc 8 : yinc
        move.w  8(a7),d1                ; skew   (stack: d1/d7, skew, em3, em1)
        move.w  12(a7),d0               ; em1
        swap    d0
        move.w  #$ffff,d0
        move.l  d0,BL+$28.w             ; endmask 1 : endmask 2 = $ffff
        move.w  10(a7),BL+$2c.w         ; endmask 3
        move.b  d1,BL+$3d.w             ; skew
        move.w  d5,BL+$36.w             ; xcount = n
        move.b  #4,BL+$3b.w             ; LOP = ~S & D
        move.l  a3,d0
        moveq   #3,d7
.ma:    move.l  #TMP,BL+$24.w
        move.l  d0,BL+$32.w
        move.w  d2,BL+$38.w
        move.b  #$c0,BL+$3c.w
        addq.l  #2,d0
        dbra    d7,.ma
        ; --- data: D |= S per present plane
        move.w  d3,d0
        sub.w   a4,d0
        addq.w  #2,d0
        move.l  #$00020000,d1
        move.w  d0,d1
        move.l  d1,BL+$20.w
        move.b  #7,BL+$3b.w
        move.w  10(a2),d7
        subq.w  #1,d7
        movea.l a1,a0
        lea     2(a2),a6                ; dest plane offsets
.da:    move.l  a0,BL+$24.w
        move.w  (a6)+,d0
        ext.l   d0
        add.l   a3,d0
        move.l  d0,BL+$32.w
        move.w  d2,BL+$38.w
        move.b  #$c0,BL+$3c.w
        adda.l  a4,a0
        dbra    d7,.da
        movem.l (a7)+,d1/d7
        sub.w   d2,d7
        ble.s   .done
        move.w  d3,d0                   ; next chunk: a1 += rc * row bytes, a3 += rc * 160
        mulu.w  d2,d0
        adda.l  d0,a1
        mulu.w  #160,d2
        adda.l  d2,a3
        bra     chunk
.done:  lea     6(a7),a7
        rts
