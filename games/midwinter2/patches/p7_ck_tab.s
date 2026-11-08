; name: p7_ck_tab
; default: yes
; site: $30f26
; orig: 4cdf7fff4e75
; data: $b5000 24
; data: $b5020 192
; data: $b50e0 384
; note: P7 items 1+2, part 1/6 (work/notes/p7_cockpit_cull.md).  Cockpit coverage table, built from
;       the replay list ($71bc -> $68000) that the encoder $30e30 writes at every 3D-view entry (the
;       list differs per vehicle type: $732c maps $6220 to one of 18 cockpit picture files).
;       Site = the encoder's exit (movem.l (a7)+,d0-d7/a0-a6 ; rts): the blob decodes the list
;       (pixel exact: opaque = no mask bit in any plane, run-copy groups = 16 opaque px) into
;       per-row opaque runs (at most two per row, in order of appearance; a third run is dropped,
;       which is conservative) for rows KR0..199 (XTAB, x words), converts them to absolute
;       edge-table keys (KEYS), then turns XTAB into the "F" table: F(r) = U(r) & F(r+1), the columns
;       that are opaque in every row r..199.
;       Key of pixel x in row y = ((y*160 + (x>>4)*8) << 16) | mask[x&15], the same {offset, mask} word
;       pair the edge walker stores per row, so within a row the key is strictly monotonic in x and a
;       span (L, R) lies in a run iff Ka <= L and R <= Kb (Kb = key of the last pixel + 1).
;       Data block $b5000: EN.w (cull enabled in this terrain pass, p7_ck_enter), BUILT.w, SYT.w
;       (sy threshold = 129 - first dashboard row), $b5008-$b5017 spare (debug counters).
;       XTAB $b5020: 24 rows x (a0,b0,a1,b1) words, a = first opaque x, b = last; empty run a = $7fff.
;       KEYS $b50e0: 24 rows x (Ka0.l, Kb0.l, Ka1.l, Kb1.l); empty run = $7fffffff / 0.
;       build is also entered lazily (BUILDSAFE $b5290) by p7_ck_enter when BUILT = 0, which is
;       what makes live-applied snapshots work (the list is already in RAM, the encoder does
;       not run again).
EN      equ     $b5000
BUILT   equ     $b5002
SYT     equ     $b5004
XTAB    equ     $b5020
KEYS    equ     $b50e0
KR0     equ     176
NR      equ     24

        org     $30f26
        jmp     $b5280.l

        org     $b5280
        bsr.s   build                   ; $b5280: encoder exit (all registers are dead here)
        movem.l (a7)+,d0-d7/a0-a6       ; displaced
        rts
        dcb.w   4,$4e71                 ; pad to $b5290
        movem.l d0-d7/a0-a6,-(a7)       ; $b5290 BUILDSAFE
        bsr.s   build
        movem.l (a7)+,d0-d7/a0-a6
        rts

; build: clobbers every register
build:  lea     XTAB.l,a1
        moveq   #NR*2-1,d0
.c:     move.w  #$7fff,(a1)+
        clr.w   (a1)+
        dbra    d0,.c
        movea.l $71bc.w,a0
        move.w  (a0)+,d7                ; records - 1
        moveq   #0,d6                   ; destination byte offset from the screen base
.rec:   move.w  (a0)+,d0
        bmi.s   .cp
        add.w   d0,d6                   ; masked record: delta.w, mask.l, or1.l, or2.l
        move.l  (a0)+,d1
        addq.l  #8,a0
        move.w  d1,d2
        swap    d1
        or.w    d1,d2
        not.w   d2                      ; opaque pixels: bit 15 = leftmost
        bsr.w   .grp
        addq.w  #8,d6
        dbra    d7,.rec
        bra.s   .keys
.cp:    not.w   d0                      ; run-copy record: ~delta.w, n-1.w, 8n data bytes
        add.w   d0,d6
        move.w  (a0)+,d5
.cg:    move.w  #$ffff,d2
        bsr.w   .grp
        addq.l  #8,a0
        addq.w  #8,d6
        dbra    d5,.cg
        dbra    d7,.rec
.keys:  lea     XTAB.l,a1
        lea     KEYS.l,a2
        lea     $40000.l,a3             ; mask[16] table (left-fill masks)
        move.l  #KR0*160*65536,d6       ; row base (y*160) << 16: keys are absolute edge-table words
        moveq   #NR-1,d7
.kr:    moveq   #1,d5
.kq:    move.w  (a1)+,d0
        move.w  (a1)+,d1
        cmp.w   #$7fff,d0
        beq.s   .abs
        bsr.w   .key
        add.l   d6,d2
        move.l  d2,(a2)+
        addq.w  #1,d1
        move.w  d1,d0
        bsr.w   .key
        add.l   d6,d2
        move.l  d2,(a2)+
        bra.s   .kn
.abs:   move.l  #$7fffffff,(a2)+
        clr.l   (a2)+
.kn:    dbra    d5,.kq
        add.l   #160*65536,d6
        dbra    d7,.kr
        lea     XTAB.l,a1               ; first row with a run >= 16 px: SYT = 129 - row
        move.w  #KR0,d0
.d:     move.w  2(a1),d1
        sub.w   (a1),d1
        cmp.w   #15,d1
        bge.s   .f
        move.w  6(a1),d1
        sub.w   4(a1),d1
        cmp.w   #15,d1
        bge.s   .f
        lea     8(a1),a1
        addq.w  #1,d0
        cmp.w   #200,d0
        bne.s   .d
.f:     move.w  #129,d1
        sub.w   d0,d1
        move.w  d1,SYT.l
        subq.l  #8,a7                   ; F(r) = U(r) & F(r+1), in place in XTAB, rows 198..176 (the
        movea.l a7,a3                   ; columns that are opaque in every row r..199, <= 2 runs)
        lea     XTAB+(NR-1)*8.l,a1
        moveq   #NR-2,d7
.fr:    lea     -8(a1),a2
        move.l  #$7fff0000,(a3)
        move.l  #$7fff0000,4(a3)
        moveq   #0,d4
        movea.l a2,a4
        moveq   #1,d5
.fi:    movem.w (a4)+,d0-d1
        movea.l a1,a5
        moveq   #1,d6
.fj:    movem.w (a5)+,d2-d3
        cmp.w   d0,d2
        bge.s   .f1
        move.w  d0,d2
.f1:    cmp.w   d1,d3
        ble.s   .f2
        move.w  d1,d3
.f2:    cmp.w   d2,d3
        blt.s   .f3
        cmp.w   #8,d4
        bge.s   .f3
        move.w  d2,(a3,d4.w)
        move.w  d3,2(a3,d4.w)
        addq.w  #4,d4
.f3:    dbra    d6,.fj
        dbra    d5,.fi
        move.l  (a3),(a2)
        move.l  4(a3),4(a2)
        movea.l a2,a1
        dbra    d7,.fr
        addq.l  #8,a7
        move.w  #1,BUILT.l
        rts

; .key: d0.w = x -> d2.l = (((x>>4)*8) << 16) | mask[x&15]; a3 = $40000; clobbers d3
.key:   moveq   #0,d3
        move.w  d0,d3
        lsr.w   #4,d3
        lsl.w   #3,d3
        swap    d3
        move.w  d0,d2
        and.w   #15,d2
        add.w   d2,d2
        move.w  (a3,d2.w),d3
        move.l  d3,d2
        rts

; .grp: d6 = destination offset, d2 = opaque bits of the 16-px group; clobbers d0,d1,d3,d4,a1,a2
.grp:   moveq   #0,d3
        move.w  d6,d3
        divu.w  #160,d3                 ; low = row, high = byte offset in the row
        move.w  d3,d4                   ; row
        swap    d3
        add.w   d3,d3                   ; x of the group's first pixel
        sub.w   #KR0,d4
        bmi.s   .gx
        cmp.w   #NR,d4
        bcc.s   .gx
        lsl.w   #3,d4
        lea     XTAB.l,a1
        adda.w  d4,a1
        moveq   #-1,d4                  ; start of the open run (-1 = none)
        moveq   #15,d1
.px:    btst    d1,d2
        beq.s   .z
        tst.w   d4
        bpl.s   .nx
        move.w  d3,d4
        bra.s   .nx
.z:     tst.w   d4
        bmi.s   .nx
        bsr.s   .add
        moveq   #-1,d4
.nx:    addq.w  #1,d3
        dbra    d1,.px
        tst.w   d4
        bmi.s   .gx
        bsr.s   .add
.gx:    rts

; .add: row entry a1, run [d4, d3-1]; extends run 0 or run 1 if adjacent, else fills the first
; empty slot, else drops the run (conservative)
.add:   move.w  d3,d0
        subq.w  #1,d0
        cmp.w   #$7fff,(a1)
        beq.s   .s0
        movea.w 2(a1),a2
        addq.l  #1,a2
        cmpa.w  d4,a2
        beq.s   .e0
        cmp.w   #$7fff,4(a1)
        beq.s   .s1
        movea.w 6(a1),a2
        addq.l  #1,a2
        cmpa.w  d4,a2
        bne.s   .dr
        move.w  d0,6(a1)
.dr:    rts
.e0:    move.w  d0,2(a1)
        rts
.s0:    move.w  d4,(a1)
        move.w  d0,2(a1)
        rts
.s1:    move.w  d4,4(a1)
        move.w  d0,6(a1)
        rts
