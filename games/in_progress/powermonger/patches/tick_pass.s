; name: tick_pass
; default: yes
; site: $13074
; orig: 0479000100057ff0
; note: P2 (needs tick_head). The game's own render/skip branch `subi.w #1,$57ff0.l ; bne.b $130b0`
;       (the follow-up `bne.b` stays). `$57ff0` counts down from `$57fee` (the speed track, 1 = render
;       every pass); a non-zero result skips VBL wait, window copy, landscape and the flip for the pass.
;       Same here, plus: on an S pass (SKIP set by tick_head: another tick is owed) the render is also
;       skipped, and `$57ff0` is parked at 1 so the next pass counts down to 0 again.
;       Returns the flags of the original subi (Z = render).
D       equ     $b8a00
        org     $13074
        jsr     $b8900.l
        nop

        org     $b8900
pass:   subi.w  #1,$57ff0.l
        beq.s   .z
        rts                             ; NZ: the game's own skip
.z:     tst.w   D+4.l                   ; SKIP
        beq.s   .ok                     ; Z: render
        clr.w   D+4.l
        move.w  #1,$57ff0.l             ; NZ: skip, count down to 0 again next pass
.ok:    rts
