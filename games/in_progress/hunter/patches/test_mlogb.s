; name: test_mlogb
; default: no
; hdonly: yes
; site: $1b8
; orig: 4ef90000aff4
; note: Measurement only (tools/huntmouse.py): logs every byte the ACIA handler hands to the game's packet decoder (PP's hook at $1ae ends in `jmp $aff4.l`
; note: at $1b8; d0 = the byte), as an entry of type 3 in the log that test_mlogd keeps at $b8200.  Not in the release set.
        org     $1b8
        jmp     $8dc80.l

        org     $8dc80
mlogb:  movem.l d1/a0-a1,-(sp)
        lea     $b8200.l,a0
        move.l  (a0),d1
        beq.s   .skip
        cmp.l   #$bffe0,d1
        bcc.s   .skip
        movea.l d1,a1
        move.w  6(a0),(a1)+
        move.w  #3,(a1)+
        move.w  d0,(a1)+
        clr.w   (a1)+
        move.l  a1,(a0)
.skip:  movem.l (sp)+,d1/a0-a1
        jmp     $aff4.l
