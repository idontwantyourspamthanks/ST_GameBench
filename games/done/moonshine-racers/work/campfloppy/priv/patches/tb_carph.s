; name: tb_carph
; default: yes
; site: $ed90
; orig: 302a0006d06a0008
; requires: tb_car
; doc: Companion of tb_car: records which wheel-animation list the game XORs into which player bitmap (the player bank alternates between states).
; note: Site $ed90 = the first two instructions of the bitmap-XOR routine `$ed90` (`move.w $6(a2),d0 / add.w $8(a2),d0` = bitmap index; entered only by falling through from `$ed74`, no references).  The blob replays them, toggles one bit of
; note: PH[bitmap index] ($BF440, tb_car's data) = bit ((list index - bitmap index) & 7) (lists are entries bitmap + 5 / + 10 of the same table: `$2e(a2) + $8(a2)`), and continues at `$ed98`.  Registers: only d1 and a1 are touched and both are loaded again
; note: before the routine uses them (`$ed9a`, `$edb4`).
PH      equ     $BF440

        org     $ed90
        jmp     $BFC00.l
        nop

        org     $BFC00
hook:   move.w  6(a2),d0
        add.w   8(a2),d0
        cmpi.w  #63,d0
        bhi.s   .x
        move.w  $2e(a2),d1
        add.w   8(a2),d1
        sub.w   d0,d1
        lea     PH.l,a1
        adda.w  d0,a1
        bchg    d1,(a1)
.x:     jmp     $ed98.l
