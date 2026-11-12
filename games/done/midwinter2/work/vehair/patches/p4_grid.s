; name: p4_grid
; default: yes
; site: $1d768
; note: Terrain grid init $1d768 (sole caller bsr $1dc66).  Original loop: 1024 x 16-byte
;       records at $6c000: clr.l 6(a0); byte $b = (d1+d7+d6)&1; a0+=16 (86 cy/record).
;       Within a row parity alternates by record (d6 decrements): record k (0..31, d6=31-k)
;       has parity (q+1+k)&1, q=(d1+d7)&1.  Row fully unrolled, a0 not advanced inside the row
;       (move.l d2,x(a0) 16 + move.b dx,y(a0) 12 = 28 cy/record + 8/row).  Bytes +0..5, +$a untouched
;       exactly as before.  Exit state identical: d0=d1&1, d6.w=-1, d7.w=-1, a0=$70000,
;       flags = last andi.w #1 (X=0,N=0,V=C=0,Z=!(d1&1)); d2 saved/restored.
        org     $1d768
        jmp     $b3500.l

        org     $b3500
        move.l  d2,-(a7)
        lea     $6c000.l,a0
        moveq   #0,d2
        move.w  $18790.l,d1
        add.w   $18792.l,d1
        move.w  #$1f,d7
row:    move.w  d1,d0
        add.w   d7,d0
        and.w   #1,d0                   ; q
        move.w  d0,d6
        eor.w   #1,d6                   ; q+1 parity -> even k
K       set     6
        rept    16
        move.l  d2,K(a0)
        move.b  d6,K+5(a0)
K       set     K+16
        move.l  d2,K(a0)
        move.b  d0,K+5(a0)
K       set     K+16
        endr
        lea     $200(a0),a0
        dbra    d7,row
        move.w  #-1,d6
        move.l  (a7)+,d2
        move.w  d1,d0
        add.w   #0,d0
        and.w   #1,d0
        rts
