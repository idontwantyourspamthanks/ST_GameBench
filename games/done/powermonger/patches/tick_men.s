; name: tick_men
; default: yes
; site: $130c2
; orig: 4eb900014b62
; note: P2 (needs tick_head). `jsr $14b62`: the people (men) update, 512 records of $32 bytes at $51b66
;       (state jump table at $14bb4, 32 units per axis per pass for walkers). Called 'status bars' in
;       hotpaths.md; it is the men simulation (timing.md). World logic: once per tick, not on a render-only pass (RON).
D       equ     $b8a00
        org     $130c2
        jsr     $b8960.l

        org     $b8960
men:    tst.w   D+6.l                   ; RON
        bne.s   .r
        jmp     $14b62.l
.r:     rts
