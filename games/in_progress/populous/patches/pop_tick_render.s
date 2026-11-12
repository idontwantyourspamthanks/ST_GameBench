; name: pop_tick_render
; default: yes
; site: $0b6f4
; orig: 4eb9 00014a28
; note: Fixed-rate world tick, part 2 of 6 (needs pop_tick; work/notes/timing.md).  `jsr $14a28` (copy of the clean background into the back buffer) starts the render stage of
;       a pass: $b6f4-$b7e6 = background copy, `$da90` (manna bar), terrain + people `$143a2`, the sprite list, the view marker `$16954`.  A catch-up pass (kind S, flag SKIP) draws
;       nothing (no frame follows): it jumps to $b800 (the world).  Measured (work/notes/timing.md section 2): the render stage writes no world state - only the screen buffers,
;       the sprite list ($3b04a ...), the scratch words $37ef0 $3d58c $37eb6 and the pointer shape $2169a.  Any other pass runs the displaced `jsr $14a28` and goes on at $b6fa.
SKIP    equ     $c6000+14
        org     $0b6f4
        jmp     $c5200.l

        org     $c5200
        tst.w   SKIP.l
        bne.s   .s
        jsr     $14a28.l
        jmp     $0b6fa.l
.s:     jmp     $0b800.l
