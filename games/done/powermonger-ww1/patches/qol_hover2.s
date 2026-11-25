; name: qol_hover2
; default: yes
; site: $12ee0
; orig: 4a790005a836
; note: the sprite-side half of qol_hover (see there; harmless alone, it only reads ARM and writes HIT in qol_hover's state block HS).  $12ee0 is the game's per-object pick (called for
;       every drawn object sprite, d0/d1 = sprite top-left, a3 = the object record); its first instruction `tst.w $5a836` (command selected?) becomes `jsr HVHOOK`; HVHOOK ends with that
;       same tst, so the flags the following `bne.b $12efc` tests are the original ones.  Nothing else changes; the pick / click behaviour is untouched.  The square test is the game's own
;       ($12efc-$12f60) with the live pointer; the WW1-only size rule `cmpi.b #$e,$2c(a3) / blt / move.l #$18,d3` ($12f16) is repeated.
HS      equ     $73900
HIT     equ     2

        org     $12ee0
        jsr     $73940.l

        org     $73940
; ---- HVHOOK (called by qol_hover2 in place of `tst.w $5a836` at $12ee0; must end with that tst) ---------------------------------------
hvhook: tst.w   HS.l
        beq.s   .out
        movem.l d3-d4/a0,-(a7)
        move.w  #2,HS.l                 ; armed and a render is running
        moveq   #8,d3                   ; the game's own square size: $12efc-$12f20
        move.b  6(a3),d4
        ext.w   d4
        lea     $12e92.l,a0
        move.w  (a0,d4.w),d4
        beq.s   .sz
        move.w  $5a860.l,d4
        add.w   d4,d4
        lea     $12ebe.l,a0
        move.w  (a0,d4.w),d3
.sz:    cmpi.b  #$e,$2c(a3)             ; WW1: the game enlarges the square of these objects
        blt.s   .sq
        move.l  #$18,d3
.sq:    move.w  $2edb2.l,d4             ; pointer inside [d0, d0 + d3) x [d1, d1 + d3)?  (the game's test, $12f24-$12f60, with the live pointer)
        sub.w   d0,d4
        bmi.s   .no
        cmp.w   d3,d4
        bge.s   .no
        move.w  $2edb4.l,d4
        sub.w   d1,d4
        bmi.s   .no
        cmp.w   d3,d4
        bge.s   .no
        cmpa.l  #$54234,a3              ; only the house table
        blo.s   .no
        cmpa.l  #$5574c,a3
        bhs.s   .no
        move.l  a3,HS+HIT.l
.no:    movem.l (a7)+,d3-d4/a0
.out:   tst.w   $5a836.l
        rts
