; name: pop_snd
; default: yes
; prog: populous
; machine: ste, tt, falcon
; site: $16fbe
; orig: 4a79000249a06712
; data: $be000 16384
; note: STE / Mega STE / TT / Falcon DMA sound replacing the Timer-A YM sample interrupt ($1717e,
;       5.4% CPU during volcano/earthquake/SFX).  Plain ST keeps original YM sound via machine mask.
;       Converts unsigned 8-bit sample (a0, len d1, rate d0 Hz) to signed 8-bit in $be000 (16 KB)
;       and plays mono 6258 Hz (or 12517 Hz if rate >= 9000) via $ffff8900..$ffff8921.  Blob $b9200.

SBUF    equ     $be000
SMAX    equ     16384

        org     $16fbe
        jmp     $b9200.l
        nop

        org     $b9200
snd:    movem.l d0-d2/a0-a1,-(a7)
        clr.b   $ffff8901.w             ; stop any running DMA playback
        clr.w   $0249a0.l               ; YM Timer-A not active
        tst.l   d1
        ble.w   .out
        cmp.l   #SMAX,d1
        ble.s   .oklen
        move.l  #SMAX,d1
.oklen: bclr    #0,d1                   ; STE DMA requires even byte count
        beq.w   .out
        lea     SBUF.l,a1
        move.l  d1,d2
        subq.l  #1,d2
.cpy:   move.b  (a0)+,d0
        eor.b   #$80,d0                 ; unsigned 8-bit -> signed 8-bit for STE DMA
        move.b  d0,(a1)+
        dbra    d2,.cpy
        ; program STE DMA start ($be000) and end (a1)
        lea     SBUF.l,a0
        move.l  a0,d2
        move.b  d2,$ffff8907.w
        lsr.l   #8,d2
        move.b  d2,$ffff8905.w
        lsr.l   #8,d2
        move.b  d2,$ffff8903.w
        move.l  a1,d2
        move.b  d2,$ffff8913.w
        lsr.l   #8,d2
        move.b  d2,$ffff8911.w
        lsr.l   #8,d2
        move.b  d2,$ffff890f.w
        ; rate: d0 was clobbered by .cpy, reload from saved stack 0(a7)
        move.w  2(a7),d0                ; saved d0.w (rate in Hz)
        move.b  #$80,d2                 ; mono 6258 Hz
        cmp.w   #9000,d0
        blo.s   .rate
        move.b  #$81,d2                 ; mono 12517 Hz
.rate:  move.b  d2,$ffff8921.w
        moveq   #1,d2                   ; play once
        tst.b   $024990.l               ; loop flag?
        beq.s   .go
        moveq   #3,d2                   ; play + loop
.go:    move.b  d2,$ffff8901.w
        clr.b   $024991.l               ; allow subsequent SFX immediately (DMA can preempt cleanly)
.out:   movem.l (a7)+,d0-d2/a0-a1
        rts
