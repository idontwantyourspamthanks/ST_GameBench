; name: pop_detail_w
; default: yes
; prog: populous
; site: $143f0
; orig: 0c7900000003b260
; note: Companion to pop_detail: freezes 2-phase water animation ($3b260) in Low Detail mode ($bd6c0.w != 0).
;       100% identical in High Detail mode.  Blob $b6840.

        org     $143f0
        jsr     $b6840.l
        nop

        org     $b6840
det_w:  tst.w   $bd6c0.l                ; Low Detail?
        bne.s   .freeze                 ; returns with Z=0 -> bne.w $14400 taken (always tile 0)
        cmpi.w  #0,$03b260.l
.freeze:
        rts
