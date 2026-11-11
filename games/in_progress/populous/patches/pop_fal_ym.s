; name: pop_fal_ym
; default: no
; prog: populous
; machine: falcon
; site: $171a8
; orig: 03c8880005888800
; note: Falcon only (see pop_fal_ym_demo.s, same code in the game).  The game's effect-sample interrupt (timer A, $1717e..$171ce, installed by
; note: $17000) writes the three YM volumes with `suba.l a0,a0 / movep.l d1,-$7800(a0) / movep.w d2,-$7800(a0)` at $171a6: the movep.l writes
; note: $ff8800 / $ff8802 / $ff8804 / $ff8806 and a Falcon bus-errors on the mirror pair, so the first sound effect of a game would kill it.
; note: The blob writes the same three register pairs in the same order through $ff8800 / $ff8802 only.
        org     $171a8
        jsr     $c4040.l
        nop

        org     $c4040
        swap    d1
        movep.w d1,-$7800(a0)
        swap    d1
        movep.w d1,-$7800(a0)
        movep.w d2,-$7800(a0)
        rts
