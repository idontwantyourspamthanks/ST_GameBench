; name: pop2_triple_w
; default: yes
; site: $1bf4
; orig: 4a79000392cc67f8
; note: Companion to pop2_triple: skips the VBL spin at $1bf4 when triple-buffering is active
;       and at least 1 VBL has elapsed since the previous flip (prevents flipping > 1x/VBL on fast TT).
;       Blob PB+$1780.

T       equ     PB+$17f0
tMAG    equ     0
tLASTV  equ     8

        org     $1bf4
        jmp     (PB+$1780).l
        nop

        org     PB+$1780
wait3:  cmpi.l  #$50325433,T+tMAG.l     ; triple buffering active?
        bne.s   .orig
        move.l  d0,-(a7)
        move.l  T+tLASTV.l,d0
.wt:    cmp.l   $392d8.l,d0             ; wait only if still in same VBL as last flip
        beq.s   .wt
        move.l  (a7)+,d0
        rts
.orig:  tst.w   $392cc.l
        beq.s   .orig
        rts
