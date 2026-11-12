; name: pop_tick_dot
; default: yes
; site: $1672a
; orig: 4eb9 000167b0
; note: Fixed-rate world tick, part 6 of 6 (needs pop_tick and pop_tick_logic; work/notes/timing.md).  `$166f0(cell, colour)` (a minimap dot for a cell: x = $40 + cx - cy, y = (cx + cy) / 2) ends with
;       `jsr $167b0` at $1672a, with the C arguments on the stack: (screen $3c510).l, x.w, y.w, colour.w.  It is called from the world ($db8a, $12fc2) - drawing inside the logic, which a
;       render-only pass skips - and from the paused path of the loop.  This hook appends x / y / colour to a list (D+$100, 560 entries of 6 bytes, write pointer D+48, reset by pop_tick at the
;       top of every turn pass) in a turn pass (flag REC) and plots as before; in a catch-up pass (flag SKIP: no frame follows) it neither plots nor records.  pop_tick_logic replays the
;       list in render-only passes.  `$167b0` writes absolute pixel values (or / and of the mask with the colour bits), so a replay is idempotent.  A call the list is too small for is
;       plotted but not recorded (never happens: 208 people + 209 objects at most).
D       equ     $c6000
oSKIP   equ     14
oREC    equ     18
oWPTR   equ     48
oDOTS   equ     $100
        org     $1672a
        jsr     $c5600.l

        org     $c5600
        tst.w   D+oSKIP.l
        bne.s   .skip
        tst.w   D+oREC.l
        beq.s   .go
        move.l  a1,-(a7)                ; now: 0(a7) a1, 4 return, 8 screen, 12 x, 14 y, 16 colour
        movea.l D+oWPTR.l,a1
        cmpa.l  #D+oDOTS+6*560,a1
        bhs.s   .full
        move.w  12(a7),(a1)+
        move.w  14(a7),(a1)+
        move.w  16(a7),(a1)+
        move.l  a1,D+oWPTR.l
.full:  movea.l (a7)+,a1
.go:    jmp     $167b0.l
.skip:  rts
