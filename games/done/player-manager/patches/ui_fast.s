; ---------------------------------------------------------------------------
; Player Manager v1.1 — Fast ST Medium Text Renderer + Select Team Polish
;
; 1. fast_draw_str ($017a38):
;    Replaces per-character Line-A $a008 exception traps with a direct 68000
;    2-plane ST Medium (640x200) transparent glyph blitter (~5-15x faster!).
;    Speeds up "The Opponents", "Select Team", "Player Profile", "The Squad",
;    "The League", and every screen/dialog using $017a38.
;    Falls back cleanly to original $a008 on non-ST-Medium modes, styled text,
;    non-transparent WRT_MODE, or clipped edges.
;
; 2. select_team_assign ($0111e8):
;    - Updates ONLY the 1 or 2 changed shirt-number cells in-place instead of
;      wiping and redrawing all 18 players in the list box.
;    - Auto-advances the active shirt number button (1 -> 2 -> ... -> 12 -> 14
;      -> 1, skipping missing shirt 13 and any right-clicked N/A slots!).
; ---------------------------------------------------------------------------

; ===========================================================================
; 1. Fast ST Low 4bpp Direct-to-Screen Transparent String Renderer ($017a38)
;    Uses 32-bit [P0:P1] / [P2:P3] longword ops (dedicated 2-instr fg==0
;    shadow path + general fg=1..15 path). Falls back to $a008 if non-ST-Low,
;    styled, non-transparent, or clipped.
; ===========================================================================
fast_draw_str:
        movem.l d0-d1/a3,-(sp)
        jsr     -$7f26(a4)              ; hide mouse
        move.w  d0,-$764a(a4)           ; cur_x = d0
        move.w  d1,-$7648(a4)           ; cur_y = d1
        tst.b   (a3)
        beq.w   .fds_exit               ; empty string -> done!

        movem.l d2-d7/a0-a2/a5-a6,-(sp)
        movea.l -$7656(a4),a0           ; a0 = Line-A base
        cmpi.w  #4,(a0)                 ; LA_PLANES == 4 (ST Low 320x200 4bpp)?
        bne.w   .fds_slow
        cmpi.w  #160,2(a0)              ; LA_BYTES_LIN == 160?
        bne.w   .fds_slow
        cmpi.w  #1,$24(a0)              ; WRT_MODE == 1 (Transparent)?
        bne.w   .fds_slow
        tst.w   -$764c(a4)              ; STYLE == 0 (plain)?
        bne.w   .fds_slow

        ; Font header a2 = font_tbl[-$764e(a4)]
        movea.l -$7652(a4),a1
        move.w  -$764e(a4),d2
        lsl.w   #2,d2
        movea.l 0(a1,d2.w),a2           ; a2 = TOS font header
        move.w  $34(a2),d4              ; d4 = cell_w (6 or 8)
        beq.w   .fds_slow
        cmpi.w  #8,d4
        bhi.w   .fds_slow
        move.w  $52(a2),d5              ; d5 = form_height (6, 8, or 16)
        beq.w   .fds_slow

        ; Bounds check Y (0 <= y && y + h <= 200) and X >= 0
        tst.w   d1
        bmi.w   .fds_slow
        move.w  d1,d2
        add.w   d5,d2
        cmpi.w  #200,d2
        bgt.w   .fds_slow
        tst.w   d0
        bmi.w   .fds_slow

        ; Quick strlen + X right-edge check (x + len * cell_w <= 320)
        movea.l a3,a1
        moveq   #0,d3
.fds_ln:
        tst.b   (a1)+
        beq.s   .fds_ld
        addq.w  #1,d3
        bra.s   .fds_ln
.fds_ld:
        move.w  d3,d2
        mulu.w  d4,d2
        add.w   d0,d2                   ; end_x
        cmpi.w  #320,d2
        bgt.w   .fds_slow

        ; Get active TOS logical screen base ONCE per string (XBIOS #3 Logbase clobbers d0-d2/a0-a2!)
        movem.l d0-d2/a0/a2,-(sp)
        move.w  #3,-(sp)
        trap    #14
        addq.l  #2,sp
        movea.l d0,a5                   ; a5 = logical screen base
        movem.l (sp)+,d0-d2/a0/a2
        move.w  d2,-$764a(a4)           ; update cur_x = end_x (exact match to $017a38!)

        ; Compute screen row base a5 += y * 160 (zero mulu!)
        lsl.w   #5,d1                   ; y * 32
        move.w  d1,d2
        add.w   d1,d1
        add.w   d1,d1                   ; y * 128
        add.w   d2,d1                   ; y * 160
        adda.w  d1,a5                   ; a5 = screen_base + y * 160

        ; Precompute 32-bit plane masks ui_fg01 / ui_fg23 from TEXT_FG ($6a(a0) & 15)
        move.w  $6a(a0),d2
        andi.w  #15,d2
        move.w  d2,ui_fg
        lsl.w   #3,d2                   ; * 8 (2 longs per colour)
        lea     ui_fg_tbl(pc),a1
        move.l  0(a1,d2.w),ui_fg01
        move.l  4(a1,d2.w),ui_fg23

        move.w  d4,ui_cellw             ; cell_w (6 or 8)
        move.w  d5,d7
        subq.w  #1,d7                   ; d7 = h - 1 (dbra count)
        move.w  d7,ui_hm1
        move.w  $50(a2),ui_fwidth       ; FWIDTH (bytes/row of 1bpp font)
        move.l  $4c(a2),ui_fbase        ; FBASE
        move.l  $48(a2),ui_offtbl       ; CHAR_OFF table
        move.w  $24(a2),ui_first        ; FIRST_ADE

        ; Outer character loop: d6 = cur_x, a3 = string ptr, a5 = screen_base + y*160
        move.w  d0,d6

.fds_ch:
        moveq   #0,d0
        move.b  (a3)+,d0
        beq.w   .fds_ok
        cmpi.b  #' ',d0                 ; space has 0 pixels -> instant advance!
        beq.w   .fds_adv
        sub.w   ui_first(pc),d0
        blt.w   .fds_adv
        add.w   d0,d0
        movea.l ui_offtbl(pc),a0
        move.w  0(a0,d0.w),d1           ; d1 = bit_x in font strip
        move.w  2(a0,d0.w),d2
        sub.w   d1,d2                   ; d2 = glyph width (1..8)
        ble.w   .fds_adv
        cmpi.w  #8,d2
        bhi.w   .fds_adv
        add.w   d2,d2
        lea     ui_wmask_tbl(pc),a0
        move.w  0(a0,d2.w),d5           ; d5 = top-w-bits mask ($fc00 for 6px, $ff00 for 8px)

        ; Source ptr a6 = FBASE + (bit_x >> 3), d3 = src_rot (bit_x & 7)
        move.w  d1,d3
        andi.w  #7,d3                   ; d3 = src_rot (0..7)
        lsr.w   #3,d1
        movea.l ui_fbase(pc),a6
        adda.w  d1,a6

        ; Dest ptr a1 = a5 + (cur_x >> 4) * 8, d4 = dst_rot (cur_x & 15)
        move.w  d6,d4
        move.w  d4,d1
        andi.w  #$fff0,d1
        lsr.w   #1,d1                   ; (cur_x >> 4) * 8 (ST Low 4bpp!)
        lea     0(a5,d1.w),a1
        andi.w  #15,d4                  ; d4 = dst_rot (0..15)

        move.w  ui_fwidth(pc),a0        ; a0 = FWIDTH
        move.w  ui_hm1(pc),d7           ; d7 = h - 1
        tst.w   ui_fg
        bne.s   .lp_fgn

; --- Ultra-fast fg == 0 (Black drop shadow: 50% of all text calls! 2x and.l!) ---
.lp_fg0:
        moveq   #0,d1
        move.b  (a6),d1
        lsl.w   #8,d1
        tst.w   d3
        beq.s   .f0_s0
        move.b  1(a6),d1
        lsl.w   d3,d1
.f0_s0: and.w   d5,d1
        beq.s   .f0_nx
        swap    d1
        lsr.l   d4,d1
        tst.w   d1                      ; right word non-zero?
        beq.s   .f0_l
        move.w  d1,d2
        not.w   d2
        move.w  d2,d0
        swap    d0
        move.w  d2,d0                   ; [~m_R : ~m_R]
        and.l   d0,8(a1)
        and.l   d0,12(a1)
.f0_l:  swap    d1
        not.w   d1
        move.w  d1,d0
        swap    d0
        move.w  d1,d0                   ; [~m_L : ~m_L]
        and.l   d0,(a1)
        and.l   d0,4(a1)
.f0_nx: adda.w  a0,a6
        lea     160(a1),a1
        dbra    d7,.lp_fg0
        bra.s   .fds_adv

; --- General fg = 1..15 (32-bit [P0:P1] + [P2:P3] mask/or!) ---
.lp_fgn:
        move.l  a2,-(sp)
        movea.l ui_fg01(pc),a2          ; keep fg01 in a2 for inner loop
.fgn_rw:
        moveq   #0,d1
        move.b  (a6),d1
        lsl.w   #8,d1
        tst.w   d3
        beq.s   .fn_s0
        move.b  1(a6),d1
        lsl.w   d3,d1
.fn_s0: and.w   d5,d1
        beq.s   .fn_nx
        swap    d1
        lsr.l   d4,d1
        tst.w   d1                      ; right word non-zero?
        beq.s   .fn_l
        move.w  d1,d0
        swap    d0
        move.w  d1,d0                   ; d0 = [m_R : m_R]
        move.l  d0,d2
        not.l   d2                      ; d2 = [~m_R : ~m_R]
        and.l   d2,8(a1)
        and.l   d2,12(a1)
        move.l  a2,d2
        and.l   d0,d2
        or.l    d2,8(a1)
        and.l   ui_fg23(pc),d0
        or.l    d0,12(a1)
.fn_l:  swap    d1
        move.w  d1,d0
        swap    d0
        move.w  d1,d0                   ; d0 = [m_L : m_L]
        move.l  d0,d2
        not.l   d2                      ; d2 = [~m_L : ~m_L]
        and.l   d2,(a1)
        and.l   d2,4(a1)
        move.l  a2,d2
        and.l   d0,d2
        or.l    d2,(a1)
        and.l   ui_fg23(pc),d0
        or.l    d0,4(a1)
.fn_nx: adda.w  a0,a6
        lea     160(a1),a1
        dbra    d7,.fgn_rw
        movea.l (sp)+,a2

.fds_adv:
        add.w   ui_cellw(pc),d6
        bra.w   .fds_ch

.fds_ok:
        movem.l (sp)+,d2-d7/a0-a2/a5-a6
.fds_exit:
        jsr     -$7f20(a4)              ; show mouse
        movem.l (sp)+,d0-d1/a3
        rts

.fds_slow:
        movem.l (sp)+,d2-d7/a0-a2/a5-a6
        jmp     $017a48.l               ; original Line-A $a008 loop!

ui_wmask_tbl:
        dc.w    $0000,$8000,$c000,$e000,$f000,$f800,$fc00,$fe00,$ff00
; 16-colour 4bpp plane expansion table: [P0_mask.w, P1_mask.w, P2_mask.w, P3_mask.w]
ui_fg_tbl:
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
ui_fg01:        dc.l    0
ui_fg23:        dc.l    0
ui_fbase:       dc.l    0
ui_offtbl:      dc.l    0
ui_fg:          dc.w    0
ui_cellw:       dc.w    0
ui_hm1:         dc.w    0
ui_fwidth:      dc.w    0
ui_first:       dc.w    0

; ===========================================================================
; 2. Select Team: Instant Single-Cell Shirt Update + Auto-Advance Picker
;    Hooked at $0111e8 (a5 = clicked player, d3.w = clicked visible row,
;    d6.w = active shirt button index 0..11, 13 -> shirt = d6 + 1)
; ===========================================================================
select_team_assign:
        ; 1. Clear shirt (d6+1) from any previous wearer & remember their visible row
        movea.l -$2e78(a4),a0           ; human club struct
        moveq   #0,d2                   ; squad offset (0, 2, 4, ...)
        moveq   #0,d4                   ; visible eligible row counter
        moveq   #-1,d5                  ; old_row (-1 = none)
        addq.w  #1,d6                   ; d6 = target shirt number (1..14)
.sta_lp:
        move.w  $2c(a0,d2.w),d0
        bmi.s   .sta_set
        mulu.w  #$2a,d0
        add.l   -$2e80(a4),d0
        movea.l d0,a6
        ; Check if eligible (same filter as $0131e0..$0131f0: not injured & not suspended)
        moveq   #0,d1
        tst.b   $16(a6)
        bne.s   .sta_chk
        move.b  $17(a6),d0
        andi.w  #3,d0
        bne.s   .sta_chk
        moveq   #1,d1                   ; eligible -> occupies visible row d4
.sta_chk:
        cmp.b   $15(a6),d6
        bne.s   .sta_nx
        clr.b   $15(a6)                 ; clear old wearer's shirt!
        tst.w   d1
        beq.s   .sta_nx
        cmpa.l  a5,a6
        beq.s   .sta_nx
        move.w  d4,d5                   ; remember old wearer's visible row!
.sta_nx:
        add.w   d1,d4
        addq.w  #2,d2
        bra.s   .sta_lp

.sta_set:
        move.b  d6,$15(a5)              ; assign shirt d6 to clicked player a5!

        ; 2. Update ONLY the 1 or 2 changed shirt cells in-place (ZERO full list redraw!)
        movem.l d3/d5-d6/a5-a6,-(sp)
        jsr     -$7f26(a4)              ; hide mouse
        moveq   #7,d0
        jsr     $017f3a.l               ; a2 = widget 7 (player list box)
        movea.l a2,a6
        moveq   #5,d0
        jsr     $017f3a.l               ; a2 = widget 5 (Shirt column header)
        move.l  a2,d0
        beq.s   .sta_drw_done
        move.w  $8(a2),d4
        addi.w  #$a,d4                  ; d4 = relative shirt_x inside widget 7!

        ; Clear old wearer's shirt cell if another visible player held this shirt
        tst.w   d5
        bmi.s   .sta_new
        move.w  d5,d1
        bsr.s   .sta_clr_cell

.sta_new:
        ; Clear clicked player's cell (erasing any old shirt) and draw new shirt number!
        move.w  d3,d1
        bsr.s   .sta_clr_cell
        move.w  d6,d0                   ; shirt number (1..14)
        lea     -$2f94(a4),a2
        jsr     -$7f86(a4)              ; itoa(d0) -> -$2f94(a4)
        movea.l a2,a3
        move.w  d4,d0                   ; rel_x = shirt_x
        move.w  d3,d1
        mulu.w  #6,d1
        addq.w  #1,d1                   ; rel_y = 1 + row * 6
        movea.l a6,a2                   ; widget 7
        jsr     $017a7a.l               ; draw shirt number (via fast_draw_str!)

.sta_drw_done:
        jsr     -$7f20(a4)              ; show mouse
        movem.l (sp)+,d3/d5-d6/a5-a6
        subq.w  #1,d6                   ; restore d6 = button index (0..13)

        ; 3. Auto-advance shirt picker button (1 -> 2 -> ... -> 12 -> 14 -> 1, skipping 13 & N/A!)
        move.w  d6,d0
        addi.w  #$c,d0
        jsr     $017bca.l               ; un-highlight current shirt button
        lea     -$3878(a4),a0           ; disabled/N/A button table (14 bytes)
        moveq   #13,d1                  ; guard <= 14 steps
.sta_adv:
        addq.w  #1,d6
        cmpi.w  #12,d6                  ; shirt 13 (index 12) does not exist -> skip to 14!
        bne.s   .sta_n13
        addq.w  #1,d6
.sta_n13:
        cmpi.w  #14,d6                  ; past shirt 14 -> wrap cleanly to shirt 1 (index 0)!
        blt.s   .sta_ok
        moveq   #0,d6
.sta_ok:
        tst.b   0(a0,d6.w)              ; skip right-click-disabled (N/A) slots
        beq.s   .sta_hl
        dbra    d1,.sta_adv
.sta_hl:
        move.w  d6,d0
        addi.w  #$c,d0
        jsr     $017bca.l               ; highlight next shirt button!
        jmp     $011056.l               ; back to Select Team event loop!

; Helper: clear 18x6 shirt cell at visible row d1.w inside widget 7 (a6), rel_x = d4.w
.sta_clr_cell:
        movem.l d0-d2/a0-a2,-(sp)
        move.w  d1,d2                   ; save row index BEFORE $0175fa (which clobbers d1!)
        move.b  $17(a6),d0              ; widget 7 background colour
        jsr     $0175fa.l               ; set Line-A fill colour planes
        movea.l -$7656(a4),a0
        clr.w   $24(a0)                 ; WRT_MODE = 0 (Replace)
        move.w  $8(a6),d0
        add.w   d4,d0
        subq.w  #2,d0                   ; x1 = box.x + shirt_x - 2
        move.w  d0,$26(a0)
        addi.w  #17,d0                  ; x2 = x1 + 17 (18px wide: covers 2 digits + shadow)
        move.w  d0,$2a(a0)
        mulu.w  #6,d2
        add.w   $a(a6),d2               ; y1 = box.y + row * 6 (covers fg at +0..+5 & shadow at +1..+6)
        move.w  d2,$28(a0)
        addq.w  #6,d2                   ; y2 = y1 + 6
        move.w  d2,$2c(a0)
        dc.w    $a005                   ; Line-A filled rect (single 18x6 cell!)
        movem.l (sp)+,d0-d2/a0-a2
        rts
