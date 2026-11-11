; name: p4_hud_pfx_replay
; default: yes
; site: $30f2c
; orig: 48e7fffe207871c0
; note: HUD "clean-prefix" set, part 4/4 (work/notes/cockpit.md section 3C).  Cockpit overlay replay
;       $30f2c.  After the terrain pass the rows above YMIN (smallest polygon row of the frame) are
;       untouched fill, and rows above 58+8*KB[b] were already final (fill skipped, p4_hud_pfx_fill).
;       So: (1) new KB[b] = (YMIN-58)>>3 clamped 0..17; (2) replay only records whose destination is at
;       or below line 58 + 8*min(old KB, new KB): a skip loop walks the list (14 B masked records /
;       4+8n B run-copy records, ascending destination) to the first such record, then the original
;       loop runs.  The stop position is cached (CK/CA1/CA0/CD7, cleared by p4_hud_reset) so the walk
;       only happens when min(old,new) KB changes.  The replay is idempotent: lines replayed twice
;       are harmless.
KB      equ     $b4680
YMIN    equ     $b4684
CK      equ     $b4686
CD7     equ     $b4688
CA1     equ     $b468c
CA0     equ     $b4690

        org     $30f2c
        jmp     $b4580.l
        nop

        org     $b4580
        movem.l d0-d7/a0-a6,-(a7)       ; displaced
        movea.l $71c0.w,a0              ; displaced: back buffer
        movea.l $71bc.w,a1              ; record list
        move.w  (a1)+,d7                ; records - 1
        movea.l a0,a4
        move.l  a0,d1
        swap    d1
        andi.w  #1,d1
        add.w   d1,d1
        lea     KB.l,a2
        adda.w  d1,a2                   ; a2 -> KB[b]
        move.w  YMIN.l,d0
        subi.w  #58,d0
        bpl.s   .p
        moveq   #0,d0
.p:     lsr.w   #3,d0                   ; new KB
        move.w  (a2),d1                 ; old KB
        move.w  d0,(a2)
        cmp.w   d1,d0
        bls.s   .m
        move.w  d1,d0                   ; d0 = min(old, new)
.m:     tst.w   d0
        beq.w   loop                    ; nothing to skip
        addq.w  #1,d0
        move.w  d0,d2                   ; cache key = min + 1
        cmp.w   CK.l,d0
        bne.s   .scan
        movea.l CA1.l,a1                ; cache hit
        adda.l  CA0.l,a0
        move.w  CD7.l,d7
        bra.w   loop
.scan:  subq.w  #1,d0
        mulu.w  #1280,d0
        lea     9280(a0),a2             ; line 58
        adda.l  d0,a2                   ; first line to replay
skip:   move.w  (a1)+,d0
        bmi.s   .c
        lea     (a0,d0.w),a3            ; destination
        cmpa.l  a2,a3
        bcc.s   .stop
        lea     12(a1),a1
        lea     8(a3),a0
        dbra    d7,skip
        bra.s   done
.c:     move.w  d0,d1
        not.w   d1
        lea     (a0,d1.w),a3
        cmpa.l  a2,a3
        bcc.s   .stop
        move.w  (a1)+,d0
        addq.w  #1,d0
        lsl.w   #3,d0
        adda.w  d0,a1
        lea     (a3,d0.w),a0
        dbra    d7,skip
        bra.s   done
.stop:  subq.l  #2,a1                   ; un-read the record's first word
        move.w  d2,CK.l
        move.l  a1,CA1.l
        move.l  a0,d0
        sub.l   a4,d0
        move.l  d0,CA0.l
        move.w  d7,CD7.l
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
.cp:    move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        dbra    d0,.cp
        dbra    d7,loop
        bra.s   done
