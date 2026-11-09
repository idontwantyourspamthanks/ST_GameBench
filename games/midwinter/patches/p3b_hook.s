; name: p3b_hook
; default: yes
; site: $13236
; orig: 6100fdaa33f900012c9800015114
; note: P3 partial B (needs p3b_head; work/notes/timing.md). $13236 is the single entry of the
;       ski/walk step's common chain; every path of the state machine $131ae ends with
;       `bra.w $13236` (or falls into it) and the chain runs to the rts at $1327c.
;       The 14 bytes are the turn `bsr.w $12fe2` and the copy `move.w $12c98,$15114`.
;       SPLIT = 0 (every pass except PH 1 of a view-split group): the two original instructions.
;       SPLIT = 1 (p3b_head PH 1): this is the end of the state machine's work for the tick and the
;       chain is NOT run here (p3b_head PH 5 runs it from $13244). Instead:
;         H0 = $12c98 ; jsr $12fe2 (turn: fresh input, $12c98 += E, $15110 = E) ; HG = $12c98 ;
;         E = HG - H0 ; (DX,DZ) = floor(sin/cos(HG & $3fe) * $15112 / 65536) exactly as $14530 ;
;         (X0,Z0) = ($12c60,$12c64) ; view sub-step 1/5 (p3b_head substep).
;       The hook then returns to the caller of the mode step (p3b_head), dropping its own return.
D       equ     $b3700
        org     $13236
        jsr     $b3500.l
        nop
        nop
        nop
        nop

        org     $b3500
hook:   tst.w   D+8.l                   ; SPLIT
        bne.s   .split
        jsr     $12fe2.l                ; displaced
        move.w  $12c98.l,$15114.l       ; displaced
        rts
.split: addq.l  #4,a7                   ; the state machine ends here: back to p3b_head
        move.w  $12c98.l,D+10.l         ; H0
        jsr     $12fe2.l                ; the turn
        move.w  $12c98.l,d0
        move.w  d0,D+14.l               ; HG
        sub.w   D+10.l,d0
        move.w  d0,D+12.l               ; E
        move.w  D+14.l,d0
        andi.w  #$3fe,d0
        lea     $1c6bc.l,a0
        lea     (a0,d0.w),a0
        move.w  (a0),d0                 ; sin
        move.w  $100(a0),d1             ; cos
        move.w  $15112.l,d2             ; speed
        muls.w  d2,d0
        muls.w  d2,d1
        swap    d0
        swap    d1
        move.w  d0,D+24.l               ; DX = floor(sin*speed/65536)
        move.w  d1,D+26.l               ; DZ
        move.l  $12c60.l,D+16.l         ; X0
        move.l  $12c64.l,D+20.l         ; Z0
        jmp     $b3300.l                ; substep (tail call: returns to p3b_head)
