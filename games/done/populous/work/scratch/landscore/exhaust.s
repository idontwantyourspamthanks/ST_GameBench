; Test scaffolding (not a game patch): run the ORIGINAL $18244 and the new one
; ($c0000, loaded but NOT hooked) on a list of (owner, cell range) inputs and compare
; d0.l, CCR (5 bits), $3b040.w, $37ef4.w and every register d1-d7/a0-a6.
; Entered once from the main loop's `jsr $db8a` ($b808 redirected by the test driver).
; Results: 6-byte records {d0.w, $3b040.b, $37ef4.b, ccr.b, flags.b}, original at
; RES_O, new at RES_N. flags: bit 0 = a register changed, bit 1 = outputs differ
; (set in both records). STAT: +0 total.l, +4 mismatches.l, +8 register faults.l,
; +12 'DONE'. TABLE (owner.w, first cell.w, count.w; owner $ffff ends) is appended
; by the driver, CCRIN is the CCR at each call.
RES_O   equ     $60000
RES_N   equ     $6c000
STAT    equ     $b2000
VARS    equ     $b2020
ORIG    equ     $1824c
NEW     equ     $c0000
CNT     equ     $3b040
FLAT    equ     $37ef4

        org     $b2100
start:  lea     STAT.l,a0
        clr.l   (a0)+
        clr.l   (a0)+
        clr.l   (a0)+
        clr.l   (a0)+
        move.l  #RES_O,VARS+0.l
        move.l  #RES_N,VARS+4.l
        lea     table(pc),a0
        move.l  a0,VARS+8.l
next_t: movea.l VARS+8.l,a0
        move.w  (a0)+,VARS+12.l         ; owner
        cmpi.w  #$ffff,VARS+12.l
        beq.w   done
        move.w  (a0)+,VARS+14.l         ; cell
        move.w  (a0)+,VARS+16.l         ; count
        move.l  a0,VARS+8.l
one:    ; ---- original
        movem.l sent(pc),d1-d7/a0-a6
        move.w  VARS+14.l,-(sp)
        move.w  VARS+12.l,-(sp)
        move.w  #CCRIN,ccr
        bsr.w   call_o
        move.w  sr,VARS+20.l
        addq.l  #4,sp
        movem.l d0-d7/a0-a6,VARS+32.l   ; d0 at +32, d1.. at +36
        move.w  CNT.l,VARS+22.l
        move.w  FLAT.l,VARS+24.l
        lea     VARS+36.l,a1
        bsr.w   regchk
        move.b  d2,VARS+26.l
        ; ---- new
        movem.l sent(pc),d1-d7/a0-a6
        move.w  VARS+14.l,-(sp)
        move.w  VARS+12.l,-(sp)
        move.w  #CCRIN,ccr
        jsr     NEW.l
        move.w  sr,VARS+100.l
        addq.l  #4,sp
        movem.l d0-d7/a0-a6,VARS+104.l  ; d0 at +104, d1.. at +108
        move.l  VARS+32.l,d6            ; d6 = original d0, d0 = new d0
        move.w  CNT.l,d4
        move.w  FLAT.l,d5
        moveq   #0,d3                   ; d3 = flags of this pair
        cmp.l   d6,d0
        bne.s   .dif
        cmp.w   VARS+22.l,d4
        bne.s   .dif
        cmp.w   VARS+24.l,d5
        bne.s   .dif
        move.w  VARS+20.l,d1
        move.w  VARS+100.l,d2
        eor.w   d1,d2
        andi.w  #$1f,d2
        beq.s   .same
.dif:   moveq   #2,d3
        addq.l  #1,STAT+4.l
.same:  lea     VARS+108.l,a1
        bsr.w   regchk
        or.b    VARS+26.l,d2
        beq.s   .r5
        addq.l  #1,STAT+8.l
.r5:    or.b    d2,d3
        ; ---- records
        movea.l VARS+0.l,a0
        move.w  d6,(a0)+
        move.b  VARS+23.l,(a0)+
        move.b  VARS+25.l,(a0)+
        move.b  VARS+21.l,(a0)+
        move.b  d3,(a0)+
        move.l  a0,VARS+0.l
        movea.l VARS+4.l,a0
        move.w  d0,(a0)+
        move.b  d4,(a0)+
        move.b  d5,(a0)+
        move.b  VARS+101.l,(a0)+
        move.b  d3,(a0)+
        move.l  a0,VARS+4.l
        addq.l  #1,STAT.l
        addq.w  #1,VARS+14.l
        subq.w  #1,VARS+16.l
        bne.w   one
        bra.w   next_t
done:   move.l  #'DONE',STAT+12.l
.spin:  bra.s   .spin

call_o: link.w  a5,#0                   ; the original's first two instructions
        movem.l d1-d6/a0-a2,-(sp)
        jmp     ORIG.l

regchk: ; d2 = 1 if any of d1-d7/a0-a6 saved at (a1) differs from sent
        lea     sent(pc),a0
        moveq   #13,d1
        moveq   #0,d2
.c1:    cmpm.l  (a0)+,(a1)+
        beq.s   .c2
        moveq   #1,d2
.c2:    dbra    d1,.c1
        rts

sent:   dc.l    $d1d1d1d1,$d2d2d2d2,$d3d3d3d3,$d4d4d4d4,$d5d5d5d5,$d6d6d6d6,$d7d7d7d7
        dc.l    $00a0a0a0,$00a1a1a0,$00a2a2a0,$00a3a3a0,$00a4a4a0,$00a5a5a0,$00a6a6a0
table:
