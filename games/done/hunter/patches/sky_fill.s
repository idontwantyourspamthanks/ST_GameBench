; name: sky_fill
; default: yes
; site: $c84a
; orig: 286d0144d9ed01a2
; requires: sky_vbl
; note: The Amiga's sky, part 2 of 7: the 3D window fill $c84a (`movea.l $144(a5),a4 / adda.l $1a2(a5),a4`, 8 B). With the sky on it fills 140 rows with solid colour 15 instead of the $aaaa/$5555 dither below the horizon, and records the horizon row of the page.
; note: The code is in sky_vbl.s (fixed entry table at SKY); see work/notes/visuals.md.
SKY     equ     $8f100

        org     $c84a
        jmp     SKY+4.l                 ; sky_fill: returns to $c852 (original fill) or $c8d0 (solid fill)
        nop
