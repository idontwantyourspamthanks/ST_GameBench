; name: pop2_bgcopy
; default: yes
; site: $1e7b2
; orig: 48e7fffe2279000392e0
; note: Unrolled 13-register movem.l copy of the 32,000-byte clean background ($392e4 -> $392e0),
;       replacing $1e7b2 (152.7k -> ~138k cycles/frame, ~1.2% of busy1).  100% pixel-identical.
;       Blob PB+$1600.

BLOB    equ     PB+$1600

        org     $1e7b2
        jmp     BLOB.l
        nop
        nop

        org     PB+$1600
bgcpy:  movem.l d0-d7/a0-a6,-(a7)
        movea.l $392e0.l,a0             ; destination: back buffer
        movea.l $392e4.l,a1             ; source: clean background
        lea     31980(a0),a2            ; 615 * 52 = 31,980
        move.l  a2,-(a7)
.rnd:   movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,52(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,104(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,156(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,208(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,260(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,312(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,364(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,416(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,468(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,520(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,572(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,624(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,676(a0)
        movem.l (a1)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,728(a0)
        lea     780(a0),a0
        cmpa.l  (a7),a0
        bne.w   .rnd
        addq.l  #4,a7
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        movem.l (a7)+,d0-d7/a0-a6
        rts
