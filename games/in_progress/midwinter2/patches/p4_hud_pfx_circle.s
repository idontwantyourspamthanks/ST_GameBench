; name: p4_hud_pfx_circle
; default: yes
; site: $1d188
; orig: 4eb850204e75
; phase: deferred
; note: HUD "clean-prefix" set, part 5/5 (work/notes/explosions.md).  The disc filler $1cf64 (explosion / effect
;       circles, reached from $1ce90) ends in `jsr $5020.w` / `rts` at $1d188: it enters the span-fill dispatcher
;       $38cd0 with d6.w = a byte OFFSET (row*160 at the end of its edge loop, e.g. $42e0), not the polygon's first row,
;       so p4_hud_pfx_ymin never lowered YMIN for a circle.  A circle drawn above the terrain therefore sat in rows
;       the clean prefix (p4_hud_pfx_fill / _replay: KB[b] blocks from line 58) counts as final sky: the next frames
;       drawn into that buffer did not refill them and the explosion stayed on screen, cut off wherever the horizon
;       moved (Hatari STE and TT, stock is clean).
;       Fix: before the fill, YMIN = min(YMIN, cy - r) with cy = $181e2, r = $181de (the disc is inside the rows
;       cy-r .. cy+r: $1ceda computes exactly these as d5/d6 for its clip tests).  Smaller YMIN is always safe (less
;       of the prefix is trusted); rows above 58 are clamped to 0 by p4_hud_pfx_replay.  Tail call: the displaced
;       `jsr $5020.w ; rts` becomes `jmp $38cd0.l` from the blob (the filler's rts returns to the caller of $1cf64).
;       d4 is saved, every other register is left untouched (the filler reads d0/d2/d3/d7/a0/a1/a6).
YMIN    equ     $b4684

        org     $1d188
        jmp     $b4fc0.l

        org     $b4fc0
        move.l  d4,-(a7)
        move.w  $181e2.l,d4             ; cy
        sub.w   $181de.l,d4             ; cy - r = first possible row
        cmp.w   YMIN.l,d4
        bge.s   .n
        move.w  d4,YMIN.l
.n:     move.l  (a7)+,d4
        jmp     $38cd0.l                ; was jsr $5020.w / rts
