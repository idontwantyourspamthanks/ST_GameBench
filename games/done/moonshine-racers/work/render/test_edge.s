; Unit test: stock $1058a vs mr_edge's generated fast routine, same inputs, all 8 d7 bit combinations, the game's 15 colour tables + random tables.
; Load at $C0000 after `msrpatch live --only mr_edge`; entered with `jmp $C0000.l` from the race loop (site $7b74), runs once, then continues into $d1e4.
; Results: $C4100 = number of comparisons, $C4104 = number of mismatching comparisons, $C4108 = first mismatch info (ti, d7, d4, d5, d6 words), $C4200.. = dump of the first mismatch regs.
        org     $C0000
test:   movem.l d0-d7/a0-a6,-(a7)
        move.l  $135a.w,-(a7)              ; save the table pointer
        clr.l   $C4100.l
        clr.l   $C4104.l
        move.l  #$2545F491,d6              ; xorshift state
        moveq   #0,d5                      ; table index 0..14 real, then 200 random
.tab:   cmp.w   #15,d5
        bge.s   .rnd
        lea     $1362.w,a0
        move.w  d5,d0
        lsl.w   #2,d0
        movea.l (a0,d0.w),a5               ; real table pointer ($1362 array)
        bra.s   .have
.rnd:   ; random table at $C1000 or $C2000 (alternate: the hook regenerates only when the pointer changes)
        lea     $C1000.l,a5
        btst    #0,d5
        beq.s   .a
        lea     $C2000.l,a5
.a:     movea.l a5,a0
        moveq   #23,d4
.rw:    bsr     rnd
        move.l  d6,d0
        swap    d0
        btst    #3,d0
        beq.s   .z
        tst.w   d0                         ; nonzero random word (never zero)
        bne.s   .nz
        moveq   #1,d0
.nz:    move.w  d0,(a0)+
        bra.s   .wn
.z:     clr.w   (a0)+
.wn:    dbra    d4,.rw
.have:  move.l  a5,$135a.w
        movem.l d5-d6/a5,-(a7)
        jsr     $B3040.l                   ; mr_edge hook: a4 = fast routine, regenerate for ($135a)
        movem.l (a7)+,d5-d6/a5
        move.l  a4,$C4110.l
        moveq   #0,d4                      ; combination counter c = 0..7
.cmb:   moveq   #15,d3                     ; 16 random inputs per combination
.in:    bsr     rnd
        move.l  d6,$C4120.l                ; d4 in
        bsr     rnd
        move.l  d6,$C4124.l                ; d5 in
        bsr     rnd
        move.l  d6,$C4128.l                ; d6 in
        bsr     rnd
        move.l  d6,$C412C.l                ; d1 in
        bsr     rnd
        move.l  d6,$C4130.l                ; d3 in
        bsr     rnd
        move.l  d6,$C4134.l                ; d0 in
        bsr     rnd
        move.l  d6,$C4138.l                ; d2 in
        bsr     rnd
        move.l  d6,$C413C.l                ; d7 low bits
        move.w  d4,d0                      ; d7 = c<<13 | random low 13 bits | high word random
        ror.w   #3,d0
        and.w   #$e000,d0
        move.w  $C413E.l,d1
        and.w   #$1fff,d1
        or.w    d1,d0
        move.w  d0,$C413E.l
        movem.l d3-d6/a4/a5,-(a7)
        ; ---- stock
        move.l  $C4120.l,d4
        move.l  $C4124.l,d5
        move.l  $C4128.l,d6
        move.l  $C412C.l,d1
        move.l  $C4130.l,d3
        move.l  $C4134.l,d0
        move.l  $C4138.l,d2
        move.l  $C413C.l,d7
        jsr     $1058a.l
        movem.l d0-d7,$C4140.l
        ; ---- fast
        move.l  $C4120.l,d4
        move.l  $C4124.l,d5
        move.l  $C4128.l,d6
        move.l  $C412C.l,d1
        move.l  $C4130.l,d3
        move.l  $C4134.l,d0
        move.l  $C4138.l,d2
        move.l  $C413C.l,d7
        movea.l $C4110.l,a4
        ifd     NEG
        eor.l   #$ffff0000,d5               ; negative control: wrong input to the fast routine only
        endif
        jsr     (a4)
        movem.l d0-d7,$C4160.l
        movem.l (a7)+,d3-d6/a4/a5
        addq.l  #1,$C4100.l
        lea     $C4140.l,a0
        lea     $C4160.l,a1
        moveq   #7,d0
.cmp:   cmpm.l  (a0)+,(a1)+
        dbne    d0,.cmp
        beq.s   .ok
        addq.l  #1,$C4104.l
        tst.l   $C4108.l
        bne.s   .ok
        move.l  d5,$C4108.l
        addq.l  #1,$C4108.l                ; table number + 1
        move.l  $C413C.l,$C410C.l
.ok:    dbra    d3,.in
        addq.w  #1,d4
        cmp.w   #8,d4
        bne     .cmb
        addq.w  #1,d5
        cmp.w   #215,d5
        bne     .tab
        move.l  (a7)+,$135a.w
        jsr     $B3040.l                   ; regenerate for the real table
        move.l  #'DONE',$C4114.l
        move.w  #$4eb9,$7b74.w             ; restore the call site: run once
        move.l  #$d1e4,$7b76.w
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $d1e4.l

rnd:    move.l  d6,d0                      ; xorshift32 on d6 (clobbers d0)
        lsl.l   #8,d0
        lsl.l   #5,d0
        eor.l   d0,d6
        move.l  d6,d0
        lsr.l   #8,d0
        lsr.l   #8,d0
        lsr.l   #1,d0
        eor.l   d0,d6
        move.l  d6,d0
        lsl.l   #8,d0
        lsl.l   #5,d0
        eor.l   d0,d6
        rts
