; name: qol_victory2
; default: yes
; stage: 2
; site: $131f8
; orig: 4a790002df96
; note: click-to-retire on the "VICTORY" button (x=0..63, y=134..152) when in a full winning
;       position ($57fce == 4), no window open ($7a36 == 0), and not paused ($57ff2 == 0).
;       Consumes the left click ($2df96), calls Retire ($d2c8 -> victory screen), and exits
;       this pass's click dispatch ($1373c).  Otherwise restores CCR and falls through to $131fe.

        org     $131f8
        jmp     $dcf00.l

        org     $dcf00
hook:   tst.w   $2df96.l                ; left button clicked?
        beq.s   .orig
        cmpi.w  #4,$57fce.l             ; full winning position?
        bne.s   .nz
        tst.w   $7a36.l                 ; any window open?
        bne.s   .nz
        tst.w   $57ff2.l                ; paused?
        bne.s   .nz
        cmpi.w  #64,d0                  ; 0 <= x < 64?
        bhs.s   .nz
        cmpi.w  #134,d1                 ; 134 <= y < 153?
        blt.s   .nz
        cmpi.w  #153,d1
        bge.s   .nz
        clr.w   $2df96.l                ; consume click
        movem.l d0-d7/a0-a6,-(a7)
        jsr     $d2c8.l                 ; Retire -> Victory screen
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $1373c.l                ; done with clicks this pass
.nz:    tst.w   $2df96.l                ; restore CCR (Z=0) for $131fe bne.b $1320a
.orig:  jmp     $131fe.l
