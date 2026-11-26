; name: cp_hiscore
; default: yes
; site: $8418
; orig: 610644fc00ff
; gate: ram2mb
; requires: cp_wrap cp_title cp_fetch cp_ptr cp_end cp_start
; doc: Campaigns: F10 on the hi-score screen opens the campaign menu too.
; note: Campaign feature, HD build.  Site $8418 = the key exit of the hi-score screen ($83ca, the second screen of the title's attract loop): `bsr.b $8420 / move.w #$ff,ccr` -> `jmp $B9F06.l` (cp_title's e2).
        org     $8418
        jmp     $B9F06.l
