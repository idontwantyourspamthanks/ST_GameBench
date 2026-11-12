; name: pop2_tick_render
; default: yes
; site: $12554
; orig: 0c79000800039766
; note: Fixed-rate world tick, part 2 of 8 (needs pop2_tick; work/notes/timing.md).  Catch-up passes (kind S, flag SKIP) draw nothing: `cmpi.w #8,$39766.l` at $12554 is the
; note: first instruction after `jsr $22f14` (the pass top) of the whole render stage - background copy $1e7b2, the marks $14158/$136ba/$13574/$16836, the terrain and
; note: sprites $1df44 (or the zoomed views $1e75e/$1e300), the minimap and HUD ($1259e-$12740) - and `$12740 jsr $1334a` (pointer shape).  An S pass jumps straight to
; note: $12746 (the pause test in front of the logic block).  Measured in busy1 (work/notes/timing.md section 1): none of these stages writes world state, only the screen
; note: buffers, the VBL counters, a scratch word in the sprite code ($20fe9) and the player visibility flags `$4b(player)` (bset by the sprite code, read by the UI).
; note: Any other pass runs the displaced instruction (flags for the `bne.b $1258c` at $1255c) and continues at $1255c.
D       equ     PB+$2800
oSKIP   equ     14
        org     $12554
        jmp     PB+$2200.l
        nop

        org     PB+$2200
        tst.w   D+oSKIP.l
        bne.s   .s
        cmpi.w  #8,$39766.l
        jmp     $1255c.l
.s:     jmp     $12746.l
