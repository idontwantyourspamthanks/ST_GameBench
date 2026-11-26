; name: tick_render
; default: no
; site: $3159c
; orig: 427870204eb85086
; note: P3 fixed-tick, part 3. This is the 3D render path of the frame loop
;       (after the $6298 render gate). When tick_head has flagged SKIP, the
;       logic is behind real time, so render, flip and the post-render calls
;       are skipped and the loop jumps straight back to its head for another
;       tick. Otherwise it behaves exactly as the original
;       `clr.w $7020.w ; jsr $5086.w`.
SKIP    equ     $b3404
        org     $3159c
        jsr     $b4110.l
        nop

        org     $b4110
        clr.w   $7020.w                 ; displaced (also on skip: game waits rely on it)
        tst.w   SKIP
        bne.s   .skip
        jmp     $5086.w                 ; displaced jsr, as a tail call
.skip:  addq.l  #4,a7                   ; drop our return address
        jmp     $31486.l                ; next logic tick, no render
