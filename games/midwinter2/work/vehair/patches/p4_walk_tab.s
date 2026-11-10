; name: p4_walk_tab
; default: yes
; site: $501a
; note: jump-table slot `jmp $3c5c4.l` (terrain caller `jsr $501a`) goes straight to the
;       blob walker entry, saving one 12-cycle jmp per call; see p4_walk.
        org     $501a
        jmp     $b3c0c.l
