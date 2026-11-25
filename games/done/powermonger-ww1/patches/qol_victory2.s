; name: qol_victory2
; default: yes
; site: $13f6c
; orig: 4a790002edb6
; note: click-to-retire on the "VICTORY" button (x=0..63, y=135..153) when in a full winning
;       position ($5a830 == 4), no window open ($74c0 == 0), and not paused ($5a856 == 0).
;       Consumes the left click ($2edb6), calls Retire ($d6b8 -> victory screen), and exits
;       this pass's click dispatch ($144b2).  Otherwise restores CCR and falls through to $13f72.

        org     $13f6c
        jmp     $75700.l

        org     $75700
hook:   tst.w   $2edb6.l                ; left button clicked?
        beq.s   .orig
        cmpi.w  #4,$5a830.l             ; full winning position?
        bne.s   .nz
        tst.w   $74c0.l                 ; any window open?
        bne.s   .nz
        tst.w   $5a856.l                ; paused?
        bne.s   .nz
        cmpi.w  #64,d0                  ; 0 <= x < 64?
        bhs.s   .nz
        cmpi.w  #135,d1                 ; 135 <= y < 154?
        blt.s   .nz
        cmpi.w  #154,d1
        bge.s   .nz
        clr.w   $2edb6.l                ; consume click
        movem.l d0-d7/a0-a6,-(a7)
        jsr     $d6b8.l                 ; Retire -> Victory screen
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $144b2.l                ; done with clicks this pass
.nz:    tst.w   $2edb6.l                ; restore CCR (Z=0) for $13f72 bne.b $13f7e
.orig:  jmp     $13f72.l
