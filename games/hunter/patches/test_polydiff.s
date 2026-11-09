; name: test_polydiff
; default: no
; site: $7554
; note: DIFFERENTIAL TEST WRAPPER for p4_poly (tools/polydiff.py; needs a 4 MB machine: shadow copies at $200000). NOT a game patch.
; note: Hooks the same site as p4_poly ($7554, entry of the polygon body). For every polygon it runs the NEW code (p4_poly's blob
; note: at $8c400: load it with the p4_poly image but do NOT apply p4_poly's site), saves the 3D window ($144(a5), 22400 bytes) and
; note: ($1600.l, $1618.b), restores the window as it was before, runs the ORIGINAL code (re-entered at $755a with the original
; note: displaced instructions) and compares window + $1600 + $1618. Counters: $8dfe0 polygons, $8dfe4 mismatches, $8dfe8 first
; note: mismatch: polygon list address, $8dfec its n, $8dfee first differing byte offset, $8dff2 variable mismatches.
SHA     equ     $200000
SHB     equ     $206000
CNT     equ     $8dfe0
P_N     equ     $8d000
        org     $7554
        jmp     $8dc00.l

        org     $8dc00
        movem.l d0-d7/a0-a4,-(a7)       ; d0 at (a7) ... a0 at 32(a7)
        movea.l $144(a5),a0
        lea     SHA.l,a1
        bsr     copy                    ; PRE := window
        movem.l (a7),d0-d7/a0-a4
        jsr     $8c400.l                ; NEW
        move.l  $1600(a5),CNT+$20.l
        move.b  $1618(a5),CNT+$24.l
        movea.l $144(a5),a0
        lea     SHB.l,a1
        bsr     copy                    ; POST(new) := window
        lea     SHA.l,a0
        movea.l $144(a5),a1
        bsr     copy                    ; window := PRE
        movem.l (a7),d0-d7/a0-a4
        pea     back(pc)
        move.w  d0,d6
        add.w   d6,d6
        move.w  d6,-(a7)
        jmp     $755a.l                 ; ORIGINAL
back:   addq.l  #1,CNT.l
        move.l  CNT+$20.l,d0
        cmp.l   $1600(a5),d0
        bne.s   .v
        move.b  CNT+$24.l,d0
        cmp.b   $1618(a5),d0
        beq.s   .w
.v:     addq.l  #1,CNT+$12.l
.w:     movea.l $144(a5),a0
        lea     SHB.l,a1
        move.w  #5599,d0
.c:     cmpm.l  (a0)+,(a1)+
        bne.s   .d
        dbra    d0,.c
        bra.s   .e
.d:     addq.l  #1,CNT+4.l
        tst.l   CNT+8.l
        bne.s   .e
        move.l  a0,d1
        sub.l   $144(a5),d1
        move.l  d1,CNT+$e.l
        move.l  32(a7),CNT+8.l          ; a0 at entry (polygon list start)
        move.w  P_N.l,CNT+$c.l
.e:     movem.l (a7)+,d0-d7/a0-a4
        rts
copy:   move.w  #559,d0
.l:     movem.l (a0)+,d1-d7/a2-a4
        movem.l d1-d7/a2-a4,(a1)
        lea     40(a1),a1
        dbra    d0,.l
        rts
