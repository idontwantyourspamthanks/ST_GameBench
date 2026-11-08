; name: p4_fill_save_a
; default: no
; site: $1b1bc
; note: item #9 (render.md s8) fill trim, part 1/2 (with p4_fill_save_b; together). Fill setup sub_01b1bc saves/restores a0-a6
; note: around every polygon (64+68 cy). Registers it and its callees ($1b0e4, the solid variants $1aa44-$1b0e0,
; note: the pick test $19e76 which saves its own) modify: a0 a2 a3 a4 a5 a6 (a1 never appears in $1aa44-$1b27e) and all of
; note: d0-d7. Reached only by `bne.w $1b1bc` tail jumps from the two polygon drivers ($19e02, $19e68), whose callers
; note: ($19ce2 loop, $1d71c loop) saved d0-d7/a0-a6 at entry and use only a0-a3,a6 (and a1, untouched here) in the loop
; note: ($1d5a6 saves everything itself). So a4/a5 (and d regs) are dead on return: save only a0,a2,a3,a6.
        org     $1b1bc
        movem.l a0/a2-a3/a6,-(a7)
