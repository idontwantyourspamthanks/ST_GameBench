; name: ms_cloud_a
; default: no
; site: $de1c
; orig: 7e0b2a7810084df829c8
; data: $BCC00 512
; doc: Cloud pass 1/2 skip (needs ms_cloud_b): erase + redraw of the 12 sky clouds ($de1c/$de6c, 80 k cycles a pass) is skipped when no cloud moved since this buffer was last drawn.
; note: Moonshine Racers sprite study (work/notes/sprites.md).  $de1c (erase) and $de6c (draw) walk the 12 cloud slots $29c8+n*$38 every pass.  Per sky pixel (backdrop bit B = 0) the pair
; note: sets plane 0 = ~(cloud mask) completely (E: P0 |= ~B, D: P0 &= ~C | B), pixels with B = 1 are untouched, so the pair is idempotent and independent of the old content.
; note: This blob (the $de1c hook) compares the 12 slots' keys (x, y, frame index $6+$8, active bit) with the keys stored when THIS back buffer was last drawn (two passes ago; $1008 selects the
; note: record, the pass counter $100e must be exactly 2 higher, the record must be valid, and `$2a(slot)` must equal the offset the draw left in `$28` one pass ago).  If all 12 match, the pair would
; note: rewrite the same pixels: skip it (FLAG tells the $de6c hook).  Rows >= 65 are NOT skipped: the horizon strip copy ($18318, rows 65-119) runs before the clouds and overwrites rows 65-69 each pass,
; note: so the part of every cloud below row 64 is still erased/drawn (the same $122e4 / $15052 kernels with row-clipped arguments; rows are independent).  The slot side effects ($2a := $28,
; note: $28 := old $2a, $100c) are replayed.  A race (re)init (cloud init $dd1c sets every $28 = $ffff) invalidates both records.  Registers on return as the original: a5 = $1008, a6 = $2c68, d7.w = $ffff.
STATE   equ     $BCC00
V0      equ     STATE+0
V1      equ     STATE+2
C0      equ     STATE+4
C1      equ     STATE+6
FLAG    equ     STATE+8
K0      equ     STATE+$10               ; 12 x 10 B: x, y, frame idx, active, pos (the offset drawn into THIS buffer, learned one pass later)
K1      equ     STATE+$88
SAVED   equ     STATE+$100              ; 12 x 2 B: the old $2a (= the new $28)
        org     $de1c
        jmp     $BC000.l
        nop
        nop

        org     $BC000
cloud_a:
        moveq   #$b,d7                  ; the replaced instructions
        movea.l $1008.w,a5
        lea     $29c8.w,a6
        movem.l d0-d6/a0-a4,-(a7)
        lea     K0.l,a0                 ; a0 = record of the buffer being drawn now, a3 = the other one
        lea     K1.l,a3
        lea     V0.l,a1
        cmpa.l  #$78000,a5
        bne.s   .bs
        lea     K1.l,a0
        lea     K0.l,a3
        lea     V1.l,a1                 ; a1 -> V[b], C[b] = 4(a1)
.bs:    ; one pass over the slots: learn the other buffer's pos ($28 now = what the last pass drew), count the $28 = $ffff slots
        lea     $29c8.w,a2
        movea.l a3,a4
        moveq   #11,d1
        moveq   #0,d3
.lp:    move.w  $28(a2),d2
        move.w  d2,8(a4)                ; other record, pos
        cmpi.w  #$ffff,d2
        bne.s   .nf
        addq.w  #1,d3
.nf:    lea     10(a4),a4
        lea     $38(a2),a2
        dbra    d1,.lp
        cmpi.w  #12,d3
        bne.s   .ni
        clr.w   V0.l                    ; every $28 = $ffff: a race (re)init: no record is valid
        clr.w   V1.l
.ni:    tst.w   (a1)
        beq.s   .store
        move.w  $100e.w,d0
        subq.w  #2,d0
        cmp.w   4(a1),d0
        bne.s   .store
        lea     $29c8.w,a2
        movea.l a0,a4
        moveq   #11,d1
.cmp:   move.w  (a2),d2
        cmp.w   (a4)+,d2
        bne.s   .store
        move.w  2(a2),d2
        cmp.w   (a4)+,d2
        bne.s   .store
        move.w  6(a2),d2
        add.w   8(a2),d2
        cmp.w   (a4)+,d2
        bne.s   .store
        moveq   #0,d2
        move.b  4(a2),d2
        andi.w  #1,d2
        cmp.w   (a4)+,d2
        bne.s   .store
        move.w  $2a(a2),d2
        cmp.w   (a4)+,d2
        bne.s   .store
        lea     $38(a2),a2
        dbra    d1,.cmp
        bra.s   .skip
.store: move.w  #1,(a1)                 ; not skippable: run the original loop, record the keys of this pass
        move.w  $100e.w,4(a1)
        lea     $29c8.w,a2
        movea.l a0,a4
        moveq   #11,d1
.st:    move.w  (a2),(a4)+
        move.w  2(a2),(a4)+
        move.w  6(a2),d2
        add.w   8(a2),d2
        move.w  d2,(a4)+
        moveq   #0,d2
        move.b  4(a2),d2
        andi.w  #1,d2
        move.w  d2,(a4)+
        addq.l  #2,a4                   ; pos: filled in by the next pass
        lea     $38(a2),a2
        dbra    d1,.st
        movem.l (a7)+,d0-d6/a0-a4
        jmp     $de26.l
.skip:  move.w  $100e.w,4(a1)           ; the record stays valid, its pass counter moves on
        move.w  #1,FLAG.l
        lea     $29c8.w,a2
        lea     SAVED.l,a4
        moveq   #11,d1
.s1:    move.w  $2a(a2),d0              ; old pos = the new $28
        move.w  d0,(a4)+
        move.w  $28(a2),$2a(a2)         ; the original loop tail
        move.w  #$ffff,$28(a2)
        cmpi.w  #$ffff,d0
        beq.s   .n1
        move.w  2(a2),d2                ; y
        move.w  $a(a2),d3               ; rows
        move.w  d2,d4
        add.w   d3,d4
        cmpi.w  #65,d4
        ble.s   .n1                     ; ends above row 65: nothing to do
        moveq   #65,d4
        sub.w   d2,d4
        bpl.s   .q
        moveq   #0,d4                   ; r0 = rows to skip at the top
.q:     sub.w   d4,d3                   ; rows left
        movea.l a5,a3
        adda.w  d0,a3                   ; screen at the old pos
        lea     $6f000.l,a1
        lsr.w   #2,d0
        andi.w  #$fffe,d0
        adda.w  d0,a1                   ; backdrop row
        move.w  d4,d5
        lsl.w   #5,d5                   ; r0 * 32
        move.w  d5,d6
        add.w   d5,d5
        add.w   d5,d5
        add.w   d6,d5                   ; r0 * 160
        adda.w  d5,a3
        move.w  d4,d5
        lsl.w   #3,d5                   ; r0 * 8
        add.w   d5,d6                   ; r0 * 32 + r0 * 8 = r0 * 40 (d6 = r0 * 32)
        adda.w  d6,a1
        move.w  d3,d7
        movem.l d1/a2/a4,-(a7)
        jsr     $122e4.l
        movem.l (a7)+,d1/a2/a4
.n1:    lea     $38(a2),a2
        dbra    d1,.s1
        movem.l (a7)+,d0-d6/a0-a4
        move.w  #$ffff,d7
        lea     $2c68.w,a6
        rts
