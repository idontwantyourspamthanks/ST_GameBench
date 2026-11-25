; name: pop2_snd
; default: yes
; site: $2a978
; orig: 41f90002b81e30390002b610
; data: PB+$1a40 4
; note: STE / Mega STE / TT / Falcon DMA sound for Populous 2 replacing Timer-A YM sample interrupt ($2aa4e).
;       Uses a lazy bus-error-safe probe of $ffff8901.w (and requires >1 MB RAM so $98000..$9bfff is free);
;       plain ST or low-RAM builds fall back automatically to original YM sound.
;       Populous 2 samples are 0-terminated unsigned 8-bit streams; converts to signed 8-bit at $98000 (16 KB)
;       and plays mono 6258 Hz (or 12517 Hz if timer data <= 70) via STE DMA.  Blob PB+$1900.

SBUF    equ     $98000
SMAX    equ     16384
SFLAG   equ     PB+$1a40                ; $534e4431 = DMA ok, $534e4432 = YM fallback

        org     $2a978
        jmp     (PB+$1900).l
        nop
        nop
        nop

        org     PB+$1900
snd2:   cmpi.l  #$534e4431,SFLAG.l
        beq.s   .dma
        cmpi.l  #$534e4432,SFLAG.l
        beq.w   .ym
        ; lazy probe: need >1 MB RAM AND working STE DMA register ($ffff8901.w)
        cmpi.l  #$100000,$42e.w
        bls.s   .noym
        movem.l a2-a4,-(a7)
        movea.l a7,a2
        movea.l $8.w,a3
        lea     .berr(pc),a4
        move.l  a4,$8.w
        clr.b   $ffff8901.w
        move.l  a3,$8.w
        movem.l (a7)+,a2-a4
        move.l  #$534e4431,SFLAG.l
        bra.s   .dma
.berr:  movea.l a2,a7
        move.l  a3,$8.w
        movem.l (a7)+,a2-a4
.noym:  move.l  #$534e4432,SFLAG.l
.ym:    lea     $2b81e.l,a0
        move.w  $2b610.l,d0
        jmp     $2a984.l

.dma:   movem.l d0-d2/a0-a1,-(a7)
        clr.b   $ffff8901.w
        sf.b    $2b60c.l                ; Timer-A idle
        lea     $2b81e.l,a0
        move.w  $2b610.l,d0
        add.w   d0,d0
        add.w   d0,d0
        move.w  d0,d1
        add.w   d0,d0
        add.w   d1,d0
        movea.l (a0,d0.w),a0            ; sample pointer (0-terminated unsigned 8-bit)
        lea     SBUF.l,a1
        move.w  #SMAX-1,d2
.cp:    move.b  (a0)+,d0
        beq.s   .end
        eor.b   #$80,d0
        move.b  d0,(a1)+
        dbra    d2,.cp
.end:   move.l  a1,d1
        subi.l  #SBUF,d1
        bclr    #0,d1                   ; even byte count
        beq.s   .out
        lea     SBUF.l,a0
        move.l  a0,d2
        move.b  d2,$ffff8907.w
        lsr.l   #8,d2
        move.b  d2,$ffff8905.w
        lsr.l   #8,d2
        move.b  d2,$ffff8903.w
        adda.l  d1,a0
        move.l  a0,d2
        move.b  d2,$ffff8913.w
        lsr.l   #8,d2
        move.b  d2,$ffff8911.w
        lsr.l   #8,d2
        move.b  d2,$ffff890f.w
        move.b  #$80,d2                 ; mono 6258 Hz
        cmpi.w  #70,$2b612.l            ; smaller timer data = higher sample rate
        bhi.s   .rt
        move.b  #$81,d2                 ; mono 12517 Hz
.rt:    move.b  d2,$ffff8921.w
        move.b  #1,$ffff8901.w          ; play once
.out:   movem.l (a7)+,d0-d2/a0-a1
        rts
