; name: pop2_tick_dot_a
; default: yes
; site: $24296
; orig: 4eb900020058
; note: Fixed-rate world tick, part 5 of 8 (needs pop2_tick and pop2_tick_logic; work/notes/timing.md).  The people loop plots one minimap pixel per person into the back
; note: buffer: $24290 `movea.l $392e0.l,a0` / $24296 `jsr $20058.l` with d0 = x, d1 = y, d2 = colour (from $309d8, blinking with the turn parity $3979c).  That is DRAWING
; note: inside the world logic, which a render-only pass skips.  This hook (also used by pop2_tick_dot_b at $27942, the same call in the effects loop) appends d0/d1/d2
; note: to a list (D+$100, 900 entries of 6 B, write pointer D+48, reset by pop2_tick at the top of every turn pass) and plots as before; in a catch-up pass
; note: (SKIP: no frame follows) it neither plots nor records.  pop2_tick_logic replays the list in render-only passes.  Any call the list is too small for is plotted
; note: but not recorded (never happens: 400 people + 240 effect objects at most).
D       equ     PB+$2800
oSKIP   equ     14
oWPTR   equ     48
oDOTS   equ     $100
        org     $24296
        jsr     PB+$2400.l

        org     PB+$2400
        tst.w   D+oSKIP.l
        bne.s   .out
        move.l  a1,-(a7)
        movea.l D+oWPTR.l,a1
        cmpa.l  #D+oDOTS+6*900,a1
        bhs.s   .full
        move.w  d0,(a1)+
        move.w  d1,(a1)+
        move.w  d2,(a1)+
        move.l  a1,D+oWPTR.l
.full:  movea.l (a7)+,a1
        jmp     $20058.l
.out:   rts
