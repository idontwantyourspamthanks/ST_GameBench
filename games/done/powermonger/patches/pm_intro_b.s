; name: pm_intro_b
; default: yes
; stage: 1
; site: $144a
; orig: 203c0000000f
; note: PMTT: second delay routine of the intro, see pm_intro_a (wb: 48 units = 160 ms).
        org     $144a
        jmp     $cd784.l
