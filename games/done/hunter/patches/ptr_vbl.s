; name: ptr_vbl
; default: yes
; site: $c69a
; orig: 4a2d01ce6b00dfbc
; requires: ptr_x ptr_y
; data: $8dbc0 18
; note: Even mouse pointer, part 1 of 3 (work/notes/mouse.md).  The game moves its software pointer ($d8/$da(a5), clamped to 0..$e4/$e6) the moment an
; note: IKBD packet arrives, and it redraws it once per VBL at $a65c.  How many packets fall between two VBLs is then luck: Hatari sends them every 150000
; note: cycles of 8 MHz (53.3 Hz) against the 50 Hz VBL, so one VBL in about 14 sees none (the pointer stops) and the next sees two (it jumps double);
; note: X and Y of one packet can land in different VBLs; and the game halves only NEGATIVE deltas (`ext.w d0 / bpl / asr.w #1,d0` at $b30e and $b32c),
; note: so left and up run at 2/3 of the speed of right and down.  ptr_x/ptr_y now only COLLECT a packet (both axes together, no halving) into PX/PY.
; note: This hook, run once per VBL just before the pointer is drawn (the site is `tst.b $1ce(a5) / bmi.w $a65c`, replaced and re-done here), moves
; note: the pointer by the mean of the last three VBLs' collected motion (a 3-tap box filter, exact: the division remainder is carried, so no motion is
; note: lost or invented and the pointer stops within two VBLs of the mouse).  Position and clamp are the game's own (same variables, same limits).
; note: STATE (18 bytes at $8dbc0, zero at the start): +0 X {pending, h1, h2, remainder}, +8 Y {same}, +16 TX (the X byte of the packet in flight).
PTR     equ     $8dbc0
        org     $c69a
        jsr     $8da70.l                ; replaces `tst.b $1ce(a5) / bmi.w $a65c`; returns to the original `rts` at $c6a2 through the nop
        nop

        org     $8da70
ptr_vbl:
        movem.l d0-d1/a0,-(sp)
        lea     PTR.l,a0
        move.l  (a0),d0                 ; nothing pending and nothing in flight on either axis: the common case
        or.l    4(a0),d0
        or.l    8(a0),d0
        or.l    12(a0),d0
        beq.s   .done
        bsr.s   .axis                   ; X: d0 = this VBL's step
        beq.s   .y
        add.w   $d8(a5),d0
        bpl.s   .x1
        clr.w   d0
.x1:    cmp.w   $e4(a5),d0
        blt.s   .x2
        move.w  $e4(a5),d0
.x2:    move.w  d0,$d8(a5)
.y:     addq.l  #8,a0
        bsr.s   .axis
        beq.s   .done
        add.w   $da(a5),d0
        bpl.s   .y1
        clr.w   d0
.y1:    cmp.w   $e6(a5),d0
        blt.s   .y2
        move.w  $e6(a5),d0
.y2:    move.w  d0,$da(a5)
.done:  movem.l (sp)+,d0-d1/a0
        tst.b   $1ce(a5)                ; the original two instructions
        bpl.s   .r
        jsr     $a65c.l                 ; (`bmi.w $a65c` was a tail jump; here it returns through the nop to the `rts` at $c6a2)
.r:     rts

; one axis, a0 -> {pending.w, h1.w, h2.w, remainder.w}: d0 = the step (Z flag set when 0)
.axis:  move.w  (a0),d0                 ; the packets collected since the last VBL ...
        sub.w   d0,(a0)                 ; ... taken (one that lands between these two instructions stays for the next VBL)
        move.w  d0,d1
        add.w   2(a0),d1                ; + the VBL before
        add.w   4(a0),d1                ; + the one before that
        move.w  2(a0),4(a0)
        move.w  d0,2(a0)
        add.w   6(a0),d1                ; + the carried remainder
        ext.l   d1
        divs    #3,d1                   ; mean of three, truncated toward 0; the remainder (sign of the sum) is kept
        move.w  d1,d0
        swap    d1
        move.w  d1,6(a0)
        tst.w   d0
        rts
