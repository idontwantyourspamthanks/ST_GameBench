; name: p4_roll_07
; default: yes
; site: $16164
; note: item #8 (render.md s8), site 8/24 of the vertex transform (ring strip loops $15a96-$17058, all 24 have the
; note: identical 24-byte shape `move.w d3,d6 / move.w d4,d7 / muls $17216,d3 / muls $17214,d7 / sub.l d7,d3 /
; note: muls $17214,d6 / muls $17216,d4 / add.l d6,d4`). With the roll word $17214 == 0 (set by $144ca; the heading
; note: terms use $17210/$17212) the two `muls ...,d7/d6` products are 0, so d3 = d3*$17216, d4 = d4*$17216 exactly.
; note: In place: tst.w $17214.l / beq.s fast / jmp slow (original sequence, copy in the blob) / fast: 2 muls.
; note: d6/d7 are only scratch here: next reads are after `clr.w d6` (outcode) or reloads at the loop head; d7 is
; note: loaded fresh before every use in $16cf6. The pc-relative displacements were re-derived per site.
        org     $16164
        tst.w   $17214.l
        beq.s   .fast
        jmp     $b3e34.l
        nop
.fast:  muls.w  $17216(pc),d3
        muls.w  $17216(pc),d4

        org     $b3e34
        move.w  d3,d6
        move.w  d4,d7
        muls.w  $17216.l,d3
        muls.w  $17214.l,d7
        sub.l   d7,d3
        muls.w  $17214.l,d6
        muls.w  $17216.l,d4
        add.l   d6,d4
        jmp     $1617c.l
