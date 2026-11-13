; name: sky2_aciax
; default: yes
; site: $b004
; orig: 4cdf1fff4e73
; requires: sky_vbl
; data: $8ecea 150
; note: The Amiga's sky, part 6 of 7: the exit of the IKBD/ACIA handler (`movem.l (a7)+,d0-d7/a0-a4 / rte`, 6 B) pops the
; note: registers in two halves, so the Timer B colour change waits for at most one 72-cycle instruction instead of 116.
; note: The `data:` line reserves the sky's state block SKYV (window sky2_, $8ECEA-$8EFFF; layout in sky_vbl.s).
; note: Same registers, same stack; the entry half is the $118 wrapper in sky_vbl.s (see work/notes/visuals.md, jitter).
SKY     equ     $8f100

        org     $b004
        jmp     SKY+20.l                ; sky_aciax
