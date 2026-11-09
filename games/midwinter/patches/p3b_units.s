; name: p3b_units
; default: yes
; site: $12a5e
; orig: 4eb90000c4f24eb90000ca7e
; note: P3 partial B (needs p3b_head; work/notes/timing.md section 4). The HUD redraw sub_0129d2
;       (`jsr $129d2` at $14e1a) is not only HUD: its last two calls, `jsr $c4f2` and `jsr $ca7e`
;       (12 bytes), are game logic. $c4f2 steps the table of up to 41 map units ($2d47e, stride $10:
;       path pointer, cell x/z, direction) one step along their paths with random turns ($c9c6 draws
;       the PRNG $d598; spawning from $2bb0a..) and $ca7e turns a unit that enters the view window
;       into the object in slot $1cdaa. Measured: 584 $c9da PRNG draws and 29 $d584 draws in 250 VBL
;       on `1mb_ski_walk` (about 15 per pass). It therefore belongs to the 5 Hz tick: on a view sub-step
;       pass (NOLOGIC = 1) it is skipped; on every other pass it runs as the original.
;       The skip tails of tick_head / p3b_head (render skipped) call the same two routines.
D       equ     $b3700
        org     $12a5e
        jsr     $b36c0.l
        nop
        nop
        nop

        org     $b36c0
units:  tst.w   D+32.l                  ; NOLOGIC
        bne.s   .no
        jsr     $c4f2.l
        jsr     $ca7e.l
.no:    rts
