; name: p4_chase
; default: no
; stage: 2
; site: $13090
; orig: 4eb9000018704eb900012ce0
; note: P4 item 3, the 3D-window background copy `$12ce0` (work/notes/p4_raster.md section 4): copy the background while waiting for the VBL.
;       The main loop does `jsr $1870` (spin until the VBL handler sets $2df8c) and then `jsr $12ce0` (32000 B from the background
;       picture [$e0d4] = $78000 into the back buffer [$2df7c]: the frame decoration, the HUD panels and the pit the terrain is painted on;
;       every pass starts from this picture, the landscape/sprite/HUD code only draws over it).  The back buffer is the buffer that was
;       displayed until the flip at the end of the previous pass and it stays on screen until the next VBL, so the copy has to wait for
;       the VBL: the wait is idle time (4 % of a pass at 8 MHz, up to a whole VBL).  The beam only moves downwards, so rows ABOVE the
;       video counter have been displayed already in this frame and can be rewritten without any visible effect.  This routine replaces
;       both calls: it polls $2df8c and the video counter ($ff8205/07/09), copies the rows the beam has passed (minus 3 rows for the
;       shifter's prefetch) in chunks of up to 4 rows, and after the VBL copies the rest at full speed.  The first VBL after a flip runs the
;       pointer restore, which writes the saved pixels back into the old buffer's pointer rectangle (our back buffer): that rectangle
;       ([$1c49a], [$1c69e]+1 rows of 16 or 8 bytes, stride [$1c6a0], saved before the first VBL) is copied again from the background
;       after the flag is set, so the final buffer is the background everywhere, byte for byte what `$12ce0` leaves.  The pointer at x = 304,
;       y >= 184 (two columns, the last row 199) also writes 8 bytes beyond its buffer, into row 0 of the next one (the second buffer follows
;       the first in memory): row 0's first 8 bytes are copied again too (found by pmab.py: SHOWN DIFFER at pointer (304,184)).
;       Registers as `$1870` + `$12ce0` leave them: a0 += 32000, a1 += 32000, d0.w = $ffff, a2 = the last long of the background, the
;       rest (d1-d7, a3-a6) untouched.  Wait semantics unchanged: returns only after $2df8c != 0, so a pass still ends one VBL after the flip
;       at the earliest.
        org     $13090
        jsr     $bd980.l
        nop
        nop
        nop

        org     $bd980
chase:  movem.l d1-d7/a2-a6,-(a7)
        move.l  $1c49a.l,-(a7)          ; the pointer rectangle as the first VBL will restore it
        move.w  $1c69e.l,-(a7)
        move.w  $1c6a0.l,-(a7)
        movea.l a0,a3                   ; background
        movea.l a1,a4                   ; back buffer
        moveq   #0,d7                   ; rows copied
.lp:    tst.w   $2df8c.l
        bne.w   .fin
        lea     $ffff8205.w,a2          ; the beam: video counter, hi / mid / lo, re-read until mid is stable
.rd:    movep.w 0(a2),d3
        move.b  4(a2),d4
        move.b  2(a2),d5
        cmp.b   d3,d5
        bne.s   .rd
        moveq   #0,d5
        move.w  d3,d5
        lsl.l   #8,d5
        move.b  d4,d5                   ; 24-bit counter
        sub.l   a4,d5
        bmi.s   .all                    ; counter outside our buffer: the VBL has reloaded it, every row is free
        cmpi.l  #32000,d5
        bcc.s   .all
        divu    #160,d5                 ; the row the beam is in
        move.w  d5,d3
        bra.s   .have
.all:   move.w  #200+3,d3
.have:  subq.w  #3,d3                   ; rows above the beam, less the prefetch margin
        bmi.w   .lp
        cmpi.w  #200,d3
        bls.s   .lim
        move.w  #200,d3
.lim:   sub.w   d7,d3                   ; rows free and not yet copied
        bls.w   .lp
        cmpi.w  #4,d3
        bls.s   .k
        moveq   #4,d3
.k:     add.w   d3,d7
        move.w  d3,d6
        subq.w  #1,d6
.c:     bsr.w   row                     ; (row clobbers d1-d5)
        dbra    d6,.c
        bra.w   .lp
.fin:   cmpi.w  #200,d7                 ; the VBL is here: the rest at full speed
        bcc.s   .done
        bsr.w   row
        addq.w  #1,d7
        bra.s   .fin
.done:  move.w  (a7)+,d6                ; stride
        move.w  (a7)+,d5                ; rows - 1
        move.l  (a7)+,d4                ; the old pointer rectangle
        beq.s   .out
        sub.l   a4,d4
        bmi.s   .out
        cmpi.l  #32000-16,d4
        bhi.s   .out
        cmpi.w  #15,d5
        bhi.s   .out
        movea.l a3,a0                   ; (a0/a1 are set again below)
        movea.l a4,a1
        adda.l  d4,a0
        adda.l  d4,a1
        cmpi.w  #$90,d6
        beq.s   .r2
.r1:    move.l  (a0),(a1)               ; one column: 8 bytes per row
        move.l  4(a0),4(a1)
        lea     160(a0),a0
        lea     160(a1),a1
        dbra    d5,.r1
        bra.s   .out
.r2:    move.l  (a0),(a1)               ; two columns: 16 bytes per row
        move.l  4(a0),4(a1)
        move.l  8(a0),8(a1)
        move.l  12(a0),12(a1)
        lea     160(a0),a0
        lea     160(a1),a1
        dbra    d5,.r2
.out:   move.l  (a3),(a4)               ; the pointer drawn at x = 304 (two columns) in the last screen row spills 8 bytes into the next
        move.l  4(a3),4(a4)             ; buffer's row 0: when that is our back buffer the first VBL's spill came after the row-0 copy;
                                        ; the original copy erased it (later VBLs spill again, as in the original)
        lea     32000(a3),a0            ; the registers `$12ce0` leaves
        lea     32000(a4),a1
        movem.l (a7)+,d1-d7/a2-a6
        movea.l -4(a0),a2
        move.w  #-1,d0
        rts
; one row: 160 bytes a0 -> a1 (both advance), five movem pairs of 32 bytes.  Clobbers d1-d5, a2, a5, a6.
row:    movem.l (a0)+,d1-d5/a2/a5/a6
        movem.l d1-d5/a2/a5/a6,(a1)
        lea     32(a1),a1
        movem.l (a0)+,d1-d5/a2/a5/a6
        movem.l d1-d5/a2/a5/a6,(a1)
        lea     32(a1),a1
        movem.l (a0)+,d1-d5/a2/a5/a6
        movem.l d1-d5/a2/a5/a6,(a1)
        lea     32(a1),a1
        movem.l (a0)+,d1-d5/a2/a5/a6
        movem.l d1-d5/a2/a5/a6,(a1)
        lea     32(a1),a1
        movem.l (a0)+,d1-d5/a2/a5/a6
        movem.l d1-d5/a2/a5/a6,(a1)
        lea     32(a1),a1
        rts
