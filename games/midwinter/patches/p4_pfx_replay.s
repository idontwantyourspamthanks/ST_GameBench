; name: p4_pfx_replay
; default: yes
; site: $1bbe6
; note: item #5 part 3/4 (port of MW2 p4_hud_pfx_replay). Goggles replay sub_01bbe6, called from the frame ($14e6c,
; note: return $14e72) after the terrain pass. Rows above YMIN are untouched sky and rows above top+8*KB[b] were
; note: already final: (1) new KB[b] = max(0,(YMIN-top)>>3), top = $171f4; (2) replay only records whose destination is at
; note: or below row top+8*min(old KB,new KB). The list ($1bbde = $74000) is row-major, ascending; masked records are
; note: 14 B (off.w, 12 B), run records `~off.w,count.w, 8*(count+1) B`, offsets relative to the previous record's end;
; note: runs never cross a row ($1bbc0 resets the run per row, encoder $1bab8), so a record starting above the
; note: boundary ends above it. The replay is idempotent (and/or masks), so re-replayed rows are harmless.
; note: Other callers ($2d6c) and unknown buffers run the original loop. Skip position cached by min+1 (CK) until
; note: p4_pfx_reset clears it.
; note: Displaces `movem.l d0-d7/a0-a6,-(a7) / movea.l $1bbe2.l,a0` (10 bytes).
KB      equ     $b4800
YMIN    equ     $b4806
CK      equ     $b4808
CD7     equ     $b480a
CA1     equ     $b480c
CA0     equ     $b4810
        org     $1bbe6
        jmp     $b4500.l
        nop
        nop
        org     $b4500
        movem.l d0-d7/a0-a6,-(a7)       ; displaced
        movea.l $1bbe2.l,a0             ; displaced: draw buffer
        movea.l $1bbde.l,a1             ; displaced: record list
        move.w  (a1)+,d7                ; displaced: records - 1
        cmpi.l  #$14e72,60(a7)          ; called from the frame? (15 regs saved = 60 bytes)
        bne.w   loop
        movea.l a0,a4
        move.l  a0,d1
        swap    d1
        subq.w  #5,d1
        cmp.w   #2,d1
        bhi.w   loop                    ; unknown buffer
        add.w   d1,d1
        lea     KB.l,a2
        adda.w  d1,a2                   ; a2 -> KB[b]
        move.w  YMIN.l,d0
        sub.w   $171f4.l,d0
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
        lsl.w   #3,d0                   ; rows
        mulu.w  #160,d0
        move.w  $171f4.l,d3
        mulu.w  #160,d3
        lea     (a0,d3.l),a2
        adda.l  d0,a2                   ; first row to replay
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
loop:   move.w  (a1)+,d0                ; original loop from $1bbf8
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
