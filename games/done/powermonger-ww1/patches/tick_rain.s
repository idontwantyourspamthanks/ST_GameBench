; name: tick_rain
; default: yes
; site: $13e24
; orig: 4eb90001b90a
; note: REPLACES tick_wx (same site; tick_wx is `; default: no`: both together fail the site-overlap check).  Port of master's tick_rain (games/done/powermonger/work/notes/rain.md).
;       `jsr $1b90a` = the season / weather step (master `jsr $1abaa`, shift +$d60).  The routine
;       (1) world logic: $50fd... season counter, 16 steps of the dissolve LCG copying 16 bits per step from the next season's picture into the working picture, the season
;           change, the rain clock $50fdc (kind 1 / 2, chosen by the season) / $50fde (ticks left), the wind / rain sounds; and
;       (2) the DRAWING of the rain, $1ba8a..$1ba9a: `$1b5b6` (d0 = $10 groups, d2 = 4, d1 = $c2 rows, d7 = kind) ORs a sparse 32-bit table row into the 4 planes of the back
;           buffer ([$2ed9c] + $3c0 + 32).  The table row of scanline r is the byte `$1b828` - 4 r (wraps; +$40 per call = the drops fall 16 rows per frame).  No RNG: purely visual,
;           the byte $1b828 is the only state.
;       tick_wx skipped all of it on a render-only pass (RON), so the rain showed on one frame per tick only.  Here a render-only pass runs just (2), with $1b828 temporarily set
;       to the phase the drops have reached by now: the last tick's phase + ACC/TK of the next step (ACC = tick_head's real time since the last tick, 0..TK-1 of 1/300 s:
;       off = ACC * 64 / 75 = ACC * 218 >> 8, in whole scanlines (& $fc; long reads need an even index)).  The next tick pass continues exactly where the last render-only frame
;       ended, and the fall is smooth at any frame rate.  The world's $1b828 is saved and restored and nothing else is written ($50fde, the LCG, the season picture): the state is
;       bit-identical to the tick-only build at every tick.  A tick pass is the original $1b90a.  Registers: d0-d3/d7, a0 (the original call clobbers d0-d7/a0/a1 too).
;       WW1 addresses (mapped from master's, shift +$d60): rain kind $4bb42 -> $50fdc, ticks left $4bb44 -> $50fde, draw $1a856 -> $1b5b6, phase byte $1aac8 -> $1b828.
D       equ     $72a80
        org     $13e24
        jsr     $72ac0.l

        org     $72ac0
rain:   tst.w   D+6.l                   ; RON
        bne.s   .r
        jmp     $1b90a.l                ; tick pass: the original
.r:     move.w  $50fdc.l,d7             ; rain kind, 0 = none (as at $1ba8a)
        beq.s   .x
        move.b  $1b828.l,-(a7)          ; world phase (the last tick's call used it; the next tick uses +$40)
        move.w  D+2.l,d0                ; ACC
        mulu.w  #218,d0
        lsr.l   #8,d0                   ; 0..63
        andi.w  #$fc,d0                 ; whole scanlines
        subi.w  #$40,d0                 ; $1b5b6 adds $40 first
        add.b   d0,$1b828.l
        moveq   #$10,d0
        moveq   #4,d2
        move.w  #$c2,d1
        jsr     $1b5b6.l
        move.b  (a7)+,$1b828.l
.x:     rts
