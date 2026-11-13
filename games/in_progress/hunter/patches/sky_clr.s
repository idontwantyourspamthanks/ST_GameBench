; name: sky_clr
; default: no
; site: $c8c2
; orig: 382d00385344
; requires: sky_vbl
; note: The Amiga's sky, part 3 of 7: the page clear $c8bc/$c8c0 (`move.w $38(a5),d4 / subq.w #1,d4`, 6 B) also takes the sky away from the page it clears (message and dialogue screens inside the 3D mode).
; note: The code is in sky_vbl.s (fixed entry table at SKY); see work/notes/visuals.md.
SKY     equ     $8f100

        org     $c8c2
        jsr     SKY+8.l                ; sky_clr
