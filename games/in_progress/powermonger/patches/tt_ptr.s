; name: tt_ptr
; default: yes
; stage: 2
; site: $188c
; orig: 23c00002df78
; init: $ba900
; note: TT: the mouse pointer was invisible in the front end (name, option, chart screens) and flickered in the map view
;       (PMTT, work/notes/tt.md).  The game's pointer is drawn by the VBL handler ($1390 block, into the DISPLAYED buffer [$2df78]) and the
;       main loop flips with `jsr $187a`, which swaps [$2df78] / [$2df7c] and writes the new base to $ff8201/03 (`move.l d0,$8200.w` at
;       $1894).  On an ST / STE the shifter latches the base at the start of the next frame, so the buffer the VBL handler draws into is
;       the one that is displayed in that frame.  Hatari's TT video follows the base register LIVE, line by line: the front end
;       flips right after every VBL handler, so the display switches to the other buffer, which holds no pointer yet, for the whole frame
;       (the pointer is drawn into the buffer that has just been put away); in the map view the pointer is missing for the part of every
;       flip frame after the flip.  The pointer pixel rows ARE written each VBL, and the mouse position words are right.
;       Fix: on a TT or Falcon only (`init`, supervisor, TOS's cookie jar still intact, sets LIVE from the _MCH cookie high word 2 / 3)
;       the flip routine's `move.l d0,$2df78.l` ($188c, 6 bytes: the second half of the buffer swap; p7_triple_tail owns $1898 so this
;       patch sits before the base write instead) becomes `jsr tt_flip`: it runs it, then the VBL handler's own
;       pointer code (a verbatim copy of the original bytes $1390..$14c3, branches are relative inside the block: restore the 16 saved
;       lines of the pointer at [$1c49a], save and draw at [$2df92]/[$2df94] into the NEW displayed buffer [$2df78]) with the VBL and HBL
;       masked (SR IPL 4: the same context as the handler) so the handler cannot interleave, and `rts` (all registers kept: d0 is the base,
;       written to $ff8201/03 by the instructions after the site).  The pointer is therefore drawn into the buffer BEFORE it is put on the display.  The next VBL handler restores
;       and redraws as before (on a latching video the result is the original's).  Cost: one extra pointer draw (12 k cycles at 8 MHz,
;       0.4 ms at 32 MHz) per flip, only on a TT.  ptr_a / ptr_b (their record is validated against [$1c49a] and [$2df78]) are
;       independent: the first VBL after this draw takes their full path.
LIVE    equ     $baaf0                  ; byte: non-zero on a TT, set by `init`

        org     $188c
        jsr     $ba940.l

        org     $ba900
init:   clr.b   LIVE.l
        move.l  $5a0.w,d0
        beq.s   .r
        movea.l d0,a0
.l:     move.l  (a0)+,d0
        beq.s   .r
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .l
        swap    d1
        cmpi.w  #2,d1                   ; TT
        beq.s   .on
        cmpi.w  #3,d1                   ; Falcon (the combined-set cold boot showed the pointer missing in 3 of 20 screenshots there, as on the TT)
        bne.s   .r
.on:    st      LIVE.l
.r:     rts

        org     $ba940
tt_flip:
        move.l  d0,$2df78.l             ; the displaced instruction (the flip's swap is done: [$2df78] = the buffer about to be shown)
        tst.b   LIVE.l
        beq.s   .out
        tst.w   $1c6b2.l                ; the pointer is hidden: the handler skips the whole block
        bne.s   .out
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        ori.w   #$0400,sr               ; VBL / HBL cannot interleave (the handler's own level); MFP / ACIA still can, as in the handler
        bsr.s   ptr
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
.out:   rts
ptr:
        dc.w    $2039,$0001,$c49a,$6700,$002c,$2840,$4df9,$0001
        dc.w    $c49e,$3c39,$0001,$c6a0,$3e39,$0001,$c69e,$28de
        dc.w    $28de,$0c46,$0090,$6600,$0006,$28de,$28de,$d8c6
        dc.w    $51cf,$ffec,$3239,$0002,$df92,$3439,$0002,$df94
        dc.w    $3e3c,$000f,$0442,$00b8,$6f00,$0004,$9e42,$33c7
        dc.w    $0001,$c69e,$3c3c,$0090,$0c41,$0130,$6f00,$0006
        dc.w    $3c3c,$0098,$33c6,$0001,$c6a0,$3439,$0002,$df94
        dc.w    $2a7c,$ffff,$ffff,$2879,$0002,$df78,$3a01,$0245
        dc.w    $000f,$0241,$fff0,$e249,$c4fc,$00a0,$48c1,$d481
        dc.w    $d9c2,$23cc,$0001,$c49a,$47f9,$0000,$14e6,$3039
        dc.w    $0002,$c1be,$6722,$d6c0,$2239,$0006,$f304,$0241
        dc.w    $0007,$660e,$0640,$00a0,$b07c,$0280,$6d04,$303c
        dc.w    $00a0,$33c0,$0002,$c1be,$4df9,$0001,$c49e,$200d
        dc.w    $301b,$4281,$321b,$4282,$341b,$4283,$361b,$4284
        dc.w    $381b,$eab8,$eab9,$eaba,$eabb,$eabc,$3cd4,$c154
        dc.w    $835c,$3cd4,$c154,$855c,$3cd4,$c154,$875c,$3cd4
        dc.w    $c154,$895c,$0c46,$0090,$6600,$0024,$4840,$4841
        dc.w    $4842,$4843,$4844,$3cd4,$c154,$835c,$3cd4,$c154
        dc.w    $855c,$3cd4,$c154,$875c,$3cd4,$c154,$895c,$d8c6
        dc.w    $51cf,$ff9c
        rts
