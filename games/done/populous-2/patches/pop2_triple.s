; name: pop2_triple
; default: yes
; site: $1bfe
; orig: 2039000392e02239000392dc
; data: PB+$17f0 16
; note: Triple buffering for Populous 2 ($1bfe): rotates 3 screen buffers (A=$2300, B=$a000, C=$90000)
;       on 2 MB+ machines ($42e > $100000), eliminating the half-VBL wait at $1bf4 (~3.9% of busy1).
;       Automatically falls back to double-buffering on 512 KB / 1 MB low-RAM machines.
;       Jumps to $1c16 with d0 = new_show so pop2_tt_ptr (TT/Falcon) runs unchanged.
;       Data T (PB+$17f0): +0 MAG.l ('P2T3'), +4 FREE.l, +8 LASTV.l.  Blob PB+$1700.

T       equ     PB+$17f0
tMAG    equ     0
tFREE   equ     4
tLASTV  equ     8
BUFC    equ     $90000

        org     $1bfe
        jmp     (PB+$1700).l
        nop
        nop
        nop

        org     PB+$1700
flip3:  cmpi.l  #$100000,$42e.w         ; > 1 MB RAM?
        bls.s   .dbl
        move.l  a0,-(a7)
        lea     T.l,a0
        cmpi.l  #$50325433,tMAG(a0)
        beq.s   .go
        move.l  #BUFC,tFREE(a0)
        move.l  $392d8.l,tLASTV(a0)
        move.l  #$50325433,tMAG(a0)
.go:    move.l  $392d8.l,tLASTV(a0)
        move.l  $392e0.l,d0             ; new_show = old back
        move.l  $392dc.l,d1             ; old_show -> next free
        move.l  tFREE(a0),$392e0.l      ; new_back = old free (ready immediately!)
        move.l  d0,$392dc.l             ; new_show -> front
        move.l  d1,tFREE(a0)
        movea.l (a7)+,a0
        jmp     $1c16.l
.dbl:   move.l  $392e0.l,d0
        move.l  $392dc.l,d1
        jmp     $1c0a.l
