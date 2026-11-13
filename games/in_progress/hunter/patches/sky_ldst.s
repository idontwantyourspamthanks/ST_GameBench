; name: sky_ldst
; default: no
; site: $61fa
; orig: 43ee0240700f
; requires: sky_vbl
; note: The Amiga's sky, part 5 of 7: the direct palette loader's destination (`lea $240(a6),a1 / moveq #$f,d0`, 6 B) becomes the shadow palette while the sky is on.
; note: The code is in sky_vbl.s (fixed entry table at SKY); see work/notes/visuals.md.
SKY     equ     $8f100

        org     $61fa
        jsr     SKY+16.l                ; sky_ldst
