; name: p4_pfx_fill
; default: no
; site: $15830
; data: $b4800 20
; note: item #5 part 1/4 of the clean-prefix set p4_pfx_{fill,ymin,replay,msg} (ported from MW2 p4_hud_pfx_*; all four together; there is
; note: no separate reset patch because $14e00 belongs to the timing set).
; note: Per-buffer state at $b4800: KB0.w KB1.w KB2.w (index (draw buffer>>16)-5 for $58000/$68000/$78000) = 8-row blocks from the window top ($171f4)
; note: that already hold the FINAL sky+goggles image in that buffer; YMIN.w ($b4806) smallest first row of a polygon filled this frame;
; note: CK.w CD7.w CA1.l CA0.l ($b4808..) replay skip cache. Reset: sub_014e00 (one frame) is called from the loop $14ac0
; note: (return $14ac4) and from every re-entry ($14a86: start / map / S-key mode switch, which also re-encode the goggles
; note: list $1bab8 and redraw the screens; $d1de). The sky fill sees the frame's return address at 64(a7) here (15 saved
; note: regs + its own return): != $14ac4 => forget all per-buffer state. Sky fill sub_01580e: a6 = window top row of the draw buffer, d7 = rows-1, then it loads
; note: d0-d5/a0-a5 with the fill words (first instruction $15830 `move.l #$ffff,d0`) and writes 144 or 160 B per row,
; note: one row per dbra ($15860/$15884/$158a8: every variant advances exactly one 160-B row per iteration).
; note: KB[b] blocks (8 rows each) already hold the final image: skip them (a6 += 160*8*KB, d7 -= 8*KB). The skipped rows
; note: are exact because final rows = sky fill + terrain + goggles replay; transparent goggles pixels show the sky,
; note: and the replay re-asserts the opaque ones. If every row is skipped, restore and return. Also resets YMIN.
; note: Unknown buffer address (not $58000/$68000/$78000) or KB==0 => the original full fill.
KB      equ     $b4800
YMIN    equ     $b4806
CK      equ     $b4808
        org     $15830
        jmp     $b4460.l
        org     $b4460
        cmpi.l  #$14ac4,64(a7)
        beq.s   .ok
        clr.l   KB.l
        clr.w   KB+4.l
        clr.w   CK.l
.ok:
        move.w  #200,YMIN.l
        move.l  $12d0a.l,d0
        swap    d0
        subq.w  #5,d0
        cmp.w   #2,d0
        bhi.s   .go
        add.w   d0,d0
        lea     KB.l,a0
        move.w  (a0,d0.w),d1
        beq.s   .go
        lsl.w   #3,d1                   ; rows to skip
        cmp.w   d7,d1
        bhi.s   .all                    ; skip >= rows (rows = d7+1)
        sub.w   d1,d7
        mulu.w  #160,d1
        adda.l  d1,a6
.go:    move.l  #$ffff,d0               ; displaced
        jmp     $15836.l
.all:   movem.l (a7)+,d0-d7/a0-a6
        rts
