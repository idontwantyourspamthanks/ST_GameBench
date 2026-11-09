; name: test_blit
; default: no
; stage: 2
; site: $1305e
; orig: 22790002df7c
; data: $ce500 128
; note: test only (never shipped): random differential test of the sprite-blit paths of p4_spr (blitter / pre-shifted cache; TMODE.l = BLT value $b17e0001 or $b17e0002) against the original CPU
;       code `$124ae..` (the entry `$124a8` itself is patched, so the reference is the three replaced instructions + `jmp $124ae.l` in
;       this blob).  Runs once from the main loop (`movea.l $2df7c.l,a1` at $1305e) when TESTGO.w != 0 (`w $ce500 $00 $01`) for TESTN.l
;       trials: per trial a random shift s 1..15 (FORCES.w >= 0 forces one; 0 is allowed), rows 1..32, column 0..17 (the entry is only
;       reached for three columns on screen), a random destination in three buffers A ($e0000, the reference), B ($e1400) and C
;       ($e2800), 32 rows of 160 B each, and sprite rows: SHEET.w = 0: random words in SPR ($ce600; mask AND plane words all random, so
;       the bits a well-formed sprite never has are covered too); SHEET.w != 0: a random even address of the real sprite sheets
;       ($312a0..$3af1c, what the cache serves).  A = reference; B = the patched entry (BLT = 2: a miss that builds the cache entry, BLT = 1: blitter); C = the patched entry again, same key (BLT = 2: a hit).  The 160-byte rows are compared (a stray write
;       outside the three columns shows) and so are the final a0, a1, d0, d1, d2.
;       RES (= $ce510): +0 trials done, +4 trials with a mismatch (B or C), +8 first failing s.w rows.w col.w, +14 which (1 = B, 2 = C),
;       +16 byte offset in the row block, +20 reference long, +24 patched long there, +28 register mismatches, +32 DONE marker $600d.
TESTGO  equ     $ce500
TESTN   equ     $ce504
RES     equ     $ce510
SEED    equ     $ce540
VS      equ     $ce544
VROWS   equ     $ce546
VCOL    equ     $ce548
VA1     equ     $ce570
VOFF    equ     $ce54c
VN      equ     $ce550
RA0     equ     $ce554
RA1     equ     $ce558
RD1     equ     $ce55c
RD2     equ     $ce560
RD0     equ     $ce562
TMODE   equ     $ce574
SHEET   equ     $ce56c
FORCES  equ     $ce56e
BLT     equ     $bdc04
SPR     equ     $ce600
SCRA    equ     $e0000
SCRB    equ     $e1400
SCRC    equ     $e2800
        org     $1305e
        jsr     $ce200.l

        org     $ce200
tst:    tst.w   TESTGO.l
        beq.w   .out
        clr.w   TESTGO.l
        movem.l d0-d7/a0-a6,-(a7)
        clr.l   RES.l
        clr.l   RES+4.l
        clr.l   RES+8.l
        clr.l   RES+12.l
        clr.l   RES+16.l
        clr.l   RES+28.l
        clr.l   RES+32.l
        move.l  #$12345678,SEED.l
        move.l  TESTN.l,VN.l
.trial: tst.l   VN.l
        beq.w   .fin
        subq.l  #1,VN.l
        bsr.w   rnd
        andi.w  #15,d0
        tst.w   FORCES.l
        bmi.s   .nf
        move.w  FORCES.l,d0
.nf:    move.w  d0,VS.l
        bsr.w   rnd
        andi.w  #31,d0
        addq.w  #1,d0
        move.w  d0,VROWS.l
        bsr.w   rnd
        andi.l  #$ffff,d0
        divu    #18,d0
        swap    d0
        move.w  d0,VCOL.l
        lsl.w   #3,d0
        ext.l   d0
        move.l  d0,VOFF.l
        lea     SPR.l,a0                ; sprite rows
        move.l  a0,VA1.l
        tst.w   SHEET.l
        beq.s   .rnd
        bsr.w   rnd                     ; a real sheet address
        andi.l  #$ffff,d0
        divu    #$9000,d0
        swap    d0
        andi.l  #$fffe,d0
        add.l   #$312a0,d0
        move.l  d0,VA1.l
        bra.s   .dst
.rnd:   move.w  VROWS.l,d1
        mulu    #5,d1
        subq.w  #1,d1
.sp:    bsr.w   rnd
        move.l  d0,(a0)+
        dbra    d1,.sp
.dst:   lea     SCRA.l,a2               ; random destination rows, the same in A, B and C
        lea     SCRB.l,a3
        lea     SCRC.l,a4
        move.w  #32*40-1,d1
.sd:    bsr.w   rnd
        move.l  d0,(a2)+
        move.l  d0,(a3)+
        move.l  d0,(a4)+
        dbra    d1,.sd
        lea     SCRA.l,a0               ; reference -> A
        adda.l  VOFF.l,a0
        movea.l VA1.l,a1
        move.w  VS.l,d0
        moveq   #0,d2
        move.w  VROWS.l,d2
        moveq   #0,d1
        jsr     ref(pc)
        move.l  a0,RA0.l
        move.l  a1,RA1.l
        move.l  d1,RD1.l
        move.w  d2,RD2.l
        move.w  d0,RD0.l
        move.l  TMODE.l,BLT.l           ; patched entry -> B (BLT = 1: blitter; 2: pre-shifted cache, this call builds the entry)
        lea     SCRB.l,a0
        adda.l  VOFF.l,a0
        movea.l VA1.l,a1
        move.w  VS.l,d0
        moveq   #0,d2
        move.w  VROWS.l,d2
        moveq   #0,d1
        jsr     $124a8.l
        move.l  #SCRB,d6
        bsr.w   regs
        lea     SCRC.l,a0               ; again -> C (p4_pre: a hit)
        adda.l  VOFF.l,a0
        movea.l VA1.l,a1
        move.w  VS.l,d0
        moveq   #0,d2
        move.w  VROWS.l,d2
        moveq   #0,d1
        jsr     $124a8.l
        move.l  #SCRC,d6
        bsr.w   regs
        addq.l  #1,RES.l
        lea     SCRA.l,a2
        lea     SCRB.l,a3
        move.w  #32*40-1,d1
.cb:    cmpm.l  (a2)+,(a3)+
        bne.s   .badb
        dbra    d1,.cb
        lea     SCRA.l,a2
        lea     SCRC.l,a3
        move.w  #32*40-1,d1
.cc:    cmpm.l  (a2)+,(a3)+
        bne.s   .badc
        dbra    d1,.cc
        bra.w   .trial
.badb:  moveq   #1,d3
        bra.s   .bad
.badc:  moveq   #2,d3
.bad:   addq.l  #1,RES+4.l
        tst.l   RES+8.l
        bne.w   .trial
        move.w  VS.l,RES+8.l
        move.w  VROWS.l,RES+10.l
        move.w  VCOL.l,RES+12.l
        move.w  d3,RES+14.l
        move.l  a2,d0
        sub.l   #SCRA,d0
        subq.l  #4,d0
        move.l  d0,RES+16.l
        move.l  -4(a2),RES+20.l
        move.l  -4(a3),RES+24.l
        bra.w   .trial
.fin:   move.l  #$600d,RES+32.l
        movem.l (a7)+,d0-d7/a0-a6
.out:   movea.l $2df7c.l,a1             ; the displaced instruction
        rts
; compare the patched entry's final registers with the reference's (d6 = the base of the buffer it drew into)
regs:   move.l  a0,d3
        sub.l   d6,d3
        move.l  RA0.l,d4
        sub.l   #SCRA,d4
        cmp.l   d4,d3
        bne.s   .b
        cmpa.l  RA1.l,a1
        bne.s   .b
        cmp.l   RD1.l,d1
        bne.s   .b
        cmp.w   RD2.l,d2
        bne.s   .b
        cmp.w   RD0.l,d0
        beq.s   .ok
.b:     addq.l  #1,RES+28.l
.ok:    rts
ref:    moveq   #$78,d1                 ; the original: the three instructions of the site, then the code at $124ae
        neg.b   d1
        subq.w  #1,d2
        jmp     $124ae.l
rnd:    move.l  SEED.l,d0
        move.l  d0,d7
        moveq   #13,d6
        lsl.l   d6,d7
        eor.l   d7,d0
        move.l  d0,d7
        moveq   #17,d6
        lsr.l   d6,d7
        eor.l   d7,d0
        move.l  d0,d7
        moveq   #5,d6
        lsl.l   d6,d7
        eor.l   d7,d0
        move.l  d0,SEED.l
        rts
