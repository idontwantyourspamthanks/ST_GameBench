; name: tick_rain
; default: yes
; site: $130b0
; orig: 4eb90001abaa
; note: P2 variant of tick_wx (REPLACES it: same site, `; default: no`; select one of the two). `jsr $1abaa` = season/weather step. The routine
;       (work/notes/rain.md) does
;       (1) world logic: `$57fec`++, 16 steps of the dissolve LCG `$57ff6` (x $24a1 + $24df, & $1fff) copying 16 bits per step from the next
;           season's picture into the working picture ($ff9e+$e80), the season change (RNG `$12c9a`, `$57fd0`), the rain clock `$4bb42`
;           (kind 1/2, chosen by the season) / `$4bb44` (ticks left), the wind/rain sounds; and
;       (2) the DRAWING of the rain, `$1ad2a..$1ad3a`: `$1a856` (d0=$10 groups, d2=4, d1=$c2 rows, d7=kind) ORs a sparse 32-bit table row
;           into the 4 planes of the back buffer (`$2df7c`+$3c0+32). The table row of scanline r is `$1aac8` - 4 r (byte, wraps; +$40
;           per call = the drops fall 16 rows per frame). No RNG: purely visual, the byte `$1aac8` is the only state.
;       tick_wx skipped all of it on a render-only pass (RON), so the rain showed on one frame per tick only. Here a render-only pass runs
;       just (2), with `$1aac8` temporarily set to the phase the drops have reached by now: the last tick's phase + ACC/TK of the next step
;       (ACC = tick_head's real time since the last tick, 0..TK-1 of 1/300 s: off = ACC * 64 / 75 = ACC*218 >> 8, in whole scanlines
;       (& $fc; long reads need an even index). The next tick pass then continues exactly where the last render-only frame ended, and the
;       fall is smooth at any frame rate. The world's `$1aac8` is saved and restored, and nothing else is written ($4bb44, `$57fec`,
;       `$57ff6`, the RNG, the season picture): the state is bit-identical to the tick-only build at every tick. A tick pass is the
;       original `$1abaa`. Registers: d0-d3/d7, a0 (the original call clobbers d0-d7/a0/a1 too).
D       equ     $b8a00
        org     $130b0
        jsr     $b8980.l

        org     $b8980
rain:   tst.w   D+6.l                   ; RON
        bne.s   .r
        jmp     $1abaa.l                ; tick pass: the original
.r:     move.w  $4bb42.l,d7             ; rain kind, 0 = none (as at $1ad2a)
        beq.s   .x
        move.b  $1aac8.l,-(a7)          ; world phase (the last tick's call used it; the next tick uses +$40)
        move.w  D+2.l,d0                ; ACC
        mulu.w  #218,d0
        lsr.l   #8,d0                   ; 0..63
        andi.w  #$fc,d0                 ; whole scanlines
        subi.w  #$40,d0                 ; $1a856 adds $40 first
        add.b   d0,$1aac8.l
        moveq   #$10,d0
        moveq   #4,d2
        move.w  #$c2,d1
        jsr     $1a856.l
        move.b  (a7)+,$1aac8.l
.x:     rts
