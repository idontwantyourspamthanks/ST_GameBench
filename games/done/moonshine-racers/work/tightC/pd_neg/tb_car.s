; name: tb_car
; default: no
; site: $39ac
; orig: 00013f6e
; requires: tb_carph
; data: $BF000 1280
; ram: $C4000-$CFFFF generated player-car code cache (48 KB, written at run time)
; doc: Player car and its second layer drawn by run-time generated straight-line code (pixel-identical, plain 68000 only; stock kernel everywhere else).
; note: Site $39ac = the long in the kernel pointer table $399c (nibble 7 = 3 data planes): entry 4 columns -> `$13f6e`.  The object draw `$ed38` fetches it with `movea.l (a4,d3.w),a4` and `jsr (a4)`s it (`$ed6e`): every
; note: 4-column nibble-7 sprite now enters the stub at $BF500.  Slot $2c68 (the player car, bank $2156a/$25244/$28f0c) and slot $3480 (its second layer, bank $2ca48) are drawn by code generated from the bitmap for
; note: the call's (bitmap, rows, x&15): per row and destination column nothing / two `move.l #imm,d(a3)` (full mask) / `andi.l #~M,d(a3)` x2 + `ori.l`/`ori.w` (partial); one `rts`.  Everything else, and every
; note: call that is clipped, aligned (x&15 = 0), off the interior, or whose variant does not fit, jumps to the stock kernel `$13f6e` with the registers untouched.
; note: Validity: the game XORs wheel-animation lists into the player bank (`$ed90`, from `$11342`/`$11300`): the bitmap alternates between states.  tb_carph (site $ed90) keeps a byte per bitmap index (PH $BF440, one bit per list kind); the entry key is
; note: (bitmap, rows, shift, PH label).  The cache is also flushed when the pass counter $100e goes down (race restart) and when any of 3 probe longs of the source bitmap differs from the value seen at generation (checked every draw).
; note: Enabled by a run-time probe at the first call (supervisor mode, plain 68000 = `move.w ccr,d0` is illegal, and no Mega STE `$ff8e21` register: it bus-errors on an ST/STE): INIT $BF000 = 1 on, 2 off.
; note: Cache entries $BF080 (24 B: key a1.l, label<<16|rows<<4|shift .l, code.l, 3 probe longs), code pool $C4000-$CFFFF.  Generation (about 60 k cycles per variant) runs inside the draw that first needs a variant.
INIT    equ     $BF000                  ; b: 0 = not probed, 1 = generated path on, 2 = off
LASTP   equ     $BF002                  ; w: pass counter $100e of the previous draw
POOLP   equ     $BF004                  ; l: next free byte of the pool
NENT    equ     $BF008                  ; w: entries in use (1..)
LAST    equ     $BF00A                  ; w x2: offset of the last entry used by slot $2c68 / slot $3480
SAVSP   equ     $BF010                  ; l
TMPE    equ     $BF014                  ; l
SCR     equ     $BF020                  ; 3 x 6 words: 0, w w w w, 0 per plane
CHP     equ     $BF044                  ; 6 longs: chunk pointers of the variant being built
RR      equ     $BF05C                  ; w: rows left
CK      equ     $BF05E                  ; w: chunk index * 4
TMPL    equ     $BF060                  ; l: start of the variant's jsr list
ENT     equ     $BF080                  ; 40 entries of 24 bytes (entry 0 never matches): key.l, kw.l, code.l, 3 probe longs
PH      equ     $BF440                  ; 64 bytes: wheel-animation state of the player bitmaps (tb_carph)
POOL    equ     $C4000
POOLEND equ     $D0000
PO1     equ     148
PO2     equ     388
PO3     equ     652

        org     $39ac
        dc.l    $BF500

        org     $BF500
stub:   cmpa.w  #$2c68,a2
        beq.s   .s12
        cmpa.w  #$3480,a2
        bne.w   .stock
        lea     LAST+2.l,a0
        moveq   #0,d4
        bra.s   .com
.s12:   lea     LAST.l,a0
        moveq   #0,d4
        move.w  6(a2),d4                ; label = PH[bitmap index]
        add.w   8(a2),d4
        andi.w  #63,d4
        lea     PH.l,a3
        move.b  (a3,d4.w),d4
        swap    d4
.com:   cmpi.b  #1,INIT.l
        bne.w   .noinit
.go:    tst.w   d7
        ble.w   .stock
        tst.w   d1
        bmi.w   .stock
        move.w  d1,d2
        add.w   d7,d2
        cmpi.w  #200,d2
        bgt.w   .stock
        tst.w   d0
        bmi.w   .stock
        moveq   #15,d3
        and.w   d0,d3
        beq.w   .stock                  ; aligned: stock
        move.w  d0,d2
        lsr.w   #4,d2                   ; X0
        cmpi.w  #15,d2
        bgt.w   .stock
        move.w  d7,d5
        lsl.w   #4,d5
        or.w    d3,d5
        or.w    d5,d4                   ; key = label << 16 | rows << 4 | shift
        move.w  $100e.w,d5
        cmp.w   LASTP.l,d5
        bcc.s   .np
        bsr.w   flush                   ; the pass counter went down: new race
.np:    move.w  d5,LASTP.l
        lea     ENT.l,a3
        adda.w  (a0),a3
        cmpa.l  (a3),a1
        bne.s   .srch
        cmp.l   4(a3),d4
        bne.s   .srch
.hit:   move.l  8(a3),d5
        beq.w   .stock                  ; no code for this variant (did not fit)
        movea.l d5,a4
        move.l  PO1(a1),d6
        cmp.l   12(a3),d6
        bne.s   .bad
        move.l  PO2(a1),d6
        cmp.l   16(a3),d6
        bne.s   .bad
        move.l  PO3(a1),d6
        cmp.l   20(a3),d6
        bne.s   .bad
        move.w  d1,d6                   ; y * 160 + X0 * 8
        lsl.w   #5,d6
        move.w  d6,d3
        lsl.w   #2,d6
        add.w   d3,d6
        lsl.w   #3,d2
        add.w   d2,d6
        move.w  d6,$100c.l              ; the stock kernel's scratch word
        lea     (a5,d6.w),a3
        jmp     (a4)
.stock: jmp     $13f6e.l
.bad:   bsr.w   flush                   ; the source bitmap changed
.srch:  move.w  NENT.l,d6
        beq.s   .new
        subq.w  #1,d6
        lea     ENT+24.l,a3
.sl:    cmpa.l  (a3),a1
        bne.s   .sn
        cmp.l   4(a3),d4
        beq.s   .found
.sn:    lea     24(a3),a3
        dbra    d6,.sl
.new:   cmpi.w  #39,NENT.l
        bcc.w   .stock                  ; table full
        bsr.w   create
        movea.l TMPE.l,a3
.found: move.l  a3,d6
        sub.l   #ENT,d6
        move.w  d6,(a0)
        bra.w   .hit
.noinit: cmpi.b #2,INIT.l
        beq.w   .stock
        bsr.w   probe
        cmpi.b  #1,INIT.l
        bne.w   .stock
        bra.w   .go

flush:  clr.w   NENT.l
        clr.l   LAST.l
        move.l  #POOL,POOLP.l
        rts

; probe: plain 68000 without the Mega STE register -> INIT = 1, else 2.  Preserves all registers.
probe:  movem.l d0-d2/a0-a1,-(a7)
        move.w  sr,d2
        btst    #13,d2
        beq.s   .off                    ; user mode
        move.w  #$2700,sr
        move.l  a7,SAVSP.l
        movea.l $10.w,a1
        move.l  #.ill,$10.w
        move.l  #$ffffffff,d0
        dc.w    $42c0                   ; move.w ccr,d0: illegal on a 68000
        move.l  a1,$10.w
        swap    d0
        tst.w   d0
        bne.s   .off                    ; 68010 or later
        movea.l $8.w,a1
        move.l  #.be,$8.w
        move.b  $ff8e21.l,d0            ; Mega STE cache/speed register: bus error on an ST/STE
        move.l  a1,$8.w
        bra.s   .off                    ; no bus error: Mega STE
.be:    movea.l SAVSP.l,a7
        move.l  a1,$8.w
        move.b  #1,INIT.l
        bsr.w   flush
        bra.s   .out
.ill:   addq.l  #2,2(a7)
        moveq   #0,d0
        rte
.off:   move.b  #2,INIT.l
.out:   move.w  d2,sr
        movem.l (a7)+,d0-d2/a0-a1
        rts

; create: entry for (a1, d4 = label << 16 | rows << 4 | shift, d7 = rows, d3 = shift) + code.  TMPE = the entry.  Preserves all registers.
; The code is built in chunks of 8 rows (each ends with rts); the variant is a list `jsr chunk0 / jsr chunk1 / ... / jmp chunkN`.  A chunk identical to the same chunk of the earlier entry for the same bitmap, rows and shift
; (the other wheel-animation state: only the wheel rows differ) is shared instead of stored again.
create: movem.l d0-d7/a0-a4,-(a7)
        move.w  NENT.l,d0
        addq.w  #1,d0
        move.w  d0,NENT.l
        mulu.w  #24,d0
        lea     ENT.l,a3
        adda.w  d0,a3
        move.l  a3,TMPE.l
        move.l  a1,(a3)
        move.l  d4,4(a3)
        move.l  PO1(a1),12(a3)
        move.l  PO2(a1),16(a3)
        move.l  PO3(a1),20(a3)
        clr.l   8(a3)
        move.w  NENT.l,d0
        subq.w  #2,d0
        movea.l #0,a3                   ; sibling list (none)
        bmi.s   .nsib
        lea     ENT+24.l,a0
.ss:    cmpa.l  (a0),a1
        bne.s   .sn
        cmp.w   6(a0),d4
        bne.s   .sn
        movea.l 8(a0),a3
        bra.s   .nsib
.sn:    lea     24(a0),a0
        dbra    d0,.ss
.nsib:  movea.l POOLP.l,a4
        move.l  a4,d0
        bne.s   .pp
        movea.l #POOL,a4                ; first use without a flush
.pp:    move.w  d7,d0
        mulu.w  #150,d0
        add.l   #96,d0
        add.l   a4,d0
        cmpi.l  #POOLEND,d0
        bhi.w   .done                   ; does not fit: entry without code = stock kernel
        move.w  d3,d5                   ; shift
        move.w  d7,RR.l
        clr.w   CK.l
        move.w  d7,d0
        addq.w  #7,d0
        lsr.w   #3,d0
        mulu.w  #6,d0
        move.l  a4,TMPL.l
        adda.w  d0,a4                   ; room for the jsr list
        moveq   #0,d3                   ; row offset
.chunk: lea     SCR.l,a0
        move.w  RR.l,d0
        cmpi.w  #8,d0
        bls.s   .cs
        moveq   #8,d0
.cs:    sub.w   d0,RR.l
        mulu.w  #160,d0
        add.w   d3,d0
        movea.w d0,a2                   ; end offset of this chunk
        move.l  a4,-(a7)
.row:   move.w  (a1)+,2(a0)             ; p0 c0
        move.w  (a1)+,4(a0)             ; p0 c1
        move.w  (a1)+,14(a0)            ; p1 c0
        move.w  (a1)+,16(a0)            ; p1 c1
        move.w  (a1)+,26(a0)            ; p2 c0
        move.w  (a1)+,28(a0)            ; p2 c1
        move.w  (a1)+,6(a0)             ; p0 c2
        move.w  (a1)+,18(a0)            ; p1 c2
        move.w  (a1)+,30(a0)            ; p2 c2
        move.w  (a1)+,8(a0)             ; p0 c3
        move.w  (a1)+,20(a0)            ; p1 c3
        move.w  (a1)+,32(a0)            ; p2 c3
        moveq   #0,d6
.col:   move.l  (a0,d6.w),d0
        lsr.l   d5,d0
        move.l  12(a0,d6.w),d1
        lsr.l   d5,d1
        move.l  24(a0,d6.w),d2
        lsr.l   d5,d2
        move.w  d6,d4
        lsl.w   #2,d4
        add.w   d3,d4                   ; displacement of the destination column
        move.w  d0,d7
        or.w    d1,d7
        or.w    d2,d7
        beq.w   .next                   ; empty mask
        cmpi.w  #$ffff,d7
        beq.s   .full
        not.w   d7
        move.w  #$02ab,(a4)+            ; andi.l #~M:~M,d(a3)  planes 0,1
        move.w  d7,(a4)+
        move.w  d7,(a4)+
        move.w  d4,(a4)+
        move.w  #$02ab,(a4)+            ; planes 2,3
        move.w  d7,(a4)+
        move.w  d7,(a4)+
        addq.w  #4,d4
        move.w  d4,(a4)+
        subq.w  #4,d4
        tst.w   d0
        beq.s   .o1
        tst.w   d1
        beq.s   .o0
        move.w  #$00ab,(a4)+            ; ori.l #p0:p1,d(a3)
        move.w  d0,(a4)+
        move.w  d1,(a4)+
        move.w  d4,(a4)+
        bra.s   .o2
.o0:    move.w  #$006b,(a4)+            ; ori.w #p0,d(a3)
        move.w  d0,(a4)+
        move.w  d4,(a4)+
        bra.s   .o2
.o1:    tst.w   d1
        beq.s   .o2
        move.w  #$006b,(a4)+            ; ori.w #p1,d+2(a3)
        move.w  d1,(a4)+
        addq.w  #2,d4
        move.w  d4,(a4)+
        subq.w  #2,d4
.o2:    tst.w   d2
        beq.s   .next
        move.w  #$006b,(a4)+            ; ori.w #p2,d+4(a3)
        move.w  d2,(a4)+
        addq.w  #4,d4
        move.w  d4,(a4)+
        bra.s   .next
.full:  move.w  #$277c,(a4)+            ; move.l #p0:p1,d(a3)
        move.w  d0,(a4)+
        move.w  d1,(a4)+
        move.w  d4,(a4)+
        addq.w  #4,d4
        tst.w   d2
        beq.s   .f0
        move.w  #$277c,(a4)+            ; move.l #p2:0,d+4(a3)
        move.w  d2,(a4)+
        clr.w   (a4)+
        move.w  d4,(a4)+
        bra.s   .next
.f0:    move.w  #$42ab,(a4)+            ; clr.l d+4(a3)
        move.w  d4,(a4)+
.next:  addq.w  #2,d6
        cmpi.w  #10,d6
        bne.w   .col
        add.w   #160,d3
        cmpa.w  d3,a2
        bne.w   .row
        move.w  #$4e75,(a4)+
        move.l  (a7)+,d1                ; chunk start
        move.w  CK.l,d0                 ; chunk index * 4
        move.l  d1,d6                   ; pointer to use
        move.l  a3,d2
        beq.s   .keep                   ; no sibling
        move.w  d0,d2
        lsr.w   #1,d2
        add.w   d0,d2                   ; index * 6
        movea.l a3,a0
        adda.w  d2,a0
        move.l  2(a0),d6                ; the sibling's chunk
        movea.l d6,a0
        movea.l d1,a2
        move.l  a4,d2
        sub.l   d1,d2
        lsr.w   #1,d2
        subq.w  #1,d2
.cmp:   cmpm.w  (a0)+,(a2)+
        dbne    d2,.cmp
        beq.s   .same
        move.l  d1,d6                   ; differs: keep the new chunk
        bra.s   .keep
.same:  movea.l d1,a4                   ; identical: free it, use the sibling's
.keep:  lea     CHP.l,a0
        move.l  d6,(a0,d0.w)
        addq.w  #4,d0
        move.w  d0,CK.l
        tst.w   RR.l
        bne.w   .chunk
        movea.l TMPL.l,a0
        movea.l TMPE.l,a2
        move.l  a0,8(a2)
        lea     CHP.l,a2
        move.w  CK.l,d0
        lsr.w   #2,d0
        subq.w  #2,d0                   ; chunks - 2
        bmi.s   .last
.lj:    move.w  #$4eb9,(a0)+            ; jsr chunk
        move.l  (a2)+,(a0)+
        dbra    d0,.lj
.last:  move.w  #$4ef9,(a0)+            ; jmp last chunk
        move.l  (a2)+,(a0)+
        move.l  a4,POOLP.l
.done:  movem.l (a7)+,d0-d7/a0-a4
        rts
