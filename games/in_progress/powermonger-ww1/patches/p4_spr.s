; name: p4_spr
; default: yes
; site: $1325e
; orig: 727844015342
; data: $df000 62464
; init: $762e0
; note: masked 32 px sprite blits (master p4_spr / work/notes/p4_raster.md section 5, re-sited: master $124a8 -> WW1 $1325e, return $124ae -> $13264; the routine is 96/96 instructions equal).  The STE blitter
;       where there is one, else a pre-shifted sprite cache for the CPU, else (s = 0, odd addresses, rows > 32, a1 outside the sheets) the original code.  `$1325e` is the main variant of the sprite
;       blitter $1316c (3 screen columns fully on screen, 96 % of its cycles; WW1's tree-heavy start view calls it ~51 times per pass): a0 = screen address of column c, row y (the clip front end has added
;       y*160 + x/16*8), a1 = sprite rows (20 B each = mask M0 P0..P3 | mask M1 Q0..Q3, already clipped at the top), d0 = shift s = x & 15, d2 = rows.  The original: per row and plane
;       ((D & Ma) | Pa) & Mb | Pb on the three words (c, c+1, c+2), Ma/Pa/Mb/Pb the ror.l-shifted words (ones fill for the masks, zero fill for the planes); ~770 cycles per row.  Both paths use the
;       equivalent form D & Mc | Pc (Mc = Ma & Mb, Pc = (Pa & Mb) | Pb, exact by Boolean algebra).
;       BLT.l ($df004) = $b17e000m, set by this patch's `init` (end of file): 1 = blitter (STE family per the _MCH cookie AND a bus-error-safe probe of the blitter's endmask registers; plain ST, TT and Falcon
;       take the cache), 2 = pre-shifted cache (also any other value), 3 = original code (the last three are for tests: wwab.py `--poke`, the differential test tools/wwblit.py).
;       A. BLITTER (HOG): per plane p, pass 1 D &= mask (LOP 1, source = M0/M1 of every row), pass 2 D |= plane (LOP 7, source = the plane words); skew s, NFSR (SKEW bit 6), source xinc 10, source yinc 10,
;       xcount 3, destination xinc 8, yinc 144; endmask1 = $ffff >> s and endmask3 = $ffff << (16-s) in BOTH passes.  8 passes; HOG so the CPU stalls and the next CPU access to the buffer sees the finished
;       sprite.  The blitter path needs no sprite-sheet range: it reads whatever a1 points to.
;       B. PRE-SHIFTED CACHE (every machine): the shifted result is computed once per (a1, s) and cached; per row 36 B: three mask longs + six plane longs in screen order; the draw is movem + 5 and.l +
;       5 or.l + movem + a sixth long, ~325 cycles per row.  8 sets x 6 ways x 1280 B slots (up to 32 rows) = 61440 B at $df400 (HIGH area, memory_plan.md 3.2), tags at $df010; a hit needs the same a1
;       and s and at least the requested rows (a larger request rebuilds); only sprite-sheet addresses SHEET0..SHEET1 (SPRITE16 $320c0 .. SPRITE32 end $4475c, loaded by the level set-up to fixed
;       addresses [INFERENCE: static data, see RESULTS_stage05.md for the write watch]).  Initialised lazily at the first call (magic word in HDR).
;       Registers as the original leaves them: a0 += 160*rows, a1 += 20*rows, d0 = s, d1 = $88, d2.w = $ffff, a2-a6 and the high word of d2 untouched, d3-d7 clobbered.
BLT     equ     $df004                          ; long: $b17e000m, m = mode (anything else = auto)
SYIN    equ     10
HDR     equ     $df000
TAGS    equ     $df010
SCR     equ     $df300
SLOTS   equ     $df400
SHEET0  equ     $320c0                          ; first byte of SPRITE16.PAK's unpacked sheet (resource 2)
SHEET1  equ     $4475c                          ; end of SPRITE32 (resource 5: $3dbdc + 27520)
MAGIC   equ     $50524530                       ; 'PRE0'
        org     $1325e
        jmp     $75f20.l

        org     $75f20
blit:   move.l  BLT.l,d1
        cmpi.l  #$b17e0001,d1
        beq.s   .go
        cmpi.l  #$b17e0003,d1
        beq.w   .cpu                    ; 3 = the original code (test mode)
        bra.w   pre                     ; 2 (or anything else: `init` did not run): the pre-shifted cache
.go:    move.w  #10,$ffff8a20.w         ; source X inc
        move.w  #SYIN,$ffff8a22.w       ; source Y inc
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
        move.b  #7,$ffff8a3b.w          ; LOP = S OR D (the same endmasks: the first/last word's other bits come from the shifter's
                                        ; previous word, whatever it was, and must not be written)
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
        jmp     $13264.l


pre:    tst.w   d0
        beq.w   .cpu                    ; s = 0
        cmpi.w  #32,d2
        bhi.w   .cpu
        cmpa.l  #SHEET0,a1
        bcs.w   .cpu
        cmpa.l  #SHEET1,a1
        bcc.w   .cpu
        movem.l d0/d2/a1-a3,-(a7)       ; d0 = s, d2 = rows, a1 = rows address are restored at the end; a2/a3 belong to the callers
        cmpi.l  #MAGIC,HDR.l
        beq.s   .ini
        bsr.w   init
.ini:   move.l  a1,d1
        lsr.l   #3,d1
        add.w   d1,d1
        add.w   d0,d1
        move.w  d1,d3
        lsr.w   #4,d3
        eor.w   d3,d1
        andi.w  #7,d1                   ; set
        mulu    #80,d1
        lea     TAGS.l,a2
        adda.w  d1,a2                   ; set record: +0 rr.w, +2.. 6 entries {a1.l, data.l, s.w, rows.w}
        lea     2(a2),a3
        moveq   #5,d3
.w:     cmpa.l  (a3),a1
        bne.s   .n
        cmp.w   8(a3),d0
        beq.s   .found
.n:     lea     12(a3),a3
        dbra    d3,.w
        move.w  (a2),d3                 ; miss: round-robin victim
        move.w  d3,d4
        addq.w  #1,d4
        cmpi.w  #6,d4
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
        bls.s   .draw
        move.w  d2,10(a3)               ; (re)build the entry for this many rows
        move.w  d2,d7
        bsr.w   build
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
        movem.l (a7)+,d0/d2/a1-a3       ; the caller's s, rows, a1, a2, a3
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
        jmp     $13264.l

; build: a1 = sprite rows, d0 = s, d7 = rows, a3 = the cache entry (data pointer at 4(a3)).  Clobbers d1, d3-d7, a1, a2; keeps a3.
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

; init: tags cleared, data pointers assigned (slot i at SLOTS + 1280*i, 6 ways per set), then the magic.  Clobbers d3, a2, a3.
init:   lea     TAGS.l,a2
        lea     SLOTS.l,a3
        moveq   #7,d3
.s:     clr.w   (a2)+                   ; round-robin counter
        moveq   #5,d4
.e:     clr.l   (a2)+                   ; tag
        move.l  a3,(a2)+                ; data pointer
        clr.w   (a2)+                   ; s
        clr.w   (a2)+                   ; rows built
        lea     1280(a3),a3
        dbra    d4,.e
        lea     6(a2),a2                ; record stride 80
        dbra    d3,.s
        move.l  #MAGIC,HDR.l
        rts

; init (core.s calls it in supervisor mode, TOS's vectors and cookie jar intact: the game image overwrites $5a0, the _p_cookies pointer, so it cannot be asked later; may not use a2 unsaved):
; BLT = $b17e0001 (blitter) iff the _MCH cookie high word is 1 (STE hardware family: STE, Mega STE; ST 0, TT 2, Falcon 3) AND the blitter's endmask registers read back and BUSY is clear
; (bus-error safe), else $b17e0002 (pre-shifted cache).  The data span $df000.. is zero-filled by the stub's records before `init` runs.
        org     $762e0
init:   movem.l d0-d4/a0-a3,-(a7)
        move.l  #$b17e0002,d4
        move.l  $5a0.w,d0
        beq.s   .set
        movea.l d0,a0
.ck:    move.l  (a0)+,d0
        beq.s   .set
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .ck
        swap    d1
        cmpi.w  #1,d1
        bne.s   .set
        movea.l a7,a2                   ; where the bus error handler resets the stack
        movea.l $8.w,a3
        lea     .berr(pc),a0
        move.l  a0,$8.w
        move.w  #$5aa5,$ffff8a28.w
        cmpi.w  #$5aa5,$ffff8a28.w
        bne.s   .no
        move.w  #$a55a,$ffff8a2a.w
        cmpi.w  #$a55a,$ffff8a2a.w
        bne.s   .no
        btst    #7,$ffff8a3c.w          ; BUSY must be clear
        bne.s   .no
        move.l  #$b17e0001,d4
.no:    move.l  a3,$8.w
.set:   move.l  d4,BLT.l
        movem.l (a7)+,d0-d4/a0-a3
        rts
.berr:  movea.l a2,a7
        bra.s   .no
