; name: test_blit
; default: no
; site: $12548
; orig: 4eb900001bf4
; data: PB+$6f30 96
; note: TEST ONLY (item 2 proof, work/notes/display.md): a random differential test of the sprite blitter inside the running game.  At the top of a pass (before the VBL wait)
; note: it runs TRIALS trials (word at PB+$6f30, set by the host; cleared when done).  Each trial picks x in -48..339, y in -40..229, rows 1..33, a sprite-row address and,
; note: one trial in eight, XORs a random word of those rows (restored afterwards: pop2_spr's cache must notice that the source changed), then calls the game's own
; note: front end `$2122e` (or, half of the trials, the 16 px front end `$211be`) twice on two identical random 32,000-byte screens: SA ($90000) with BLT = $b17e0003 (the ORIGINAL code) and SB ($98000) with the mode under test (word at
; note: PB+$6f32: 1 = blitter, 2 = pre-shifted cache).  The rows y-2..y+rows+2 (clipped to the screen) are compared after every trial and the whole screens every 64th trial; on a
; note: mismatch SB is re-synchronised from SA.  Results at PB+$6f40: +0 trials done (long), +4 mismatches (long), +8 x.w, +10 y.w, +12 rows.w, +14 a1.l of the first mismatch,
; note: +$18 full-screen mismatches (long), +$1c trials that used the pool sprites (long, they hit the cache), +$20 trials through the 16 px front end $211be (long).  Run: apply `test_blit pop2_spr` live, `w PB+$6f32 $00 <m>`, `w PB+$6f30 $ea $60`.
TRIALS  equ     PB+$6f30
TMODE   equ     PB+$6f32
RES     equ     PB+$6f40
SEED    equ     PB+$6f80                ; long
TCNT    equ     PB+$6f84                ; word: trials left
MUTA    equ     PB+$6f88                ; long: mutated word address (0 = none)
MUTW    equ     PB+$6f8c                ; word: its old value
SA      equ     $90000
SB      equ     $98000
BLT     equ     $88200
TBLIT   equ     PB+$6a00
        org     $12548
        jsr     TBLIT.l

        org     PB+$6a00
tb:     tst.w   TRIALS.l
        beq.w   .out
        movem.l d0-d7/a0-a6,-(a7)
        tst.l   SEED.l
        bne.s   .s0
        move.l  #$2545f491,SEED.l
.s0:    lea     SA.l,a0
        lea     SB.l,a1
        move.w  #7999,d6
.f:     bsr.w   rnd
        move.l  d0,(a0)+
        move.l  d0,(a1)+
        dbra    d6,.f
        move.w  TRIALS.l,TCNT.l
        subq.w  #1,TCNT.l
.t:     bsr.w   rnd                     ; x -48..339
        moveq   #0,d1
        move.w  d0,d1
        lsr.w   #3,d1
        divu    #388,d1
        swap    d1
        subi.w  #48,d1
        movea.w d1,a3
        bsr.w   rnd                     ; y -40..229
        moveq   #0,d1
        move.w  d0,d1
        lsr.w   #3,d1
        divu    #270,d1
        swap    d1
        subi.w  #40,d1
        movea.w d1,a4
        bsr.w   rnd                     ; rows 1..33
        moveq   #0,d1
        move.w  d0,d1
        lsr.w   #3,d1
        divu    #33,d1
        swap    d1
        addq.w  #1,d1
        movea.w d1,a5
        bsr.w   rnd                     ; sprite rows: half the trials from a pool of two real sprite addresses
        btst    #12,d0
        beq.s   .rand
        move.l  #$69450,d4
        btst    #13,d0
        beq.s   .pool
        move.l  #$6ac38,d4
.pool:  addq.l  #1,RES+$1c.l
        bra.s   .have
.rand:  moveq   #0,d4                   ; $40000 + 4 * (0..8191): even, rows*20 stays below $7b380
        move.w  d0,d4
        lsr.w   #3,d4
        lsl.l   #2,d4
        addi.l  #$40000,d4
.have:  movea.l d4,a2                   ; a2 = the sprite rows (the routines keep a2-a6)
        bsr.w   rnd                     ; front end: the 32 px one ($2122e) or the 16 px one ($211be, rows of 10 B)
        lea     $2122e.l,a6
        btst    #7,d0
        beq.s   .fe
        lea     $211be.l,a6
        addq.l  #1,RES+$20.l
.fe:
        clr.l   MUTA.l                  ; mutation: one trial in eight XORs a random word of the rows (restored after the calls)
        bsr.w   rnd
        move.w  d0,d3
        andi.w  #7,d3
        bne.s   .nomut
        move.w  a5,d1
        mulu    #20,d1
        move.l  d0,d2
        lsr.l   #3,d2
        andi.l  #$ffff,d2
        divu    d1,d2
        swap    d2                      ; byte offset in the rows
        andi.l  #$fffe,d2
        movea.l d4,a0
        adda.l  d2,a0
        move.l  a0,MUTA.l
        move.w  (a0),MUTW.l
        ori.w   #1,d0
        eor.w   d0,(a0)
.nomut: move.l  #$b17e0003,BLT.l        ; the original
        moveq   #0,d0
        move.w  a3,d0
        moveq   #0,d1
        move.w  a4,d1
        moveq   #0,d2
        move.w  a5,d2
        lea     SA.l,a0
        movea.l a2,a1
        jsr     (a6)
        moveq   #0,d0
        move.w  TMODE.l,d0
        ori.l   #$b17e0000,d0
        move.l  d0,BLT.l
        moveq   #0,d0
        move.w  a3,d0
        moveq   #0,d1
        move.w  a4,d1
        moveq   #0,d2
        move.w  a5,d2
        lea     SB.l,a0
        movea.l a2,a1
        jsr     (a6)
        move.l  MUTA.l,d0
        beq.s   .cmp
        movea.l d0,a0                   ; restore the mutated word
        move.w  MUTW.l,(a0)
.cmp:   move.w  a4,d0                   ; compare rows y-2 .. y+rows+2, clipped to 0..199
        subq.w  #2,d0
        bpl.s   .y0
        moveq   #0,d0
.y0:    move.w  a4,d1
        add.w   a5,d1
        addq.w  #2,d1
        cmpi.w  #199,d1
        ble.s   .y1
        move.w  #199,d1
.y1:    cmp.w   d0,d1
        blt.s   .done                   ; band entirely off screen
        sub.w   d0,d1                   ; rows - 1
        mulu    #160,d0
        lea     SA.l,a0
        lea     SB.l,a1
        adda.l  d0,a0
        adda.l  d0,a1
        move.w  d1,d2
.r:     moveq   #39,d3
.l:     cmpm.l  (a0)+,(a1)+
        dbne    d3,.l
        bne.s   .bad
        dbra    d2,.r
        bra.s   .done
.bad:   addq.l  #1,RES+4.l
        tst.l   RES+8.l
        bne.s   .resync
        move.w  a3,RES+8.l
        move.w  a4,RES+10.l
        move.w  a5,RES+12.l
        move.l  a2,RES+14.l
.resync:lea     SA.l,a0
        lea     SB.l,a1
        move.w  #7999,d0
.rs:    move.l  (a0)+,(a1)+
        dbra    d0,.rs
.done:  addq.l  #1,RES.l
        move.l  RES.l,d0
        andi.l  #63,d0
        bne.s   .nx
        lea     SA.l,a0                 ; every 64th trial: the whole screens
        lea     SB.l,a1
        move.w  #7999,d0
.fl:    cmpm.l  (a0)+,(a1)+
        dbne    d0,.fl
        beq.s   .nx
        addq.l  #1,RES+$18.l
        lea     SA.l,a0
        lea     SB.l,a1
        move.w  #7999,d0
.fr:    move.l  (a0)+,(a1)+
        dbra    d0,.fr
.nx:    subq.w  #1,TCNT.l
        bpl.w   .t
        clr.w   TRIALS.l
        movem.l (a7)+,d0-d7/a0-a6
.out:   jmp     $1bf4.l

rnd:    move.l  SEED.l,d0               ; xorshift32 in memory; returns d0; clobbers d1
        move.l  d0,d1
        lsl.l   #8,d1
        lsl.l   #5,d1
        eor.l   d1,d0
        move.l  d0,d1
        lsr.l   #8,d1
        lsr.l   #8,d1
        lsr.l   #1,d1
        eor.l   d1,d0
        move.l  d0,d1
        lsl.l   #5,d1
        eor.l   d1,d0
        move.l  d0,SEED.l
        rts
