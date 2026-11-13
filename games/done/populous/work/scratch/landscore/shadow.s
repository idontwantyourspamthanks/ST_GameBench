; Test scaffolding (not a game patch): gate (a). Every call of $18244 and of $20796
; made by the running game is executed twice, by the new code ($c0000 / $c1000,
; loaded but not hooked) and by the original, with the same arguments, registers
; and CCR; the outputs are compared and the game continues with the original's.
; $18244 and $20796 are redirected here by the driver (jmp sh_score / jmp sh_mul).
;
; SV (counters): +0 score calls.l, +4 score mismatches.l, +8 score register faults.l,
;   +12 mul calls.l, +16 mul mismatches.l, +20 mul register faults.l,
;   +24 mul calls with both operands 0..65535.l, +28 logged records.w,
;   +32 score calls on the unrolled path.l, +36 on the edge path.l
; LOG: 32-byte records, first 200 mismatches:
;   score: 'S',0, return.l, owner.w, cell.w, turn.w, d0 new.l, d0 orig.l, ccr new.b,
;          ccr orig.b, $3b040 new.w, orig.w, $37ef4 new.w, orig.w, 0.w
;   mul:   'M',0, return.l, a.l, b.l, product new.l, product orig.l, ccr new.b, ccr orig.b
SV      equ     $b2000
SR_     equ     $b2040                  ; score: registers at entry (60 bytes)
SN      equ     $b2080                  ; score: new  {sr.w, pad.w, d0-d7/a0-a6, cnt.w, flat.w}
SO      equ     $b20d0                  ; score: orig {same}
MR      equ     $b2120                  ; mul: registers at entry
MN      equ     $b2160                  ; mul: new  {sr.w, pad.w, product.l, d0-d7/a0-a6}
MO      equ     $b21b0                  ; mul: orig
LOG     equ     $60000
NEW     equ     $c0000
NEWMUL  equ     $c1000
CNT     equ     $3b040
FLAT    equ     $37ef4

        org     $b2200
        bra.w   sh_score                ; $b2200: target of the jmp written at $18244
        bra.w   sh_mul                  ; $b2204: target of the jmp written at $20796
; ------------------------------------------------------------------ $18244
sh_score:                               ; stack: return, owner.w, cell.w
        move.w  sr,-(sp)                ; sr 0(sp), return 2(sp), owner 6(sp), cell 8(sp)
        movem.l d0-d7/a0-a6,SR_.l
        move.w  8(sp),-(sp)
        move.w  8(sp),-(sp)
        move.w  4(sp),ccr
        jsr     NEW.l
        move.w  sr,SN.l
        addq.l  #4,sp
        movem.l d0-d7/a0-a6,SN+4.l
        move.w  CNT.l,SN+64.l
        move.w  FLAT.l,SN+66.l
        movem.l SR_.l,d0-d7/a0-a6
        move.w  8(sp),-(sp)
        move.w  8(sp),-(sp)
        move.w  4(sp),ccr
        bsr.w   call_o
        move.w  sr,SO.l
        addq.l  #4,sp
        movem.l d0-d7/a0-a6,SO+4.l
        move.w  CNT.l,SO+64.l
        move.w  FLAT.l,SO+66.l
        addq.l  #1,SV.l
        ; path statistics (same tests as the patch's entry)
        cmpi.w  #1,6(sp)
        bhi.s   .st3
        move.w  8(sp),d0
        subi.w  #$80,d0
        cmpi.w  #$f00,d0
        bhs.s   .st2
        andi.w  #$3f,d0
        subq.w  #2,d0
        cmpi.w  #59,d0
        bhi.s   .st2
        addq.l  #1,SV+32.l
        bra.s   .st3
.st2:   addq.l  #1,SV+36.l
.st3:   ; outputs: d0.l, ccr, cnt, flat
        move.w  SN.l,d0
        move.w  SO.l,d1
        eor.w   d1,d0
        andi.w  #$1f,d0
        bne.s   .bad
        move.l  SN+4.l,d0
        cmp.l   SO+4.l,d0
        bne.s   .bad
        move.l  SN+64.l,d0
        cmp.l   SO+64.l,d0
        beq.s   .regs
.bad:   addq.l  #1,SV+4.l
        cmpi.w  #200,SV+28.l
        bhs.s   .regs
        move.w  SV+28.l,d0
        addq.w  #1,SV+28.l
        lsl.w   #5,d0
        lea     LOG.l,a0
        adda.w  d0,a0
        move.w  #$5300,(a0)+
        move.l  2(sp),(a0)+
        move.w  6(sp),(a0)+
        move.w  8(sp),(a0)+
        move.w  $3c506.l,(a0)+
        move.l  SN+4.l,(a0)+
        move.l  SO+4.l,(a0)+
        move.b  SN+1.l,(a0)+
        move.b  SO+1.l,(a0)+
        move.w  SN+64.l,(a0)+
        move.w  SO+64.l,(a0)+
        move.w  SN+66.l,(a0)+
        move.w  SO+66.l,(a0)+
        clr.w   (a0)+
.regs:  ; d1-d7/a0-a6 after the new code and after the original must equal the entry values
        lea     SR_+4.l,a0
        lea     SN+8.l,a1
        lea     SO+8.l,a2
        moveq   #13,d0
        moveq   #0,d1
.rl:    move.l  (a0)+,d2
        cmp.l   (a1)+,d2
        beq.s   .r1
        moveq   #1,d1
.r1:    cmp.l   (a2)+,d2
        beq.s   .r2
        moveq   #1,d1
.r2:    dbra    d0,.rl
        tst.w   d1
        beq.s   .ret
        addq.l  #1,SV+8.l
.ret:   movem.l SO+4.l,d0-d7/a0-a6
        addq.l  #2,sp
        move.w  SO.l,ccr                ; the original's result and flags
        rts
call_o: link.w  a5,#0
        movem.l d1-d6/a0-a2,-(sp)
        jmp     $1824c.l

; ------------------------------------------------------------------ $20796
sh_mul:                                 ; stack: return, a.l, b.l
        move.w  sr,-(sp)                ; sr 0(sp), return 2(sp), a 6(sp), b 10(sp)
        ori.w   #$700,sr                ; not re-entrant: keep interrupts out
        movem.l d0-d7/a0-a6,MR.l
        move.l  10(sp),-(sp)
        move.l  10(sp),-(sp)
        move.w  8(sp),ccr
        jsr     NEWMUL.l
        move.w  sr,MN.l
        move.l  (sp)+,MN+4.l
        movem.l d0-d7/a0-a6,MN+8.l
        movem.l MR.l,d0-d7/a0-a6
        move.l  10(sp),-(sp)
        move.l  10(sp),-(sp)
        move.w  8(sp),ccr
        bsr.w   call_om
        move.w  sr,MO.l
        move.l  (sp)+,MO+4.l
        movem.l d0-d7/a0-a6,MO+8.l
        addq.l  #1,SV+12.l
        tst.w   6(sp)
        bne.s   .nf
        tst.w   10(sp)
        bne.s   .nf
        addq.l  #1,SV+24.l
.nf:    move.w  MN.l,d0
        move.w  MO.l,d1
        eor.w   d1,d0
        andi.w  #$1f,d0
        bne.s   .bad
        move.l  MN+4.l,d0
        cmp.l   MO+4.l,d0
        beq.s   .regs
.bad:   addq.l  #1,SV+16.l
        cmpi.w  #200,SV+28.l
        bhs.s   .regs
        move.w  SV+28.l,d0
        addq.w  #1,SV+28.l
        lsl.w   #5,d0
        lea     LOG.l,a0
        adda.w  d0,a0
        move.w  #$4d00,(a0)+
        move.l  2(sp),(a0)+
        move.l  6(sp),(a0)+
        move.l  10(sp),(a0)+
        move.l  MN+4.l,(a0)+
        move.l  MO+4.l,(a0)+
        move.b  MN+1.l,(a0)+
        move.b  MO+1.l,(a0)+
.regs:  lea     MR.l,a0                 ; all of d0-d7/a0-a6 are preserved by both
        lea     MN+8.l,a1
        lea     MO+8.l,a2
        moveq   #14,d0
        moveq   #0,d1
.rl:    move.l  (a0)+,d2
        cmp.l   (a1)+,d2
        beq.s   .r1
        moveq   #1,d1
.r1:    cmp.l   (a2)+,d2
        beq.s   .r2
        moveq   #1,d1
.r2:    dbra    d0,.rl
        tst.w   d1
        beq.s   .ret
        addq.l  #1,SV+20.l
.ret:   movem.l MR.l,d0-d7/a0-a6
        move.w  (sp)+,sr                ; entry CCR and interrupt level back
call_om:
        link.w  a6,#0                   ; then the original, for real
        movem.l d0-d3/d7,-(sp)
        jmp     $2079e.l
