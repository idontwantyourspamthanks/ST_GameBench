; name: pal_load
; default: no
; site: $6200
; orig: 3218e24902410777
; requires: pal_fade
; note: STE 4096-colour palette, part 2 of 2 (work/notes/visuals.md).  The direct palette loader $61f2 (called once per screen-mode
; note: change, $5f3c, with palette 1 = all black) does `move.w (a0)+,d1 / lsr.w #1,d1 / andi.w #$777,d1 / move.w d1,(a1)+` per colour.
; note: On STE-class palette hardware (FLAGS bit0) the 12-bit value is written in STE form: ((c >> 1) & $777) | ((c & $111) << 3).
; note: A plain ST / Mega ST takes the original two instructions.  d1.w = result; every other register is preserved.
FLAGS   equ     $8bff0
PALL    equ     $8c040

        org     $6200
        jsr     PALL.l                  ; replaces `move.w (a0)+,d1 / lsr.w #1,d1 / andi.w #$777,d1` (8 B)
        nop

        org     $8c040
pal_load:
        move.w  (a0)+,d1                ; original
        btst    #0,FLAGS+3.l
        beq.s   .st
        move.w  d1,-(sp)
        andi.w  #$111,d1
        lsl.w   #3,d1
        lsr.w   (sp)
        andi.w  #$777,(sp)
        or.w    (sp)+,d1
        rts
.st:    lsr.w   #1,d1                   ; the original instructions
        andi.w  #$777,d1
        rts
