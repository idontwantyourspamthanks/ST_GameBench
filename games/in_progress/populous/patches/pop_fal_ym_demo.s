; name: pop_fal_ym_demo
; default: no
; prog: demo
; machine: falcon
; site: $cf98
; orig: 03c8880005888800
; note: Falcon only (`; machine: falcon`: the payload skips the site on every other machine, the ST / STE / Mega STE / TT game bytes stay
; note: the original's).  The title program's sample interrupt (timer A, $cf70..$cfbc: the volume of the three YM channels, one table
; note: entry per sample) starts with `suba.l a0,a0 / movep.l d1,-$7800(a0) / movep.w d2,-$7800(a0)`.  The movep.l writes four bytes to
; note: $ff8800, $ff8802, $ff8804, $ff8806: on an ST the YM decodes $ff8804 / $ff8806 as the same two registers, a Falcon (Hatari: TOS 4.04)
; note: raises a bus error at $ffff8804, TOS kills the program and the loader goes on to the game without the menu.  The blob does the same
; note: three register writes in the same order through $ff8800 / $ff8802 only (two movep.w for the long's two halves, then d2's).  d1 and
; note: a0 end as before; Powermonger's `fal_ym` does the same for its title music.
        org     $cf98
        jsr     $c4000.l
        nop

        org     $c4000
        swap    d1
        movep.w d1,-$7800(a0)           ; bytes 3,2 of the original movep.l: register select, value
        swap    d1
        movep.w d1,-$7800(a0)           ; bytes 1,0: the original wrote them to the mirror $ff8804 / $ff8806
        movep.w d2,-$7800(a0)           ; the original's second instruction
        rts
