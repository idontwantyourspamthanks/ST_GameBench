; name: qol_type2
; default: yes
; stage: 2
; site: $13d7c
; orig: 4eb90000cf46
; note: drains all queued keys from qol_type's TFIFO and refreshes the name-entry window buffer BEFORE $7a56 redraws,
;       so typed characters appear immediately on the same frame with zero backlog.
TH      equ     $dcb00
TT      equ     $dcb02

        org     $13d7c
        jsr     $dcbc0.l

        org     $dcbc0
drain:  move.w  TH.l,d0
        cmp.w   TT.l,d0
        beq.s   .last                   ; FIFO empty: normal single call
.lp:    jsr     $cf46.l                 ; pop & append 1 char
        tst.b   $d03e.l                 ; Return pressed -> typing finished?
        beq.s   .done
        move.w  TH.l,d0
        cmp.w   TT.l,d0
        bne.s   .lp
.last:  jmp     $cf46.l                 ; copy updated string into window buffer before $7a56 draws
.done:  rts
