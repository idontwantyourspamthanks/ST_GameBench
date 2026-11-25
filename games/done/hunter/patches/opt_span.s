; name: opt_span
; default: yes
; site: $7a24
; orig: 0240000fd040
; note: Fast polygon span filler (replaces p4_poly .p2 + $7a7c..$7d00 solid-colour fills).
; note: Hooks $7a24 (colour select) to record col*2 in OPT_COL ($8dffe) without touching any other register.
; note: One-time bus-error-safe 68000 Blitter probe on first polygon:
; note:  - 68000 + Blitter (STE / Mega STE / Mega ST): 4-plane halftone HOG Blitter for multi-group spans, inline CPU for 1-group.
; note:  - Plain ST / TT / Falcon: inline 1-group fill + unrolled 18-group Duff's device (24 cyc/8 B vs 50 cyc/8 B).
P4_EMIT equ     $8d008
P4_SCR  equ     $8d00c
P4_SPAN equ     $8d100
P4_LTAB equ     $8ce00
OPT_COL equ     $8dffe

        org     $7a24
        jmp     $8dc00.l

        org     $8dc00
opt_col:
        andi.w  #$f,d0
        add.w   d0,d0
        move.w  d0,OPT_COL.l
        jmp     $7a32.l                 ; write $79fc.l (for $7932) + rts; skip dead $76ee.l

; Entry from p4_poly after .emit: fills P4_EMIT spans from P4_SPAN into P4_SCR.
        org     $8dc20
opt_span:
        move.w  P4_EMIT.l,d7
        subq.w  #1,d7
        movea.l P4_SCR.l,a1
        lea     P4_SPAN.l,a4
        lea     P4_LTAB.l,a2
        move.w  OPT_COL.l,d0            ; col * 2
        add.w   d0,d0                   ; col * 4
        add.w   d0,d0                   ; col * 8
        lea     col_tab(pc),a3
        movem.l (a3,d0.w),d4-d5         ; d4 = plane0:plane1, d5 = plane2:plane3
        moveq   #15,d6
        move.b  opt_bflg(pc),d0
        bgt.w   opt_blit
        beq.w   opt_probe
opt_cpu:
        move.w  (a4)+,d0                ; xl
        move.w  (a4)+,d1                ; xr
        bmi.s   .nx
        move.w  d0,d2
        and.w   d6,d2                   ; xl & 15
        sub.w   d2,d0                   ; xl_grp << 4
        move.w  d1,d3
        and.w   d6,d3                   ; xr & 15
        sub.w   d3,d1                   ; xr_grp << 4
        sub.w   d0,d1                   ; (xr_grp - xl_grp) << 4
        lsr.w   #1,d0                   ; xl_grp * 8
        lea     (a1,d0.w),a0
        add.w   d2,d2
        add.w   d2,d2
        add.w   d3,d3
        add.w   d3,d3
        tst.w   d1
        bne.s   .multi
        ; 1-group span: keep_out = (~left_in) | right_out
        move.l  (a2,d2.w),d2
        not.l   d2
        or.l    64(a2,d3.w),d2
        move.l  (a0),d0
        eor.l   d4,d0
        and.l   d2,d0
        eor.l   d4,d0
        move.l  d0,(a0)+
        move.l  (a0),d0
        eor.l   d5,d0
        and.l   d2,d0
        eor.l   d5,d0
        move.l  d0,(a0)
.nx:    adda.w  #160,a1
        dbra    d7,opt_cpu
        rts

.multi: ; left edge: keep_out = ~left_in
        move.l  (a2,d2.w),d2
        not.l   d2
        move.l  (a0),d0
        eor.l   d4,d0
        and.l   d2,d0
        eor.l   d4,d0
        move.l  d0,(a0)+
        move.l  (a0),d0
        eor.l   d5,d0
        and.l   d2,d0
        eor.l   d5,d0
        move.l  d0,(a0)+
        ; interior: (groups - 2) in 0..18, unrolled 24 cyc per 16-pixel group
        lsr.w   #2,d1                   ; (groups - 1) * 4 in 4..76
        neg.w   d1                      ; -4..-76
        jmp     .mend+4(pc,d1.w)
        rept    18
        move.l  d4,(a0)+
        move.l  d5,(a0)+
        endr
.mend:  ; right edge: keep_out = right_out (no not.l needed)
        move.l  64(a2,d3.w),d2
        move.l  (a0),d0
        eor.l   d4,d0
        and.l   d2,d0
        eor.l   d4,d0
        move.l  d0,(a0)+
        move.l  (a0),d0
        eor.l   d5,d0
        and.l   d2,d0
        eor.l   d5,d0
        move.l  d0,(a0)
        adda.w  #160,a1
        dbra    d7,opt_cpu
        rts

; ---- STE Blitter 4-plane HOG span filler (groups >= 2; groups == 1 inline CPU) ---------------------------------------
opt_blit:
        lea     $ffff8a28.w,a3          ; Blitter ENDMASK1 base (constants ENDMASK2/DST_XINC/HOP/OP/SKEW set in opt_probe)
        ; Load HALFTONE[0, 15, 14, 13] = plane 0, 1, 2, 3 (DST_YINC < 0 decrements line_num: 0 -> 15 -> 14 -> 13)
        move.w  d4,-$a(a3)              ; $8a1e HALFTONE[15] = plane 1
        swap    d4
        move.w  d4,-$28(a3)             ; $8a00 HALFTONE[0]  = plane 0
        swap    d4
        move.w  d5,-$e(a3)              ; $8a1a HALFTONE[13] = plane 3
        swap    d5
        move.w  d5,-$c(a3)              ; $8a1c HALFTONE[14] = plane 2
        swap    d5
.brow:  move.w  (a4)+,d0                ; xl
        move.w  (a4)+,d1                ; xr
        bmi.s   .bnx
        move.w  d0,d2
        and.w   d6,d2                   ; xl & 15
        sub.w   d2,d0                   ; xl_grp << 4
        move.w  d1,d3
        and.w   d6,d3                   ; xr & 15
        sub.w   d3,d1                   ; xr_grp << 4
        sub.w   d0,d1                   ; (xr_grp - xl_grp) << 4
        lsr.w   #1,d0                   ; xl_grp * 8
        lea     (a1,d0.w),a0
        add.w   d2,d2
        add.w   d2,d2
        tst.w   d1
        bne.s   .bmulti
        ; 1-group span: inline CPU is faster than Blitter setup
        add.w   d3,d3
        add.w   d3,d3
        move.l  (a2,d2.w),d2
        not.l   d2
        or.l    64(a2,d3.w),d2
        move.l  (a0),d0
        eor.l   d4,d0
        and.l   d2,d0
        eor.l   d4,d0
        move.l  d0,(a0)+
        move.l  (a0),d0
        eor.l   d5,d0
        and.l   d2,d0
        eor.l   d5,d0
        move.l  d0,(a0)
.bnx:   adda.w  #160,a1
        dbra    d7,.brow
        rts

.bmulti:
        move.w  (a2,d2.w),(a3)          ; ENDMASK1 = left_in
        add.w   d3,d3                   ; (xr & 15) * 2
        move.w  rtab_in(pc,d3.w),4(a3)  ; ENDMASK3 = ~right_out
        lsr.w   #3,d1                   ; (groups - 1) * 2 in 2..38
        move.w  yinc_tab-2(pc,d1.w),8(a3) ; DST_YINC = 2 - 8*(groups - 1)
        move.l  a0,$a(a3)               ; DST_ADDR
        add.w   d1,d1                   ; (groups - 1) * 4 in 4..76
        move.l  xy_tab-4(pc,d1.w),$e(a3); X_COUNT = groups (hi), Y_COUNT = 4 (lo) in one write!
        move.b  #$c0,$14(a3)            ; BUSY | HOG, line 0 (steps 0, 15, 14, 13)
        adda.w  #160,a1
        dbra    d7,.brow
        rts

rtab_in:
        dc.w    $8000,$c000,$e000,$f000,$f800,$fc00,$fe00,$ff00
        dc.w    $ff80,$ffc0,$ffe0,$fff0,$fff8,$fffc,$fffe,$ffff

yinc_tab:
        dc.w    -6,-14,-22,-30,-38,-46,-54,-62,-70,-78
        dc.w    -86,-94,-102,-110,-118,-126,-134,-142,-150

xy_tab:
        dc.w    2,4,3,4,4,4,5,4,6,4,7,4,8,4,9,4,10,4,11,4
        dc.w    12,4,13,4,14,4,15,4,16,4,17,4,18,4,19,4,20,4

; ---- One-time 68000 Blitter hardware probe (preserves d4-d7/a1-a4) ---------------------------------------------------
opt_probe:
        movem.l a1-a2,-(sp)
        move.w  sr,-(sp)
        ori.w   #$0700,sr
        moveq   #-1,d0                  ; default: no Blitter
        movea.l sp,a2
        movea.l $10.w,a1
        lea     .p68k(pc),a0
        move.l  a0,$10.w
        dc.w    $4e7a,$1002             ; movec cacr,d1: succeeds on 68020+, traps on 68000/68010
        move.l  a1,$10.w
        moveq   #-1,d0                  ; 68020+ -> CPU fast-span path
        bra.s   .pdone
.p68k:  movea.l a2,sp
        move.l  a1,$10.w
        movea.l $8.w,a1
        lea     .pberr(pc),a0
        move.l  a0,$8.w
        move.w  $ffff8a00.w,d1          ; HALFTONE[0]: bus error if no Blitter
        move.w  #$5aa5,$ffff8a00.w
        cmpi.w  #$5aa5,$ffff8a00.w
        bne.s   .pno
        move.w  #$a55a,$ffff8a00.w
        cmpi.w  #$a55a,$ffff8a00.w
        bne.s   .pno
        moveq   #1,d0                   ; 68000 + Blitter verified
        move.w  #$ffff,$ffff8a2a.w      ; ENDMASK2 = $ffff (constant)
        move.w  #8,$ffff8a2e.w          ; DST_XINC = 8 (constant)
        move.w  #$0103,$ffff8a3a.w      ; HOP = 1, OP = 3 (constant)
        clr.b   $ffff8a3d.w             ; SKEW = 0 (constant)
.pno:   move.w  d1,$ffff8a00.w
        bra.s   .pclr
.pberr: movea.l a2,sp
.pclr:  move.l  a1,$8.w
.pdone: move.w  (sp)+,sr
        movem.l (sp)+,a1-a2
        lea     opt_bflg(pc),a0
        move.b  d0,(a0)
        bgt.w   opt_blit
        bra.w   opt_cpu

opt_bflg:
        dc.b    0,0

col_tab:
        dc.l    $00000000,$00000000     ; 0
        dc.l    $ffff0000,$00000000     ; 1
        dc.l    $0000ffff,$00000000     ; 2
        dc.l    $ffffffff,$00000000     ; 3
        dc.l    $00000000,$ffff0000     ; 4
        dc.l    $ffff0000,$ffff0000     ; 5
        dc.l    $0000ffff,$ffff0000     ; 6
        dc.l    $ffffffff,$ffff0000     ; 7
        dc.l    $00000000,$0000ffff     ; 8
        dc.l    $ffff0000,$0000ffff     ; 9
        dc.l    $0000ffff,$0000ffff     ; 10
        dc.l    $ffffffff,$0000ffff     ; 11
        dc.l    $00000000,$ffffffff     ; 12
        dc.l    $ffff0000,$ffffffff     ; 13
        dc.l    $0000ffff,$ffffffff     ; 14
        dc.l    $ffffffff,$ffffffff     ; 15
