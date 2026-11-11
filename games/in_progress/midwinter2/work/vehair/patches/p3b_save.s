; name: p3b_save
; default: yes
; site: $33be6
; orig: 21f866e666ee
; note: P3 partial-B ("patch 7"). sub_033bde saves the pre-move position and route
;       ($66ee/$66f2/$66fe) before the step; the collision/arrival probes
;       ($1ba60, $1bc50, $34056, $340d4, ...) revert to them. With 5 sub-ticks per 5 Hz
;       step they must hold the position at the start of the GROUP: the save runs only
;       on the first foot pass (HOLD = 0, p3b_head) and on every full (option A) pass.
;       Original: move.l $66e6,$66ee; move.l $66ea,$66f2; move.w $764c,$66fe.
;       The site is the first move. HOLD = 0: it is replayed and the other two follow
;       in the original code. HOLD = 1: all three are skipped (jmp $33bf8).
        org     $33be6
        jsr     $b4126.l

        org     $b4126
        tst.w   $b42ea.l                ; HOLD
        bne.s   .hold
        move.l  $66e6.w,$66ee.w         ; the replaced instruction
        rts
.hold:  addq.l  #4,a7
        jmp     $33bf8.l
