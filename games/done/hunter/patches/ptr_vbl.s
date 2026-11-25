; name: ptr_vbl
; default: yes
; site: $c69a
; orig: 4a2d01ce6b00dfbc
; requires: ptr_x ptr_y ptr_thr
; data: $8dbc0 18
; note: Responsive, even mouse pointer + redundant-redraw skip, part 1 of 4.
; note: ptr_thr sets IKBD mouse threshold (1,1); ptr_x/ptr_y collect X and Y atomically without halving negative deltas.
; note: This VBL hook commits (PX, PY) 1:1 right before the pointer redraw ($a65c) and skips the 5,180-cycle erase+redraw
; note: when in the 3D window (y < 130) if the pointer is already drawn, hasn't moved, and the shown screen page hasn't flipped.
; note: STATE (18 bytes at $8dbc0, zero at start): +0 PX.w, +2 last_xy.l, +6 last_scr.w, +8 PY.w, +16 TX.w.
PTR     equ     $8dbc0
        org     $c69a
        jsr     $8da70.l                ; replaces `tst.b $1ce(a5) / bmi.w $a65c`; returns to the original `rts` at $c6a2 through the nop
        nop

        org     $8da70
ptr_vbl:
        movem.l d0/a0,-(sp)
        lea     PTR.l,a0
        move.w  (a0),d0                 ; X: packets collected since the last VBL
        beq.s   .y
        sub.w   d0,(a0)                 ; atomic take (a packet landing here stays for the next VBL)
        add.w   $d8(a5),d0
        bpl.s   .x1
        clr.w   d0
.x1:    cmp.w   $e4(a5),d0
        blt.s   .x2
        move.w  $e4(a5),d0
.x2:    move.w  d0,$d8(a5)
.y:     move.w  8(a0),d0                ; Y: packets collected since the last VBL
        beq.s   .chk
        sub.w   d0,8(a0)
        add.w   $da(a5),d0
        bpl.s   .y1
        clr.w   d0
.y1:    cmp.w   $e6(a5),d0
        blt.s   .y2
        move.w  $e6(a5),d0
.y2:    move.w  d0,$da(a5)
.chk:   tst.b   $1ce(a5)                ; pointer enabled (bit 7)?
        bpl.s   .r
        btst    #0,$1ce(a5)             ; already drawn on screen (bit 0)?
        beq.s   .draw
        btst    #7,$93(a5)              ; in 3D view?
        beq.s   .draw
        cmpi.w  #130,$da(a5)            ; inside 3D window (above 140-row HUD panel)?
        bge.s   .draw
        move.b  $ffff8201.w,d0
        lsl.w   #8,d0
        move.b  $ffff8203.w,d0
        cmp.w   6(a0),d0                ; shown screen page unchanged?
        bne.s   .draw
        move.l  $d8(a5),d0
        cmp.l   2(a0),d0                ; cursor (x, y) unchanged?
        beq.s   .r                      ; skip redundant 5,180-cycle erase+redraw!
.draw:  move.b  $ffff8201.w,d0
        lsl.w   #8,d0
        move.b  $ffff8203.w,d0
        move.w  d0,6(a0)
        move.l  $d8(a5),2(a0)
        movem.l (sp)+,d0/a0
        jsr     $a65c.l                 ; (`bmi.w $a65c` was a tail jump; returns through nop to `rts` at $c6a2)
        rts
.r:     movem.l (sp)+,d0/a0
        rts
