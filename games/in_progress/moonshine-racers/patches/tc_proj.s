; name: tc_proj
; default: no
; site: $e316
; orig: 43f8100047f84804
; doc: Object projection $e316/$e338 (36 slots): the scale-term chain is skipped when the slot's $1e is 0 (always, in the first level), `moveq #9 / asr.l` becomes `asl.l #7 / swap` (state identical).
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md).  Site $e316 (the first two `lea`s) -> `jmp $B6C00.l` + nop; the blob is the whole routine ($e316 + $e338 loop, same memory results).  Callers: $7b34 and mx_sync's `jsr $e316.l`.
; note: Changes against stock $e338: (1) `muls d4,d6 / muls d2,d6 / moveq #9,d3 / asr.l d3,d6 / add.w (a3,d1.w),d6` keeps only the low word of the shifted product, so `asl.l #7,d6 / swap d6` gives the same low word
; note: (4 cycles less, d3 stays free); (2) `mulu.w $1e(a0),d4 / lsr.l #6,d4` with $1e = 0 yields d4 = 0, which collapses `sub.w d4,d5 / neg.w d4 / add.w d6,d4` to d5 = (a5,d1), d4 = (a4,d1);
; note: tst.w $1e(a0) selects that path, any other value runs the stock sequence.  Type 2 slots ($c = 2) run the stock code unchanged.  The hidden / visible result paths ($7fff markers, $2, $a) are the stock ones.
        org     $e316
        jmp     $B6C00.l
        nop

        org     $B6C00
tc_proj:
        lea     $1000.w,a1
        lea     $4804.w,a3
        lea     $48e4.w,a4
        lea     $49c4.w,a5
        lea     $13b0.w,a6
        lea     $2d80.w,a0
        moveq   #$1f,d7
        bsr.s   .loop
        lea     $2ca0.w,a0
        moveq   #3,d7
.loop:  btst    #0,4(a0)
        beq.w   .next
        move.w  $20(a0),d0
        lea     (a1,d0.w),a2
        moveq   #0,d1
        move.b  $2d54(a2),d1
        move.w  d1,$12(a0)
        move.b  $3154(a2),d1
        addi.b  #$20,d1
        move.w  d1,d4
        add.w   $1316.w,d4
        add.w   d1,d1
        move.w  d0,d3
        add.w   $13ae.w,d3
        andi.w  #$3ff,d3
        moveq   #0,d5
        moveq   #0,d6
        lea     (a6,d3.w),a2
        move.b  (a2),d5
        move.b  $400(a2),d6
        cmpi.w  #2,$c(a0)
        beq.s   .t2
        move.w  $1c(a0),d2
        bpl.s   .p
        move.w  d5,d6
.p:     muls    d4,d6
        muls    d2,d6
        asl.l   #7,d6
        swap    d6
        add.w   (a3,d1.w),d6
        move.w  d6,(a0)
.c8:    move.w  d4,$32(a0)
        tst.w   $1e(a0)
        bne.s   .gen
        move.w  (a5,d1.w),d5
        move.w  (a4,d1.w),d4
        beq.s   .hid
.chk:   cmpi.w  #$5a,d4
        bgt.s   .vis
.hid:   move.w  #$7fff,(a0)
        move.w  #$7fff,$2c(a0)
        bra.s   .next
.vis:   move.w  d4,2(a0)
        move.w  d5,$a(a0)
.next:  lea     $38(a0),a0
        dbra    d7,.loop
        rts
.gen:   mulu.w  $1e(a0),d4
        lsr.l   #6,d4
        move.w  (a5,d1.w),d5
        sub.w   d4,d5
        neg.w   d4
        move.w  (a4,d1.w),d6
        beq.s   .hid
        add.w   d6,d4
        bra.s   .chk
.t2:    move.w  $1c(a0),d2
        bpl.s   .t2a
        muls    d2,d5
        neg.w   d2
        muls    d2,d6
        bra.s   .t2b
.t2a:   muls    d2,d6
        neg.w   d2
        muls    d2,d5
.t2b:   muls    d4,d5
        muls    d4,d6
        moveq   #9,d3
        asr.l   d3,d5
        asr.l   d3,d6
        add.w   (a3,d1.w),d5
        add.w   (a3,d1.w),d6
        move.w  d5,(a0)
        move.w  d6,$2c(a0)
        bra.s   .c8
