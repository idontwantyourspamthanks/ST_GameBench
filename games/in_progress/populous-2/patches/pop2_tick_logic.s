; name: pop2_tick_logic
; default: no
; site: $12746
; orig: 4a7900039796663e
; note: Fixed-rate world tick, part 3 of 8 (needs pop2_tick; work/notes/timing.md).  The game's own pause test in front of the world logic block: `tst.w $39796.l` /
; note: `bne.b $1278c` (paused: skip to the flip).  A render-only pass (kind R, flag RON: ahead of real time) takes the same branch, so none of the logic calls
; note: ($2309a people, $25652, $26644 effects, $27faa, $1fcce, $29c7e, $2a0b2) runs and the world stays exactly where the last turn left it.  One thing in that block
; note: is drawing, not logic: the people loop ($24244-$24296) and the effects loop ($2793c-$27942) plot one pixel per object on the minimap (`jsr $20058`, a0 = back buffer
; note: [$392e0]).  pop2_tick_dot_a/b record those calls in a turn pass; an R pass replays the list here, so the minimap shows the same dots in every frame of a turn.
; note: Any other pass: the original test (paused -> $1278c, else the logic at $1274e).
D       equ     PB+$2800
oRON    equ     16
oWPTR   equ     48
oDOTS   equ     $100
        org     $12746
        jmp     PB+$2240.l
        nop

        org     PB+$2240
        tst.w   D+oRON.l
        bne.s   .r
        tst.w   $39796.l
        bne.s   .p
        jmp     $1274e.l
.p:     jmp     $1278c.l
.r:     movem.l d0-d3/a0/a2,-(a7)
        lea     D+oDOTS.l,a2
        move.l  D+oWPTR.l,d3
        movea.l $392e0.l,a0
.l:     cmpa.l  d3,a2
        bhs.s   .done
        move.w  (a2)+,d0
        move.w  (a2)+,d1
        move.w  (a2)+,d2
        jsr     $20058.l
        bra.s   .l
.done:  movem.l (a7)+,d0-d3/a0/a2
        jmp     $1278c.l
