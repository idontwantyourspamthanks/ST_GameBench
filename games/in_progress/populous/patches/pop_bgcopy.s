; name: pop_bgcopy
; default: no
; site: $14a28
; orig: 4e55000048e700c0
; note: The 32,000-byte copy of the clean background ($3b016, the book / icons / minimap picture at $78000) over the back
;       buffer ($3c510) that the main loop makes at the start of every pass (`00b6f4 jsr $14a28`; also $b5f4 and $1d58a):
;         014a28 link.w a5,#0 / movem.l a0-a1,-(a7) / movea.l $3c510.l,a0 / movea.l $3b016.l,a1 / move.w #$1f3f,d0
;         014a40 move.l (a1)+,(a0)+ / dbra d0,$14a40      ; 8000 x 30 cycles = 240,000 + the frame, 257,000 measured
;       Replaced by a movem copy through 13 registers (d0-d7, a2-a6 = 52 bytes per block, 615 blocks in 41 unrolled rounds
;       of 15 = 146 k cycles) plus the last 20 bytes as five `move.l (a1)+,(a0)+` (so the flags the caller sees are the
;       original's: N/Z of the last long copied, V = C = 0, X untouched).  Same bytes copied, same order (ascending).
;       Registers: everything is restored except d0.w = $ffff (the original leaves the dbra's -1 there; the high word of d0 is
;       kept).  No interrupt is masked; the longest uninterruptible instruction is a 13-register movem (116 cycles; the original's
;       is 20), far below the IKBD byte time (10 k cycles at 8 MHz) that limits a chunked copy.  The remaining bytes of the
;       original routine are dead.  Blob $c2600-$c26ff.
        org     $14a28
        jmp     $c2600.l
        nop

        org     $c2600
cpy:    movem.l d0-d7/a0-a6,-(sp)       ; 15 longs: d0 at 0(sp) ... a6 at 56(sp)
        move.w  #$ffff,2(sp)            ; the d0 the caller gets back: high word kept, low word -1
        movea.l $3c510.l,a0             ; destination: the back buffer
        movea.l $3b016.l,a1             ; source: the clean background
        lea     31980(a0),a2            ; end of the 615 blocks (41 rounds); all 13 data registers are busy, so the
        move.l  a2,-(sp)                ; end pointer lives on the stack
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
        cmpa.l  (sp),a0
        bne.w   .rnd
        addq.l  #4,sp
        move.l  (a1)+,(a0)+             ; 20 bytes left: 615 x 52 = 31,980
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+             ; the flags the original ends with
        movem.l (sp)+,d0-d7/a0-a6
        rts
