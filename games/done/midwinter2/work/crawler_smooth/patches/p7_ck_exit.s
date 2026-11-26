; name: p7_ck_exit
; default: yes
; site: $1dcae
; orig: 50790001877c
; phase: deferred
; note: P7 items 1+2, part 3/5 (work/notes/p7_cockpit_cull.md).  First instruction after `bsr.w $1fa54`
;       in $1dc12 (addq.w #8,$1877c.l): clears EN ($b5000) so the cull/trim hooks are only active
;       inside the terrain pass entered by p7_ck_enter.  Displaced instruction replayed here.
EN      equ     $b5000

        org     $1dcae
        jmp     $b54dc.l

        org     $b54dc
        clr.w   EN.l
        addq.w  #8,$1877c.l             ; displaced
        jmp     $1dcb4.l
