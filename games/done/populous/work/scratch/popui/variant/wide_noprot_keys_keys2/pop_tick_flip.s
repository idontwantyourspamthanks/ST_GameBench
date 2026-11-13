; name: pop_tick_flip
; default: no
; site: $0b940
; orig: 4eb9 00016f16
; note: Fixed-rate world tick, part 4 of 6 (needs pop_tick and pop_tick_cmd; work/notes/timing.md).  `jsr $16f16` is the flip (wait for the VBL flag $16d28, swap $3c510/$3c50c, write
;       $ff8201/03, clear the flag); the keys ($200a6), the keypad scroll, the pointer/click UI ($11a24 $d42c $c420) and the command executor ($1e750 at $bbfa) follow it.
;       Kind S (catch-up, flag SKIP): has drawn nothing: no flip, no keys, no UI - it runs the command executor (commands belong to turns) and goes back to the pass top $b632.
;       No VBL wait is needed either: the flip only paces the loop, and the next pass starts at once.
;       Kind R (render-only, flag RON): the flip, then the click latches are masked for the UI of this pass: a FRESH latch (word 0 = "a click is waiting": $3d566 left, $3c514 right,
;       state machine $16c96) is shown to the UI as 1 ("up") and put back at the end of the pass (pop_tick_cmd, bit 0 / bit 1 of FLAGS = D+20).  So the UI of a render-only pass draws
;       its hover cursor (the `$16954` cell marker of $11a24) and scrolls from the keys, but takes no click: a click is taken, and its command written, by the next turn pass, whose
;       command executor runs it.  Without the mask a button held across a turn boundary would have its command written again by the render-only passes after the turn pass and
;       executed AGAIN at the next turn: one extra raise / lower after every release (the original's held-button repeat is one per pass = one per turn).
;       Any other pass: the displaced `jsr $16f16`, then $b946.
D       equ     $c6000
oSKIP   equ     14
oRON    equ     16
oFLAGS  equ     20
        org     $0b940
        jmp     $c5400.l

        org     $c5400
        tst.w   D+oSKIP.l
        bne.s   .s
        jsr     $16f16.l
        tst.w   D+oRON.l
        bne.s   .r
        jmp     $0b946.l
.r:     move.w  d0,-(a7)
        move.w  sr,-(a7)
        ori.w   #$700,sr                ; the VBL routine writes the latches
        clr.w   D+oFLAGS.l
        tst.w   $3d566.l
        bne.s   .l1
        move.w  #1,$3d566.l             ; fresh left click: hidden from this pass
        bset    #0,D+oFLAGS+1.l
.l1:    tst.w   $3c514.l
        bne.s   .l2
        move.w  #1,$3c514.l             ; fresh right click
        bset    #1,D+oFLAGS+1.l
.l2:    move.w  (a7)+,sr
        move.w  (a7)+,d0
        jmp     $0b946.l
.s:     clr.w   -(a7)
        jsr     $1e750.l
        addq.l  #2,a7
        jmp     $0b632.l
