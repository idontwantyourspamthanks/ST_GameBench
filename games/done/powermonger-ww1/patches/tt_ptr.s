; name: tt_ptr
; default: yes
; site: $e20
; orig: 23c00002ed98
; init: $75a00
; data: $75bf0 4
; note: TT / Falcon mouse pointer (master tt_ptr / work/notes/tt.md, re-sited).  The game's pointer is drawn by the VBL handler (block $87e..$9b7, into the DISPLAYED buffer
;       [$2ed98]) and the main loop flips with `jsr $e0e`, which swaps [$2ed98] / [$2ed9c] and writes the new base to $ff8201/03.  On an ST / STE the shifter latches the
;       base at the start of the next frame, so the buffer the VBL handler draws into is the one displayed in that frame.  Hatari's TT video follows the base register LIVE:
;       the display switches to the other buffer, which holds no pointer yet, for the whole frame.  Fix: on a TT or Falcon only (`init`, supervisor, TOS's cookie jar intact,
;       sets LIVE from the _MCH cookie high word 2 / 3) the flip routine's `move.l d0,$2ed98.l` ($e20, 6 bytes, the second half of the buffer swap) becomes `jsr tt_flip`: it
;       runs it, then the VBL handler's own pointer code (a verbatim copy of the original bytes $87e..$9b7 = `ptr` below, checked against the resident image by the gate;
;       branches are relative inside the block: restore the 16 saved lines of the pointer at [$1d2ba], save and draw at [$2edb2]/[$2edb4] into the NEW displayed buffer
;       [$2ed98]) with the VBL and HBL masked (SR IPL 4: the handler's context), and `rts` (all registers kept: d0 is the base, written to $ff8201/03 by the instructions after
;       the site).  The pointer is drawn into the buffer BEFORE it is put on the display; the next VBL handler restores and redraws as before.  Cost: one extra pointer draw per
;       flip, only on a TT / Falcon.  WW1 differences from master: addresses; the block is 6 bytes longer (`cmp.w #$320,d0 / beq.b`, WW1-only); hidden-pointer word $1d4d2.
LIVE    equ     $75bf0                  ; byte: non-zero on a TT / Falcon, set by `init`

        org     $e20
        jsr     $75a40.l

        org     $75a00
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
        cmpi.w  #3,d1                   ; Falcon
        bne.s   .r
.on:    st      LIVE.l
.r:     rts

        org     $75a40
tt_flip:
        move.l  d0,$2ed98.l             ; the displaced instruction (the flip's swap is done: [$2ed98] = the buffer about to be shown)
        tst.b   LIVE.l
        beq.s   .out
        tst.w   $1d4d2.l                ; the pointer is hidden: the handler skips the whole block
        bne.s   .out
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        ori.w   #$0400,sr               ; VBL / HBL cannot interleave (the handler's own level); MFP / ACIA still can, as in the handler
        bsr.s   ptr
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
.out:   rts
ptr:
        dc.w    $2039,$0001,$d2ba,$6700,$002c,$2840,$4df9,$0001
        dc.w    $d2be,$3c39,$0001,$d4c0,$3e39,$0001,$d4be,$28de
        dc.w    $28de,$0c46,$0090,$6600,$0006,$28de,$28de,$d8c6
        dc.w    $51cf,$ffec,$3239,$0002,$edb2,$3439,$0002,$edb4
        dc.w    $3e3c,$000f,$0442,$00b8,$6f00,$0004,$9e42,$33c7
        dc.w    $0001,$d4be,$3c3c,$0090,$0c41,$0130,$6f00,$0006
        dc.w    $3c3c,$0098,$33c6,$0001,$d4c0,$3439,$0002,$edb4
        dc.w    $2a7c,$ffff,$ffff,$2879,$0002,$ed98,$3a01,$0245
        dc.w    $000f,$0241,$fff0,$e249,$c4fc,$00a0,$48c1,$d481
        dc.w    $d9c2,$23cc,$0001,$d2ba,$47f9,$0000,$09da,$3039
        dc.w    $0002,$cfde,$6728,$d6c0,$b07c,$0320,$671a,$2239
        dc.w    $0007,$1b7c,$0241,$0007,$660e,$0640,$00a0,$b07c
        dc.w    $0280,$6d04,$303c,$00a0,$33c0,$0002,$cfde,$4df9
        dc.w    $0001,$d2be,$200d,$301b,$4281,$321b,$4282,$341b
        dc.w    $4283,$361b,$4284,$381b,$eab8,$eab9,$eaba,$eabb
        dc.w    $eabc,$3cd4,$c154,$835c,$3cd4,$c154,$855c,$3cd4
        dc.w    $c154,$875c,$3cd4,$c154,$895c,$0c46,$0090,$6600
        dc.w    $0024,$4840,$4841,$4842,$4843,$4844,$3cd4,$c154
        dc.w    $835c,$3cd4,$c154,$855c,$3cd4,$c154,$875c,$3cd4
        dc.w    $c154,$895c,$d8c6,$51cf,$ff9c
        rts
