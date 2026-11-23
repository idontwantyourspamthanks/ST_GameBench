; name: tick_pass
; default: yes
; site: $13de8
; orig: 047900010005a854
; note: (needs tick_head) The game's own render/skip branch `subi.w #1,$5a854.l ; bne.b $13e24` (the follow-up `bne.b` stays; master $13074 / $57ff0).
;       `$5a854` counts down from `$5a852` (the speed track, 1 = render every pass); a non-zero result skips VBL wait, window copy, landscape and the flip
;       for the pass.  Same here, plus: on an S pass (SKIP set by tick_head: another tick is owed) the render is also skipped, and `$5a854` is parked at 1
;       so the next pass counts down to 0 again.  Returns the flags of the original subi (Z = render).
D       equ     $72a80
        org     $13de8
        jsr     $72a00.l
        nop

        org     $72a00
pass:   subi.w  #1,$5a854.l
        beq.s   .z
        rts                             ; NZ: the game's own skip
.z:     tst.w   D+4.l                   ; SKIP
        beq.s   .ok                     ; Z: render
        clr.w   D+4.l
        move.w  #1,$5a854.l             ; NZ: skip, count down to 0 again next pass
.ok:    rts
