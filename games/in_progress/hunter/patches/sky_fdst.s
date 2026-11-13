; name: sky_fdst
; default: no
; site: $6790
; orig: 43ee02402e2d0180
; requires: sky_vbl
; note: The Amiga's sky, part 4 of 7: the fade's palette destination (`lea $240(a6),a1 / move.l $180(a5),d7`, 8 B) becomes the shadow palette while the sky is on.
; note: The code is in sky_vbl.s (fixed entry table at SKY); see work/notes/visuals.md.
SKY     equ     $8f100

        org     $6790
        jsr     SKY+12.l                ; sky_fdst
        nop
