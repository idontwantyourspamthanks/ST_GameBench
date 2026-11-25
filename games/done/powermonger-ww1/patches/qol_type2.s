; name: qol_type2
; default: yes
; site: $14b02
; orig: 4eb90000d32c
; note: drains all queued keys from qol_type's TFIFO and refreshes the name-entry window buffer BEFORE $74e0 redraws,
;       so typed characters appear immediately on the same frame with zero backlog.
TH      equ     $72f80
TT      equ     $72f82

        org     $14b02
        jsr     $72f40.l

        org     $72f40
drain:  move.w  TH.l,d0
        cmp.w   TT.l,d0
        beq.s   .last                   ; FIFO empty: normal single call
.lp:    jsr     $d32c.l                 ; pop & append 1 char
        tst.b   $d424.l                 ; Return pressed -> typing finished?
        beq.s   .done
        move.w  TH.l,d0
        cmp.w   TT.l,d0
        bne.s   .lp
.last:  jmp     $d32c.l                 ; copy updated string into window buffer before $74e0 draws
.done:  rts
