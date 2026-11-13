; name: tb_frame
; default: yes
; site: $5fc2
; orig: 610e61004adc
; requires: tb_flip tb_vbl
; note: Triple buffering, part 2 of 3 (needs tb_flip: code, state; tb_vbl).  The 3D loop's frame boundary,
;       `bsr $5fd2` (the flip) + `bsr $aaa2` (wait for the next VBL), becomes `jsr tb_frame`:
;         flip, then  tb on  -> return at once (the pass starts in the spare page; tb_flip already guaranteed that a
;                               VBL has passed since the previous flip);
;                     tb off -> `jmp $aaa2`, the original wait (TT/Falcon: no change at all).
;       The `bra $5fa4` behind the site (the $1ac/$1aa VBL latch) is untouched.
A       equ     $23000
B       equ     $2ad00
C       equ     $81000
TBB     equ     $8c1b2
TBON    equ     TBB+4
TBFLIP  equ     $5fd2
TBCODE  equ     $8c2c0

        org     $5fc2
        jsr     TBCODE.l

        org     $8c2c0
tb_frame:
        jsr     TBFLIP.l                ; the flip (tb_flip's hook; falls back to the original on 68020+)
        move.w  TBON.l,d0
        cmpi.w  #1,d0
        beq.s   .out
        jmp     $aaa2.l                 ; 68020+: the original VBL lock
.out:   rts
