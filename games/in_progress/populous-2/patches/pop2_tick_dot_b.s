; name: pop2_tick_dot_b
; default: yes
; site: $27942
; orig: 4eb900020058
; note: Fixed-rate world tick, part 6 of 8 (needs pop2_tick_dot_a, whose recorder it calls; work/notes/timing.md).  The effects loop's minimap pixel: $2793c `movea.l $392e0.l,a0` /
; note: $27942 `jsr $20058.l` (d2 = the colour word at $2795a, d0/d1 from the object's x/y).  Same hook as pop2_tick_dot_a.
        org     $27942
        jsr     PB+$2400.l
