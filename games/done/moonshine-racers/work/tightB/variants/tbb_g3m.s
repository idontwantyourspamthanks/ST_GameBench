; name: tbb_g3m
; default: no
; site: $39a0
; requires: tbb_g3m11 tbb_g3m13 tbb_g3m15
; conflicts: tbb_h tbb_h11 tbb_h13 tbb_h15 tbb_800 tbb_80011 tbb_80013 tbb_80015 tb_blit tb_blit11 tb_blit13 tb_blit15
; data: $B5800 512
; doc: STE blitter for the shifted 1-3 column sprites that win (enough rows); stock kernels for everything else, no blitter, TT/Falcon, Mega STE and 68010+ (generated from work/tightB/blit_template.s; select tb_blit tb_blit11 tb_blit13 tb_blit15 together).
; note: Generated file (work/tightB/gen_blit.py, BUDGET=900 GUARD=1 GTH=3).  Sites: the kernel pointer tables `$399c` (nibble 7), `$39b0` (11), `$39c4` (13), `$3a14` (15): the 1-, 2- and 3-column entries point at 16-byte stubs
; note: at $B4510... (one patch file per table: tb_blit = nibble 7 + the blob, tb_blit11/13/15).  Hooking the tables (not `$ed6e`) keeps it working with the tc_* object-stage patches, which call the same entries without `$ecc8`.  4 columns stay stock (nibble 7: tb_car).
; note: A stub sets d4 = columns, a2 = descriptor, d3 = the stock entry and jumps to `common`, which jumps to the stock entry (registers untouched, d7 clamped to the screen bottom like the stock kernel does) unless: blitter present (probe at the first call:
; note: supervisor, plain 68000, no Mega STE register $ff8e21 (it bus-errors on an ST/STE), $ff8a28 reads back what was written), x & 15 != 0, x >= 0, y >= 0, all destination columns on screen, rows >= minimum (1 col 16, 2 cols 10, 3 cols 16).
; note: Blit formulation (work/notes/sprites.md section 6): mask T = OR of the data planes (P passes into TMP $B5880), D &= ~T on the 4 destination planes, D |= S per data plane; 3-column rows are a plane-major pair + one single column (two groups).
; note: Burst limit: rows per pass are chosen so that one pass moves at most BUDGET=900 cycles of words (12 cycles each).  GUARD=1: before every pass Timer B is checked: the pass starts only if TBCR $fffffa1b != 8 (Timer B stopped: the ISR $d616 stops it after
; note: the last band of a frame) or the data register $fffffa21 >= GTH=3 (the next raster interrupt is then at least GTH-1 scanlines away); otherwise the CPU spins (bounded) until the raster interrupt has run.
BL      equ     $ffff8a00
BST     equ     $B5800                  ; b: 0 = not probed, 1 = blitter path on, 2 = off
SAVSP   equ     $B5804
TMP     equ     $B5880                  ; mask rows
BUDGET  equ     900
GUARD   equ     1
GTH     equ     3

        org     $39a0
        dc.l    $B4510,$B4520,$B4530            ; kernel pointer table $399c (nibble 7): 1, 2, 3 columns (4 columns = tb_car / stock)

        org     $B4500
; 12 stubs of 16 bytes (the kernel pointer tables of nibbles 7 / 11 / 13 / 15 point here): d4 = columns, a2 = descriptor, d3 = the stock entry
STUB    macro   ; label, cols, descriptor, stock entry
\1:     moveq   #\2,d4
        lea     \3(pc),a2
        move.l  #\4,d3
        bra.w   common
        endm
        dcb.b   16,0
        STUB    s_n7c1,1,d7_,$12994
        STUB    s_n7c2,2,d7_,$12f60
        STUB    s_n7c3,3,d7_,$13662
        STUB    s_n11c1,1,d11_,$12a98
        STUB    s_n11c2,2,d11_,$130e2
        STUB    s_n11c3,3,d11_,$1384c
        STUB    s_n13c1,1,d13_,$12bac
        STUB    s_n13c2,2,d13_,$1327e
        STUB    s_n13c3,3,d13_,$13a5e
        STUB    s_n15c1,1,d15_,$12ce0
        STUB    s_n15c2,2,d15_,$1345a
        STUB    s_n15c3,3,d15_,$13cc8

        dcb.b   $B4600-*,0
PASS    macro
        ifne    GUARD
        cmpi.b  #8,$fffffa1b.w         ; Timer B running (event count)?
        bne.s   .pg\@
        cmpi.b  #GTH,$fffffa21.w
        bcc.s   .pg\@
        bsr.w   gwait
.pg\@:
        endc
        move.b  #$c0,BL+$3c.w           ; start + HOG
        endm
; contract = the stock FULL entries: d0 = x, d1 = y, d7 = rows, a1 = bitmap rows, a5 = screen; every fallback jumps to the stock entry with these untouched (d7 only clamped to the screen bottom like the stock kernel does)
fb:     movea.l d3,a0
        jmp     (a0)
common: cmpi.b  #1,BST.l
        bne.w   .nb
.go:    moveq   #15,d6
        and.w   d0,d6                   ; shift
        beq.w   fb
        tst.w   d0
        bmi.w   fb
        tst.w   d1
        bmi.w   fb
        move.w  #200,d2
        sub.w   d1,d2
        ble.w   fb
        cmp.w   d2,d7
        ble.s   .r
        move.w  d2,d7                   ; the stock clamp to the screen bottom
.r:     tst.w   d7
        ble.w   fb                     ; rows <= 0: the stock kernel returns
        lea     minr(pc),a0
        cmp.b   (a0,d4.w),d7
        bcs.w   fb
        move.w  d0,d2
        lsr.w   #4,d2                   ; X0
        move.w  d2,d5
        add.w   d4,d5
        cmpi.w  #19,d5                  ; X0 + cols + 1 <= 20
        bgt.w   fb
        move.w  d4,d5
        addq.w  #1,d5                   ; n = destination words per row
        move.w  d1,d3                   ; dest = a5 + y * 160 + X0 * 8
        lsl.w   #5,d3
        move.w  d3,d0
        add.w   d3,d3
        add.w   d3,d3
        add.w   d0,d3
        lsl.w   #3,d2
        add.w   d2,d3
        move.w  d3,$100c.l              ; the stock kernel's scratch word
        lea     (a5,d3.w),a3
        move.w  (a2),d3                 ; 2P
        mulu.w  d4,d3                   ; source bytes per row
        move.l  a6,-(a7)
        cmpi.w  #3,d4
        bcc.s   .many
        bsr.w   grp                     ; 1 or 2 columns: one group
        movea.l (a7)+,a6
        rts
.many:  movem.l d4/d7/a1/a3,-(a7)       ; 3 columns: the plane-major pair, then one single column
        moveq   #2,d4
        bsr.w   grp
        movem.l (a7)+,d4/d7/a1/a3
        move.w  (a2),d0
        add.w   d0,d0
        adda.w  d0,a1                   ; 4P bytes: the pair
        lea     16(a3),a3
        moveq   #1,d4
        bsr.w   grp
        movea.l (a7)+,a6
        rts
.nb:    cmpi.b  #2,BST.l
        beq.w   fb
        bsr.w   probe
        cmpi.b  #1,BST.l
        beq.w   .go
        bra.w   fb

minr:   dc.b    0,16,10,16
; descriptors: 2P, dest byte offsets of the P data planes, P
d7_:    dc.w    6,0,2,4,0,3
d11_:   dc.w    6,0,2,6,0,3
d13_:   dc.w    6,0,4,6,0,3
d15_:   dc.w    8,0,2,4,6,4
cht:    dc.w    0,BUDGET/12,BUDGET/24,BUDGET/36,BUDGET/48,BUDGET/60

; grp: draw d4 columns (1 or 2) of d7 rows at a1 -> a3, shift d6, d3 = source bytes per sprite row, a2 = descriptor.  Clobbers d0-d2, d5, d7, a0, a1, a3, a4, a6.
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
        moveq   #16,d2
        sub.w   d6,d2
        lsl.w   d2,d0
        move.w  d0,-(a7)                ; em3
        move.w  d6,d0
        ori.w   #$40,d0
        move.w  d0,-(a7)                ; skew byte
chunk:  move.w  d7,d2                   ; rows of this chunk
        cmp.w   d1,d2
        ble.s   .c1
        move.w  d1,d2
.c1:    movem.l d1/d7,-(a7)
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
        PASS
        move.b  #7,BL+$3b.w             ; LOP = S | D for the other planes
.mb:    adda.l  a4,a0
        move.l  a0,BL+$24.w
        move.l  #TMP,BL+$32.w
        move.w  d2,BL+$38.w
        PASS
        subq.w  #1,d7
        bne.s   .mb
        move.l  #$00020002,BL+$20.w     ; mask apply: D &= ~M on the 4 destination planes
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
        PASS
        addq.l  #2,d0
        dbra    d7,.ma
        move.w  d3,d0                   ; data: D |= S per present plane
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
        PASS
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

        ifne    GUARD
gwait:  move.w  d0,-(a7)                ; bounded spin until Timer B's counter is >= GTH again (the raster interrupt has run) or Timer B stops
        move.w  #400,d0
.l:     cmpi.b  #8,$fffffa1b.w
        bne.s   .x
        cmpi.b  #GTH,$fffffa21.w
        bcc.s   .x
        dbra    d0,.l
.x:     move.w  (a7)+,d0
        rts
        endc

; probe: STE/ST blitter on a plain 68000 (no Mega STE register $ff8e21) in supervisor mode -> BST = 1, else 2.  Preserves all registers.
probe:  movem.l d0-d2/a0-a1,-(a7)
        move.w  sr,d2
        btst    #13,d2
        beq.w   .off
        move.w  #$2700,sr
        move.l  a7,SAVSP.l
        movea.l $10.w,a1
        move.l  #.ill,$10.w
        move.l  #$ffffffff,d0
        dc.w    $42c0                   ; move.w ccr,d0: illegal on a 68000
        move.l  a1,$10.w
        swap    d0
        tst.w   d0
        bne.s   .off                    ; 68010 or later
        movea.l $8.w,a1
        move.l  #.be1,$8.w
        move.b  $ff8e21.l,d0            ; Mega STE cache/speed register
        move.l  a1,$8.w
        bra.s   .off                    ; no bus error: Mega STE
.be1:   movea.l SAVSP.l,a7
        move.l  a1,$8.w
        movea.l $8.w,a1
        move.l  #.be2,$8.w
        move.w  #$5aa5,$ff8a28.l        ; blitter endmask 1 reads back
        move.w  $ff8a28.l,d0
        move.l  a1,$8.w
        move.w  #$ffff,$ff8a28.l
        cmpi.w  #$5aa5,d0
        bne.s   .off
        move.b  #1,BST.l
        bra.s   .out
.be2:   movea.l SAVSP.l,a7
        move.l  a1,$8.w
        bra.s   .off
.ill:   addq.l  #2,2(a7)
        moveq   #0,d0
        rte
.off:   move.b  #2,BST.l
.out:   move.w  d2,sr
        movem.l (a7)+,d0-d2/a0-a1
        rts
