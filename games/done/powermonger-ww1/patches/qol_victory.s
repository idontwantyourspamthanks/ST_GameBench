; name: qol_victory
; default: yes
; site: $1787e
; orig: 41f9000178ba
; note: replace the balance gauge (x=0..63, y=134..153) with a brass/green "VICTORY" button
;       when in a full winning position ($5a830 == 4).  Companion qol_victory2 makes it clickable
;       to retire straight to the victory screen.  When $5a830 < 4, original gauge is drawn untouched.
;       Procedural 64x20 4-bitplane renderer + 5x7 font for "VICTORY" fits in ~250 B of LOW RAM.

        org     $1787e
        jmp     $732c0.l

        org     $732c0
hook:   cmpi.w  #4,d0
        beq.s   .win
        lea     $178ba.l,a0
        jmp     $17884.l

.win:   movea.l $e4ca.l,a1
        adda.w  #$53c0,a1               ; a1 = HUD backdrop at (0, 134)
        ; draw frame rectangles from RECTS table (x0, y0, x1, y1, col), terminated by $ff
        lea     $75760.l,a0
.rlp:   moveq   #0,d0
        move.b  (a0)+,d0
        cmp.b   #$ff,d0
        beq.s   .text
        moveq   #0,d1
        move.b  (a0)+,d1
        moveq   #0,d2
        move.b  (a0)+,d2
        moveq   #0,d3
        move.b  (a0)+,d3
        moveq   #0,d4
        move.b  (a0)+,d4
        bsr.s   rect
        bra.s   .rlp

.text:  ; draw "VICTORY" drop shadow at (12, 7) in col 0, then shaded gold/cream at (11, 6)
        moveq   #12,d5
        moveq   #7,d6
        moveq   #0,d7                   ; d7 = 0 -> shadow (col 0)
        bsr.s   draw_word
        moveq   #11,d5
        moveq   #6,d6
        moveq   #1,d7                   ; d7 = 1 -> shaded gold/cream (5 / 10 / 9)
        bsr.s   draw_word
        jmp     $178b4.l                ; movem.l (a7)+,d1-d7/a0-a2 ; rts

; rect: fill [d0..d2] x [d1..d3] with colour d4 into a1 (stride 160)
rect:   movem.l d0-d5,-(a7)
.ry:    move.w  d0,d5                   ; x = x0
.rx:    bsr.s   putpx                   ; plots (d5, d1) in colour d4
        addq.w  #1,d5
        cmp.w   d2,d5
        ble.s   .rx
        addq.w  #1,d1
        cmp.w   d3,d1
        ble.s   .ry
        movem.l (a7)+,d0-d5
        rts

; draw_word: draw 7 glyphs from FONT at (d5, d6); d7=0 shadow, d7=1 shaded
draw_word:
        lea     $74f00.l,a0
        moveq   #6,d2                   ; 7 letters (V I C T O R Y)
.ch:    moveq   #0,d3                   ; row 0..6
.row:   move.b  (a0)+,d0                ; 5-bit glyph row (bits 4..0 = cols 0..4)
        move.w  d6,d1
        add.w   d3,d1                   ; y = y0 + row
        moveq   #0,d4                   ; col = 0 (shadow)
        tst.w   d7
        beq.s   .colok
        moveq   #5,d4                   ; r <= 1 -> cream (5)
        cmp.w   #1,d3
        ble.s   .colok
        moveq   #10,d4                  ; r <= 4 -> bright gold (10)
        cmp.w   #4,d3
        ble.s   .colok
        moveq   #9,d4                   ; r >= 5 -> gold (9)
.colok: movem.l d2-d3,-(a7)
        moveq   #4,d2                   ; bit index 4..0
        move.w  d5,d3                   ; x = cur_x
.bit:   btst    d2,d0
        beq.s   .nb
        exg     d3,d5
        bsr.s   putpx                   ; plots (d5, d1) in colour d4
        exg     d3,d5
.nb:    addq.w  #1,d3
        dbra    d2,.bit
        movem.l (a7)+,d2-d3
        addq.w  #1,d3
        cmp.w   #7,d3
        blt.s   .row
        addq.w  #6,d5                   ; next char x += 6
        dbra    d2,.ch
        rts

; putpx: plot pixel (x=d5, y=d1, col=d4) into 4-bitplane buffer a1 (stride 160). Preserves all regs.
putpx:  movem.l d0-d3/a2,-(a7)
        move.w  d1,d0
        mulu.w  #160,d0
        move.w  d5,d2
        lsr.w   #4,d2
        lsl.w   #3,d2
        add.w   d2,d0
        lea     (a1,d0.w),a2            ; a2 -> 4-plane word group
        moveq   #15,d2
        move.w  d5,d3
        and.w   #15,d3
        sub.w   d3,d2                   ; d2 = bit index (15 - (x & 15))
        moveq   #0,d3
        bset    d2,d3                   ; d3 = set mask
        move.w  d3,d1
        not.w   d1                      ; d1 = clear mask
        moveq   #0,d0                   ; plane 0..3
.pl:    btst    d0,d4
        beq.s   .clr
        or.w    d3,(a2)+
        bra.s   .nx
.clr:   and.w   d1,(a2)+
.nx:    addq.w  #1,d0
        cmp.w   #4,d0
        blt.s   .pl
        movem.l (a7)+,d0-d3/a2
        rts

        org     $75760
RECTS:  ; x0, y0, x1, y1, col
        dc.b    0,0,63,19,0             ; black outer border
        dc.b    0,1,62,18,9             ; brass frame body
        dc.b    0,1,61,1,10             ; top highlight
        dc.b    1,1,1,18,10             ; left highlight
        dc.b    0,1,1,1,5               ; top-left specular
        dc.b    0,17,62,17,6            ; bottom dark bronze
        dc.b    61,2,61,17,6            ; right dark bronze
        dc.b    0,18,62,18,1            ; bottom shadow
        dc.b    62,2,62,18,1            ; right shadow
        dc.b    3,3,59,16,13            ; dark military green interior
        dc.b    3,3,59,3,1              ; inner top bevel
        dc.b    3,3,3,16,1              ; inner left bevel
        dc.b    3,16,59,16,12           ; inner bottom highlight
        dc.b    59,4,59,16,12           ; inner right highlight
        dc.b    6,6,6,6,0               ; rivet shadows
        dc.b    58,6,58,6,0
        dc.b    6,15,6,15,0
        dc.b    58,15,58,15,0
        dc.b    5,5,5,5,10              ; 4 brass rivets
        dc.b    57,5,57,5,10
        dc.b    5,14,5,14,10
        dc.b    57,14,57,14,10
        dc.b    $ff

        org     $74f00
FONT:   ; 5x7 bitmaps (bits 4..0) for V, I, C, T, O, R, Y (49 bytes)
        dc.b    $11,$11,$11,$11,$11,$0a,$04     ; V
        dc.b    $1f,$04,$04,$04,$04,$04,$1f     ; I
        dc.b    $0e,$11,$10,$10,$10,$11,$0e     ; C
        dc.b    $1f,$04,$04,$04,$04,$04,$04     ; T
        dc.b    $0e,$11,$11,$11,$11,$11,$0e     ; O
        dc.b    $1e,$11,$11,$1e,$14,$12,$11     ; R
        dc.b    $11,$11,$0a,$04,$04,$04,$04     ; Y
        even
