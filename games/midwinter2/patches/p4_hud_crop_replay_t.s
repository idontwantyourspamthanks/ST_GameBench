; name: p4_hud_crop_replay_t
; default: no
; site: $30f2c
; orig: 48e7fffe207871c0
; note: TYPE-TABLE variant, see p4_hud_crop_clip_t.
; note: VISUAL-TRADEOFF EXPERIMENT (work/notes/cockpit.md section 4), part 3/3.  Cockpit overlay replay
;       $30f2c, foot mode only ($6220 = 13; other modes run the original loop).  The first replay into
;       each buffer (flag KB[b] = 0, cleared by p4_hud_reset at every 3D-view entry) first blanks lines
;       182-199 (2,880 B, colour 0) and replays the whole list, so the dashboard band is drawn once
;       per buffer; every later frame replays only the records above line 182 (the visor pillars) and
;       stops at the first record at or below it.  Needs p4_hud_crop_fill + p4_hud_crop_clip so that
;       nothing else writes lines 182-199.
KB      equ     $b4680

        org     $30f2c
        jmp     $b4540.l
        nop

        org     $b4540
        movem.l d0-d7/a0-a6,-(a7)       ; displaced
        movea.l $71c0.w,a0              ; displaced
        movea.l $71bc.w,a1
        move.w  (a1)+,d7
        move.w  $6220.w,d0
        andi.w  #$1f,d0
        lea     TYP(pc),a2
        tst.b   (a2,d0.w)
        beq.s   loop                    ; type not cropped: original replay
        move.l  a0,d1
        swap    d1
        andi.w  #1,d1
        add.w   d1,d1
        lea     KB.l,a2
        adda.w  d1,a2
        tst.w   (a2)
        bne.s   pil
        move.w  #1,(a2)                 ; first replay into this buffer: band + all records
        lea     32000(a0),a3
        moveq   #0,d0
        move.w  #719,d1
.cl:    move.l  d0,-(a3)                ; lines 182-199 (2880 B) = 0
        dbra    d1,.cl
        bra.s   loop
pil:    lea     29120(a0),a2            ; line 182
pl:     move.w  (a1)+,d0
        bmi.s   pcy
        adda.w  d0,a0
        cmpa.l  a2,a0
        bcc.s   done
        move.l  (a1)+,d1
        move.l  (a0),d0
        and.l   d1,d0
        or.l    (a1)+,d0
        move.l  d0,(a0)+
        and.l   (a0),d1
        or.l    (a1)+,d1
        move.l  d1,(a0)+
        dbra    d7,pl
        bra.s   done
pcy:    not.w   d0
        adda.w  d0,a0
        cmpa.l  a2,a0
        bcc.s   done
        move.w  (a1)+,d0
.cp:    move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        dbra    d0,.cp
        dbra    d7,pl
        bra.s   done
loop:   move.w  (a1)+,d0                ; original loop from $30f3a
        bmi.s   copy
        adda.w  d0,a0
        move.l  (a1)+,d1
        move.l  (a0),d0
        and.l   d1,d0
        or.l    (a1)+,d0
        move.l  d0,(a0)+
        and.l   (a0),d1
        or.l    (a1)+,d1
        move.l  d1,(a0)+
        dbra    d7,loop
done:   movem.l (a7)+,d0-d7/a0-a6
        rts
copy:   not.w   d0
        adda.w  d0,a0
        move.w  (a1)+,d0
.cq:    move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        dbra    d0,.cq
        dbra    d7,loop
        bra.s   done
TYP:    dc.b    0,1,0,1,0,0,1,1,0,1,1,0,1,1,0,1,0,0,0,1,0,0
        dc.b    0,0,0,0,0,0,0,0,0,0
