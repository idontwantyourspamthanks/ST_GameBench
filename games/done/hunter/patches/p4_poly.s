; name: p4_poly
; default: yes
; site: $7554
; note: item (d) polygon scan converter (work/notes/p4_raster.md section 4). Replaces $7554..$76f8 of sub_007518 (the polygon body
; note: after the colour set-up and the vertex-count decode; also the target of the $7504 entry) by a re-implementation:
; note:  A  vertex loop with registers instead of the stack, ring list of record pointers (own buffer),
; note:  B  the original y rejection tests ($1618 stays exactly as the original leaves it),
; note:  C  exact early rejection of polygons that provably draw nothing (all rows left of x=0 or right of x=319),
; note:  D  edge walk by blocks of rows (min of the two edge run lengths) instead of two counters per row; rows above the screen
; note:    only advance the accumulators; span buffer P4_SPAN,
; note:  E  span loop with table masks and the original self-modified fill dispatch ($76ee).
; note: Anything unusual (n < 3 vertices, an edge with dy < 0, no top edge) re-enters the ORIGINAL code at $755a with the
; note: original machine state, so those polygons are drawn exactly as before.
; note: Free registers on return: the original clobbers d0-d7/a0-a4 as well (callers reload a0 from $1600(a5)).
P4_N    equ     $8d000
P4_A0   equ     $8d002
P4_SKIP equ     $8d006
P4_EMIT equ     $8d008
P4_ROWS equ     $8d00a
P4_SCR  equ     $8d00c
P4_RING equ     $8d010
P4_SPAN equ     $8d100
P4_LTAB equ     $8ce00
; data: $8d000 864
        org     $7554
        jmp     $8c400.l

        org     $8c400
p4_poly:
        move.w  d0,P4_N.l
        move.l  a0,P4_A0.l
        cmp.w   #3,d0
        blo     .fb
        lea     P4_RING.l,a1
        move.w  d0,d7
        add.w   d7,d7
        lea     (a1,d7.w),a2
        move.w  d0,d7
        subq.w  #1,d7
        move.w  #$8000,d3               ; y max
        move.w  #$7fff,d2               ; best (top) y
        move.w  d2,d1                   ; best slope low word
        move.w  d2,d6                   ; best x
        moveq   #0,d5                   ; best: address of the ring entry after the top edge
.v:     moveq   #0,d0
        move.b  (a0)+,d0
        lsl.w   #4,d0
        lea     (a4,d0.w),a3            ; edge record
        move.w  a3,(a1)+                ; ring entries are record addresses (< $8000)
        move.w  a3,(a2)+
        movem.w 4(a3),d0/d4             ; y0, dy
        tst.w   d4
        bmi     .fb
        add.w   d0,d4                   ; y bottom
        cmp.w   d4,d3
        bge.s   .a
        move.w  d4,d3
.a:     cmp.w   d0,d2
        blt.s   .nx
        bgt.s   .tk
        cmp.w   2(a3),d6
        blt.s   .nx
        bgt.s   .tk
        cmp.w   $a(a3),d1
        ble.s   .nx
.tk:    move.w  2(a3),d6
        move.w  $a(a3),d1
        move.w  d0,d2
        move.l  a1,d5
.nx:    dbra    d7,.v
        tst.l   d5
        beq     .fb
        move.l  a0,$1600(a5)
        cmp.w   #$8c,d2
        blt.s   .y1
.st:    st.b    $1618(a5)
        rts
.y1:    tst.w   d3
        bmi.s   .st
        cmp.w   #$8c,d3
        ble.s   .y2
        move.w  #$8c,d3
.y2:    sub.w   d2,d3
        bmi.s   .st
        beq.s   .y3
        subq.w  #1,d3
.y3:    move.w  P4_N.l,d0
        add.w   d0,d0
        movea.l d5,a4                   ; right chain
        lea     (a4,d0.w),a3            ; left chain (predecrement)
        movea.w -2(a3),a2               ; top edge
        move.l  2(a2),d2                ; x0:y0
        movea.w (a4),a1                 ; next edge
        cmp.l   2(a1),d2
        beq.s   .ok
        tst.b   $1619(a5)
        beq.s   .st
        subq.w  #2,a4
        subq.w  #2,a3
.ok:    move.w  d2,d0                   ; top y
        bpl.s   .t0
        add.w   d3,d0                   ; E-1
        bmi.s   .st                     ; completely above the screen
        addq.w  #1,d0
        move.w  d0,P4_EMIT.l
        neg.w   d2
        move.w  d2,P4_SKIP.l            ; rows above the screen
        moveq   #0,d4
        bra.s   .t1
.t0:    move.w  d3,d1
        addq.w  #1,d1
        move.w  d1,P4_EMIT.l
        clr.w   P4_SKIP.l
        move.w  d2,d4
.t1:    mulu.w  #160,d4
        add.l   $144(a5),d4
        move.l  d4,P4_SCR.l
        sf.b    $1618(a5)
; ---- C: early rejection (exact, see p4_raster.md) --------------------------------------------------------------------
        lea     P4_RING.l,a1
        movea.w (a1),a2
        move.w  2(a2),d0
        blt     .xleft
        cmp.w   #320,d0
        blt     .scan
        move.w  P4_N.l,d7
        subq.w  #1,d7
.xr:    movea.w (a1)+,a2
        move.w  2(a2),d0
        cmp.w   #320,d0
        blt     .scan
        cmp.w   #8191,d0
        bgt     .scan
        ext.l   d0
        lsl.l   #5,d0                   ; A = x0*32
        move.w  6(a2),d1
        bgt.s   .r1
        moveq   #1,d1
.r1:    move.l  8(a2),d2
        cmp.w   #1,d1
        beq.s   .r2
        muls.w  d1,d2                   ; S = slope * max(dy,1)  (slope fits a word when dy >= 2)
.r2:    tst.l   d2
        bmi.s   .rn
        add.l   d0,d2                   ; hi = A + S   (lo = A >= 10240)
        cmp.l   #$fffff,d2
        bgt     .scan
        bra.s   .rx
.rn:    add.l   d0,d2                   ; lo = A + S   (hi = A <= 262112)
        cmp.l   #10240,d2
        blt     .scan
.rx:    dbra    d7,.xr
        rts                             ; every row is empty: nothing to draw ($1618 = sf as the original leaves it)
.xleft: move.w  P4_N.l,d7
        subq.w  #1,d7
.xl:    movea.w (a1)+,a2
        move.w  2(a2),d0
        bge     .scan
        ext.l   d0
        lsl.l   #5,d0                   ; A < 0
        move.w  6(a2),d1
        bgt.s   .l1
        moveq   #1,d1
.l1:    move.l  8(a2),d2
        cmp.w   #1,d1
        beq.s   .l2
        muls.w  d1,d2
.l2:    tst.l   d2
        bmi.s   .l3
        add.l   d2,d0                   ; hi = A + S
        bge     .scan
.l3:    dbra    d7,.xl
        rts
; ---- D: edge walk ---------------------------------------------------------------------------------------------------------
.scan:  moveq   #0,d3                   ; rows left on the left edge
        moveq   #0,d4                   ; rows left on the right edge
        move.w  P4_SKIP.l,d0
        beq.s   .emit
        move.w  d0,P4_ROWS.l
.sb:    bsr     .ensure
        move.w  d3,d2
        cmp.w   d4,d2
        ble.s   .s1
        move.w  d4,d2
.s1:    move.w  P4_ROWS.l,d0
        cmp.w   d0,d2
        ble.s   .s2
        move.w  d0,d2
.s2:    sub.w   d2,d3
        sub.w   d2,d4
        sub.w   d2,d0
        move.w  d0,P4_ROWS.l
        subq.w  #1,d2
.sr:    add.l   a0,d6
        add.l   d5,d7
        dbra    d2,.sr
        tst.w   d0
        bne.s   .sb
.emit:  move.w  P4_EMIT.l,P4_ROWS.l
        lea     P4_SPAN.l,a1
.eb:    bsr     .ensure
        move.w  d3,d2
        cmp.w   d4,d2
        ble.s   .e1
        move.w  d4,d2
.e1:    move.w  P4_ROWS.l,d0
        cmp.w   d0,d2
        ble.s   .e2
        move.w  d0,d2
.e2:    sub.w   d2,d3
        sub.w   d2,d4
        sub.w   d2,d0
        move.w  d0,P4_ROWS.l
        subq.w  #1,d2
.er:    move.l  d6,d0
        move.l  d7,d1
        cmp.l   d0,d1
        bge.s   .o1
        exg     d0,d1
.o1:    asr.l   #5,d1
        bmi.s   .em
        cmp.w   #319,d1
        ble.s   .o2
        move.w  #319,d1
.o2:    asr.l   #5,d0
        bpl.s   .o3
        moveq   #0,d0
.o3:    cmp.w   d0,d1
        bge.s   .o4
.em:    moveq   #-1,d1
.o4:    move.w  d0,(a1)+
        move.w  d1,(a1)+
        add.l   a0,d6
        add.l   d5,d7
        dbra    d2,.er
        tst.w   P4_ROWS.l
        bne.s   .eb
; ---- E: spans -------------------------------------------------------------------------------------------------------------
        move.w  P4_EMIT.l,d7
        subq.w  #1,d7
        movea.l P4_SCR.l,a1
        lea     P4_SPAN.l,a4
        lea     P4_LTAB.l,a2
        move.w  $76ee.l,d0
        lea     $76ee.l,a3
        adda.w  d0,a3                   ; the fill routine the original `bsr.w $7af0` would call
        moveq   #15,d6
.p2:    move.w  (a4)+,d4                ; xl
        move.w  (a4)+,d5                ; xr
        bmi.s   .nx2
        move.w  d4,d0
        and.w   d6,d0
        add.w   d0,d0
        add.w   d0,d0
        move.l  (a2,d0.w),d0            ; left mask (both words)
        move.w  d5,d3
        and.w   d6,d3
        add.w   d3,d3
        add.w   d3,d3
        move.l  64(a2,d3.w),d3          ; right-side mask A
        move.l  d0,d2
        not.l   d2
        move.l  d3,d1
        not.l   d1
        lsr.w   #4,d4
        lsr.w   #4,d5
        sub.w   d4,d5                   ; groups - 1
        lsl.w   #3,d4
        lea     (a1,d4.w),a0
        jsr     (a3)
.nx2:   adda.w  #160,a1
        dbra    d7,.p2
        rts
; ---- edge loading -------------------------------------------------------------------------------------------------------------
.ensure:
        tst.w   d3
        bgt.s   .n1
        bsr.s   .loadl
.n1:    tst.w   d4
        bgt.s   .n2
        bsr.s   .loadr
.n2:    rts
.loadl: movea.w -(a3),a2
        move.l  (a2),d6
        lsl.l   #5,d6
        move.w  6(a2),d3
        bgt.s   .la
        moveq   #1,d3
.la:    move.l  8(a2),d1
        movea.l d1,a0
        bpl.s   .lb
        add.l   $c(a2),d6
.lb:    rts
.loadr: movea.w (a4)+,a2
        move.w  6(a2),d4
        bne.s   .ra
        movea.w (a4)+,a2
        move.w  6(a2),d4
.ra:    move.l  (a2),d7
        lsl.l   #5,d7
        move.l  8(a2),d5
        bmi.s   .rb
        add.l   $c(a2),d7
.rb:    tst.w   d4
        bgt.s   .rc
        moveq   #1,d4
.rc:    rts
; ---- fallback: the original code ---------------------------------------------------------------------------------------------
.fb:    movea.l P4_A0.l,a0
        move.w  P4_N.l,d0
        move.w  d0,d6
        add.w   d6,d6
        move.w  d6,-(a7)
        jmp     $755a.l

        org     $8ce00
        dc.l    $ffffffff
        dc.l    $7fff7fff
        dc.l    $3fff3fff
        dc.l    $1fff1fff
        dc.l    $0fff0fff
        dc.l    $07ff07ff
        dc.l    $03ff03ff
        dc.l    $01ff01ff
        dc.l    $00ff00ff
        dc.l    $007f007f
        dc.l    $003f003f
        dc.l    $001f001f
        dc.l    $000f000f
        dc.l    $00070007
        dc.l    $00030003
        dc.l    $00010001
        dc.l    $7fff7fff
        dc.l    $3fff3fff
        dc.l    $1fff1fff
        dc.l    $0fff0fff
        dc.l    $07ff07ff
        dc.l    $03ff03ff
        dc.l    $01ff01ff
        dc.l    $00ff00ff
        dc.l    $007f007f
        dc.l    $003f003f
        dc.l    $001f001f
        dc.l    $000f000f
        dc.l    $00070007
        dc.l    $00030003
        dc.l    $00010001
        dc.l    $00000000
