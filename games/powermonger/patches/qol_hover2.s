; name: qol_hover2
; default: no
; stage: 2
; site: $12138
; orig: 4a7900057fd4
; note: the sprite-side half of qol_hover (see there; harmless alone, it only reads ARM and writes HIT in qol_hover's state block HS).
;       $12138 is the game's per-object pick (called for every drawn object sprite, d0/d1 = sprite top-left, a3 = the object record);
;       its first instruction `tst.w $57fd4` (command selected?) becomes `jsr HVHOOK`; HVHOOK ends with that same tst, so the flags the
;       following `bne.b $12154` tests are the original ones.  Nothing else changes; the pick / click behaviour is untouched.
HS      equ     $cd5e0
HIT     equ     2

        org     $12138
        jsr     $cd560.l

        org     $cd560
; ---- HVHOOK (called by qol_hover2 in place of `tst.w $57fd4` at $12138; must end with that tst) ---------------------------------------
hvhook: tst.w   HS.l
        beq.s   .out
        movem.l d3-d4/a0,-(a7)
        move.w  #2,HS.l                 ; armed and a render is running
        moveq   #8,d3                   ; the game's own square size: $12154-$1216a
        move.b  6(a3),d4
        ext.w   d4
        lea     $120ea.l,a0
        move.w  (a0,d4.w),d4
        beq.s   .sz
        move.w  $57ffc.l,d4
        add.w   d4,d4
        lea     $12116.l,a0
        move.w  (a0,d4.w),d3
.sz:    move.w  $2df92.l,d4             ; pointer inside [d0, d0 + d3) x [d1, d1 + d3)?  (the game's test, $1216e-$121aa, with the live pointer)
        sub.w   d0,d4
        bmi.s   .no
        cmp.w   d3,d4
        bge.s   .no
        move.w  $2df94.l,d4
        sub.w   d1,d4
        bmi.s   .no
        cmp.w   d3,d4
        bge.s   .no
        cmpa.l  #$4f916,a3              ; only the house table
        blo.s   .no
        cmpa.l  #$51536,a3
        bhs.s   .no
        move.l  a3,HS+HIT.l
.no:    movem.l (a7)+,d3-d4/a0
.out:   tst.w   $57fd4.l
        rts

