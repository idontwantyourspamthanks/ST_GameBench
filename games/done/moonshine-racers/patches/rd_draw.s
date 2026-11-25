; name: rd_draw
; default: yes
; site: $17c42
; orig: 22784b8445f84ff8
; ram: $CB000-$D7FFF  rd_draw window tables (2 x 24 KB), colour table copy, table pointer WPTR; zero at game start, built lazily behind WPTR
; doc: Faster road span draw $17c42 (pixel-identical): per-row control logic rewritten, the two edge windows of a row come from generated per-(width, shift, stripe colour) tables instead of the edge routine.
; note: Moonshine Racers road study (work/notes/road.md).  Site $17c42 (`movea.l $4b84.w,a1 / lea.l $4ff8.w,a2`) -> `jmp $B5004.l` ($B5000 = the pre-warm entry used by rd_init).
; note: A row is [grass][edge window A: 2 groups][road][edge window B: 2 groups][grass].  The windows depend only on (w0 class, A&15 or B&15, stripe colour bits 15-13 of the flags) and on the level colour table ($135a):
; note: they are generated once per colour table by calling the stock edge routine $1058a (3072 calls, about 1.7 M cycles, on the first draw after a colour-table change) into 2 x 24 KB at $CB000.
; note: Rows the fast path does not cover (edges closer than 32 px, w0 > $b00) hand the rest of the frame to the stock loop at $17c66; the whole frame runs stock when $13a0 != 0 (far-colour reload).
; note: Run-time tables are declared with `; ram:` (not `; data:`: payload image limit): $CB000-$D7FFF of the free RAM run $B2700-$E2BFF (top = $E2BFF: TOS 2.06 1 MB Mega STE GEM data from $E2C50, integration.md section 10.3).
WT      equ     $CB000          ; window tables: A at WT, B at WT+$6000 (each k*2048 + combo*256 + shift*16, 16 bytes), colour table copy at WT+$C000 (48 bytes), WPTR at WT+$C040
CT      equ     WT+$C000
WPTR    equ     WT+$C040        ; the $135a value the tables were built for (0 = none)
        org     $17c42
        jmp     $B5004.l

        org     $B5000
TBL     macro                           ; \1 family number, \2 continuation: jump table entry n (index 4n) -> chain entry; n = 2m -> even chain + 4*(10-m), n = 2m+1 -> odd chain + 4*(9-m)
t\1:    bra.w   \2                      ; n = 0 (callers never use it)
nn      set     1
        rept    20
        ifne    nn&1
        bra.w   c\1_odd+4*(9-nn/2)
        else
        bra.w   c\1_even+4*(10-nn/2)
        endif
nn      set     nn+1
        endr
        endm
CH      macro                           ; \1 family number, \2 continuation: unrolled fills of the pattern a2,a3,a4,a6 (2 groups per movem)
c\1_even:
        rept    10
        movem.l a2-a4/a6,-(a0)
        endr
        bra.w   \2
c\1_odd:
        rept    9
        movem.l a2-a4/a6,-(a0)
        endr
        movem.l a2-a3,-(a0)
        bra.w   \2
        endm
; $B5000 = pre-warm entry (called once per race by rd_init): builds the window tables now instead of in the first road frame
        bra.w   rdd_init
rd_draw:
        tst.b   $13a0.l
        bne.w   rd_stock0
        move.l  $135a.w,d0
        beq.w   rd_stock0
        cmp.l   WPTR.l,d0
        beq.s   .ok
        movea.l d0,a0
        bsr.w   gen_win
.ok:    movea.l $4b84.w,a1
        movea.l $1008.l,a0
        lea     $7d00(a0),a0
        lea     WT+$6000.l,a5
        move.w  #$6d,d7
rd_rec: movem.w (a1)+,d0-d3             ; w0, A, B, F
        cmp.w   #$b00,d0
        bhi.w   rd_mid
        move.w  d1,d4
        and.w   #$fff0,d4               ; Aal
        move.w  d2,d5
        and.w   #$fff0,d5               ; Bal
        move.w  d4,d6
        sub.w   d5,d6
        cmp.w   #32,d6
        blt.w   rd_mid                  ; edges closer than 32 px (or crossed): stock
        lsl.w   #3,d0                   ; k << 11
        move.w  d3,d6
        lsr.w   #5,d6
        and.w   #$700,d6                ; combo << 8
        add.w   d6,d0                   ; K
        sub.w   d4,d1                   ; d1 & 15 (since d4 = d1 & $fff0)
        lsl.w   #4,d1
        add.w   d0,d1
        sub.w   #$6000,d1               ; window A index (A table sits below a5)
        sub.w   d5,d2                   ; d2 & 15 (since d5 = d2 & $fff0)
        lsl.w   #4,d2
        add.w   d0,d2                   ; window B index
        cmp.w   #288,d4                 ; both edge windows fully on screen (0 <= Aal, Bal <= 288, Aal >= Bal + 32): no clipping at all
        bhi.w   rd_gen
        cmp.w   #288,d5
        bhi.w   rd_gen
        move.w  #288,d6
        sub.w   d4,d6
        beq.w   rd_fa
        lsr.w   #2,d6
        tst.w   d3
        bmi.s   .g1b
        movem.l $6000(a5),a2-a3
        bra.s   .g1c
.g1b:   movem.l $6008(a5),a2-a3
.g1c:   movea.l a2,a4
        movea.l a3,a6
        jmp     tu1(pc,d6.w)
        TBL     u1,rd_fa
rd_fa:  movem.l (a5,d1.w),a2-a4/a6
        movem.l a2-a4/a6,-(a0)
        move.w  d4,d6
        sub.w   d5,d6
        sub.w   #32,d6
        beq.w   rd_fb
        lsr.w   #2,d6
        btst    #14,d3
        bne.s   .i3
        movem.l $6010(a5),a2-a3
        bra.s   .i4
.i3:    movem.l $6018(a5),a2-a3
.i4:    movea.l a2,a4
        movea.l a3,a6
        jmp     tu2(pc,d6.w)
        TBL     u2,rd_fb
rd_fb:  movem.l (a5,d2.w),a2-a4/a6
        movem.l a2-a4/a6,-(a0)
        move.w  d5,d6
        beq.w   rd_end
        lsr.w   #2,d6
        tst.w   d3
        bmi.s   .g4b
        movem.l $6000(a5),a2-a3
        bra.s   .g4c
.g4b:   movem.l $6008(a5),a2-a3
.g4c:   movea.l a2,a4
        movea.l a3,a6
        jmp     tu3(pc,d6.w)
        TBL     u3,rd_end
        ; ---- generic rows (some edge window clipped or off screen)
rd_gen: move.w  #288,d6
        sub.w   d4,d6
        ble.w   rd_awin
        lsr.w   #2,d6
        cmp.w   #80,d6
        ble.s   .g1
        moveq   #80,d6
.g1:    tst.w   d3
        bmi.s   .g1b
        movem.l $6000(a5),a2-a3
        bra.s   .g1c
.g1b:   movem.l $6008(a5),a2-a3
.g1c:   movea.l a2,a4
        movea.l a3,a6
        jmp     t1(pc,d6.w)
        TBL     1,rd_awin
rd_awin: ; ---- edge window A
        cmp.w   #320,d4
        bge.s   rd_int
        cmp.w   #-16,d4
        blt.w   rd_end
        movem.l (a5,d1.w),a2-a4/a6
        cmp.w   #304,d4
        bge.s   .a_left
        tst.w   d4
        bpl.s   .a_both
        movem.l a4/a6,-(a0)             ; Aal = -16: only the right group is on screen
        bra.w   rd_end
.a_left: movem.l a2-a3,-(a0)
        bra.s   rd_int
.a_both: movem.l a2-a4/a6,-(a0)
rd_int: cmp.w   #16,d4
        blt.w   rd_end
        move.w  #320,d6
        cmp.w   d6,d4
        bge.s   .i1
        move.w  d4,d6
.i1:    cmp.w   #-16,d5
        blt.s   .i2
        sub.w   d5,d6
        sub.w   #32,d6
.i2:    cmp.w   #1,d6
        blt.w   rd_bwin
        lsr.w   #2,d6
        btst    #14,d3
        bne.s   .i3
        movem.l $6010(a5),a2-a3
        bra.s   .i4
.i3:    movem.l $6018(a5),a2-a3
.i4:    movea.l a2,a4
        movea.l a3,a6
        jmp     t2(pc,d6.w)
        TBL     2,rd_bwin
rd_bwin: ; ---- edge window B
        cmp.w   #-16,d5
        blt.w   rd_end
        cmp.w   #320,d5
        bge.s   rd_f4
        movem.l (a5,d2.w),a2-a4/a6
        cmp.w   #304,d5
        bge.s   .b_left
        tst.w   d5
        bpl.s   .b_both
        movem.l a4/a6,-(a0)
        bra.s   rd_f4
.b_left: movem.l a2-a3,-(a0)
        bra.s   rd_f4
.b_both: movem.l a2-a4/a6,-(a0)
rd_f4:  cmp.w   #16,d5
        blt.s   rd_end
        move.w  d5,d6
        lsr.w   #2,d6
        cmp.w   #80,d6
        ble.s   .g4
        moveq   #80,d6
.g4:    tst.w   d3
        bmi.s   .g4b
        movem.l $6000(a5),a2-a3
        bra.s   .g4c
.g4b:   movem.l $6008(a5),a2-a3
.g4c:   movea.l a2,a4
        movea.l a3,a6
        jmp     t3(pc,d6.w)
        TBL     3,rd_end
rd_end: move.l  2(a1),d0                ; next record's A:B (Z = terminator)
        dbeq    d7,rd_rec
        beq.s   .fin
        moveq   #0,d7
.fin:   move.w  d7,$12f4.l
        move.l  a0,$12f0.l
        rts
        ; the fast path gave up on this row: finish the frame with the stock loop from the current record
rd_mid: move.w  -8(a1),d2
        move.l  -6(a1),d1
        subq.l  #2,a1                   ; the stock loop reads the flags word itself
        lea     $4ff8.w,a2
        lea     $1058a.l,a4
        movea.l $135a.w,a5
        jmp     $17c66.l
rd_stock0: movea.l $4b84.w,a1
        lea     $4ff8.w,a2
        jmp     $17c4a.l

        CH      u1,rd_fa
        CH      u2,rd_fb
        CH      u3,rd_end
        CH      1,rd_awin
        CH      2,rd_bwin
        CH      3,rd_end

; rdd_init: the window-table generation the first road frame would run when $135a differs from the table pointer the windows were built for
rdd_init:
        tst.b   $13a0.l
        bne.s   .x
        move.l  $135a.w,d0
        beq.s   .x
        cmp.l   WPTR.l,d0
        beq.s   .x
        movea.l d0,a0
        bsr.w   gen_win
.x:     rts

; gen_win: a0 = game colour table ($135a value).  Builds the window tables (stock edge routine $1058a applied to the pattern table $4ff8 masks) and the colour copy.
gen_win:
        movem.l d0-d7/a0-a6,-(a7)
        movea.l a0,a5                   ; the stock edge routine reads its colours through a5
        lea     CT.l,a1
        moveq   #11,d0
.cc:    move.l  (a0)+,(a1)+
        dbra    d0,.cc
        lea     WT.l,a2                 ; output pointer: orientation A table, then B
        suba.l  a4,a4                   ; orientation 0 = A
.or:    lea     $4ff8.w,a3              ; pattern table row k (256 bytes each), k = 0..11
.k:     moveq   #0,d3                   ; combo
.cb:    move.w  d3,d7
        ror.w   #3,d7                   ; d7 = combo << 13 (bits 15-13 select the colour variants)
        movea.l a3,a6
        moveq   #15,d1                  ; shifts 0..15
.s:     cmpa.w  #0,a4
        bne.s   .ob
        move.l  8(a6),d4                ; A edge: right of the boundary = grass (d4), edge band (d5), left = road (d6)
        move.l  4(a6),d5
        move.l  (a6),d6
        bra.s   .go
.ob:    move.l  (a6),d4                 ; B edge: left = grass, band, right = road
        move.l  4(a6),d5
        move.l  8(a6),d6
.go:    jsr     $1058a.l                ; d1, d3, d5, d7 and the address registers are preserved; outputs d0, d2, d4, d6
        swap    d0
        swap    d2
        swap    d4
        swap    d6
        movem.w d0/d2/d4/d6,(a2)        ; left group (high words)
        swap    d0
        swap    d2
        swap    d4
        swap    d6
        movem.w d0/d2/d4/d6,8(a2)       ; right group (low words)
        lea     16(a2),a2
        lea     16(a6),a6
        dbra    d1,.s
        addq.w  #1,d3
        cmp.w   #8,d3
        bne.s   .cb
        lea     $100(a3),a3
        cmpa.l  #$4ff8+$c00,a3
        bne.s   .k
        cmpa.w  #0,a4
        bne.s   .done
        lea     1(a4),a4
        bra.s   .or
.done:  move.l  32(a7),WPTR.l           ; a0 as pushed = the colour table pointer
        movem.l (a7)+,d0-d7/a0-a6
        rts
