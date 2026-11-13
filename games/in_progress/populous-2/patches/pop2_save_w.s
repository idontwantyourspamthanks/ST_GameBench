; name: pop2_save_w
; default: no
; site: $2cbe4
; orig: 4eb900036efc
; note: Part 2 of 3 of the in-game SAVE/LOAD fix (see pop2_save): the write call of the game's save routine $2cba6 (d0 = 1, a0 = name, a1 = $39630, d1 = $dd72) goes to the
; note: GEMDOS blob instead of PP's disk-layer stub.  Ships with pop2_save and pop2_save_d.
SAVE    equ     PB+$300

        org     $2cbe4
        jsr     SAVE.l
