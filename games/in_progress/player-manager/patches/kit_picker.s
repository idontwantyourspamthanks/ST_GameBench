; ---------------------------------------------------------------------------
; Player Manager v1.1 — New Game Club Kit Picker (hooked at $010a34)
; Entered right after scr4.men "Done" with PM a4 = $02969a and club name at
; -$2e6e(a4). Allows choosing Style (0..5), Shirt Colour 1 (0..19), and Trim
; Colour 2 (0..19) via Mouse clicks OR Keyboard, with a live 48x52 jersey
; preview in exact Kick Off 2 ST RGB colours!
; Saves packed kit word to PM_HUM_KIT_OFF(a4) (-$24c8(a4), persisted in saves).
; ---------------------------------------------------------------------------

club_kit_picker:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)

        ; 2-step setup: step 0 = Home (1st) kit -> NEXT, step 1 = Away (2nd) kit -> DONE!
        clr.w   kp_step
        clr.w   kp_style                ; default Home: Plain Royal Blue & White
        move.w  #1,kp_col1
        move.w  #4,kp_col2

        ; Hide PM mouse cursor before clearing & drawing screen
        jsr     -$7f26(a4)

        ; Install clean PM-styled 16-colour palette
        pea     kp_pal(pc)
        move.w  #6,-(sp)                ; XBIOS Setpalette
        trap    #14
        addq.l  #6,sp

        ; Clear entire 320x200 screen ($078000, 32000 bytes) to col 0 (dark green $0020)
        lea     $078000.l,a0
        move.w  #(32000/4-1),d0
.kp_cl: clr.l   (a0)+
        dbra    d0,.kp_cl

        ; Draw header banner + club name + buttons (re-called on step 0 -> step 1!)
        bsr.w   kp_draw_chrome

        ; Left Jersey Preview Box (x=24..108, y=46..136)
        move.w  #24,d0
        move.w  #46,d1
        move.w  #84,d2
        move.w  #90,d3
        moveq   #4,d4                   ; rich pitch green
        bsr.w   kp_fill_box

        ; Row labels & static < / > arrow buttons for 3 rows (y=56, 86, 116)
        lea     $078000+47*160.l,a3
        lea     kp_lbl_st(pc),a0
        move.w  #122,d4
        moveq   #5,d0
        bsr.w   draw_mini_str

        lea     $078000+77*160.l,a3
        lea     kp_lbl_c1(pc),a0
        move.w  #122,d4
        moveq   #5,d0
        bsr.w   draw_mini_str

        lea     $078000+107*160.l,a3
        lea     kp_lbl_c2(pc),a0
        move.w  #122,d4
        moveq   #5,d0
        bsr.w   draw_mini_str

        ; Draw 3 pairs of < (x=122,w=18) and > (x=280,w=18) buttons at y=56, 86, 116
        move.w  #56,d6
        moveq   #2,d7
.kp_ab: move.w  #122,d0
        move.w  d6,d1
        moveq   #18,d2
        moveq   #16,d3
        moveq   #3,d4                   ; silver button
        bsr.w   kp_fill_box
        move.w  #280,d0
        move.w  d6,d1
        moveq   #18,d2
        moveq   #16,d3
        moveq   #3,d4
        bsr.w   kp_fill_box
        move.w  d6,d0
        addq.w  #5,d0
        mulu.w  #160,d0
        lea     $078000.l,a3
        adda.l  d0,a3
        lea     kp_lt_s(pc),a0
        move.w  #129,d4
        moveq   #2,d0                   ; black '<'
        bsr.w   draw_mini_str
        lea     kp_gt_s(pc),a0
        move.w  #287,d4
        moveq   #2,d0                   ; black '>'
        bsr.w   draw_mini_str
        addi.w  #30,d6
        dbra    d7,.kp_ab

        ; DONE/NEXT button drawn by kp_draw_chrome (updated when advancing Home -> Away!)

        ; Bottom control hint
        lea     $078000+184*160.l,a3
        lea     kp_hint_s(pc),a0
        moveq   #47,d4                  ; 45*5=225 -> (320-225)/2 = 47
        moveq   #1,d0
        bsr.w   draw_mini_str

        ; Initial live preview & value boxes draw
        bsr.w   kp_redraw_live
        jsr     -$7f20(a4)              ; show PM mouse cursor!

        ; Flush any stale click or key
        clr.w   -$3a24(a4)
.kp_fl: move.w  #$0b,-(sp)
        trap    #1
        addq.l  #2,sp
        tst.w   d0
        beq.w   .kp_loop
        move.w  #$08,-(sp)
        trap    #1
        addq.l  #2,sp
        bra.s   .kp_fl

; --- Main interactive loop (Mouse clicks + Keyboard) ---
.kp_loop:
        move.w  #$25,-(sp)              ; XBIOS Vsync
        trap    #14
        addq.l  #2,sp

        ; 1. Check PM mouse click (-$3a24(a4) != 0 and left btn -$3a26(a4) != 0)
        tst.w   -$3a24(a4)
        beq.s   .kp_key
        clr.w   -$3a24(a4)
        tst.w   -$3a26(a4)
        beq.s   .kp_key
        move.w  -$3a2e(a4),d0           ; mouse X (0..319)
        move.w  -$3a2c(a4),d1           ; mouse Y (0..199)

        ; Hit-test DONE button (x=112..208, y=150..170)
        cmpi.w  #150,d1
        blt.s   .kp_rows
        cmpi.w  #170,d1
        bgt.s   .kp_key
        cmpi.w  #112,d0
        blt.s   .kp_key
        cmpi.w  #208,d0
        ble.w   .kp_finish
        bra.s   .kp_key

.kp_rows:
        ; Check left/right X hit: '<' (120..142) => d2=-1, '>' (278..300) => d2=+1
        moveq   #-1,d2
        cmpi.w  #120,d0
        blt.s   .kp_key
        cmpi.w  #144,d0
        ble.s   .kp_gotx
        moveq   #1,d2
        cmpi.w  #276,d0
        blt.s   .kp_key
        cmpi.w  #300,d0
        bgt.s   .kp_key
.kp_gotx:
        ; Which row? Row 0 (Style: y=54..74), Row 1 (Shirt: y=84..104), Row 2 (Trim: y=114..134)
        cmpi.w  #54,d1
        blt.s   .kp_key
        cmpi.w  #74,d1
        ble.s   .kp_chg_st
        cmpi.w  #84,d1
        blt.s   .kp_key
        cmpi.w  #104,d1
        ble.s   .kp_chg_c1
        cmpi.w  #114,d1
        blt.s   .kp_key
        cmpi.w  #134,d1
        ble.s   .kp_chg_c2

.kp_key:
        move.w  #$0b,-(sp)              ; GEMDOS Cconis
        trap    #1
        addq.l  #2,sp
        tst.w   d0
        beq.w   .kp_loop
        move.w  #$08,-(sp)              ; GEMDOS Cnecin
        trap    #1
        addq.l  #2,sp
        cmpi.b  #' ',d0
        beq.w   .kp_finish
        cmpi.b  #$0d,d0
        beq.w   .kp_finish
        moveq   #1,d2
        cmpi.b  #'1',d0
        beq.s   .kp_chg_st
        cmpi.b  #'2',d0
        beq.s   .kp_chg_c1
        cmpi.b  #'3',d0
        beq.s   .kp_chg_c2
        bra.w   .kp_loop

.kp_chg_st:
        move.w  kp_style(pc),d0
        add.w   d2,d0
        bpl.s   .ks_hi
        moveq   #5,d0
.ks_hi: cmpi.w  #6,d0
        blt.s   .ks_sv
        moveq   #0,d0
.ks_sv: move.w  d0,kp_style
        bra.s   .kp_upd

.kp_chg_c1:
        move.w  kp_col1(pc),d0
        add.w   d2,d0
        bpl.s   .k1_hi
        moveq   #19,d0
.k1_hi: cmpi.w  #20,d0
        blt.s   .k1_sv
        moveq   #0,d0
.k1_sv: move.w  d0,kp_col1
        bra.s   .kp_upd

.kp_chg_c2:
        move.w  kp_col2(pc),d0
        add.w   d2,d0
        bpl.s   .k2_hi
        moveq   #19,d0
.k2_hi: cmpi.w  #20,d0
        blt.s   .k2_sv
        moveq   #0,d0
.k2_sv: move.w  d0,kp_col2

.kp_upd:
        jsr     -$7f26(a4)              ; hide mouse
        bsr.w   kp_redraw_live
        jsr     -$7f20(a4)              ; show mouse
        bra.w   .kp_loop

.kp_finish:
        jsr     -$7f26(a4)              ; hide mouse
        ; Pack kit word: $8000 | (style<<10) | (col1<<5) | col2
        move.w  kp_style(pc),d0
        lsl.w   #5,d0
        or.w    kp_col1(pc),d0
        lsl.w   #5,d0
        or.w    kp_col2(pc),d0
        ori.w   #$8000,d0
        tst.w   kp_step
        bne.s   .kp_save_away

        ; Step 0 finished: save Home (1st) kit, auto-pick contrasting default Away (2nd) kit, enter Step 1!
        move.w  d0,PM_HUM_KIT_OFF(a4)
        move.w  #1,kp_step
        clr.w   kp_style
        ; Choose a smart contrasting default Away kit based on Home's shirt colour family
        move.w  kp_col1(pc),d1
        lea     kit_family_tbl(pc),a0
        move.b  0(a0,d1.w),d1           ; 0=Blue,1=White/Grey,2=Black,3=Red,4=Yellow,5=Pink/Purp,6=Green
        cmpi.b  #4,d1                   ; Home is Yellow -> default Away = Royal Blue & White
        beq.s   .ka_blu
        cmpi.b  #1,d1                   ; Home is White/Grey -> default Away = Red & White
        beq.s   .ka_red
        ; Otherwise (Blue/Red/Black/Green/Purple) -> default Away = Yellow & Navy!
        move.w  #12,kp_col1             ; Yellow
        clr.w   kp_col2                 ; Navy
        bra.s   .ka_go
.ka_blu:
        move.w  #1,kp_col1              ; Royal Blue
        move.w  #4,kp_col2              ; White
        bra.s   .ka_go
.ka_red:
        move.w  #10,kp_col1             ; Red
        move.w  #4,kp_col2              ; White
.ka_go:
        bsr.s   kp_draw_chrome          ; update banner ("CHOOSE AWAY KIT (2ND)") & button ("DONE")!
        bsr.w   kp_redraw_live
        jsr     -$7f20(a4)              ; show mouse
        ; Wait brief debounce / clear click so NEXT click doesn't double-trigger DONE
        clr.w   -$3a24(a4)
        bra.w   .kp_loop

.kp_save_away:
        move.w  d0,PM_HUM_AWAY_OFF(a4)
        jsr     -$7f20(a4)              ; restore mouse visibility for PM!

        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        ; Execute displaced original instructions at $010a34..$010a3d
        movea.l -$2e74(a4),a5
        move.b  #$64,$7(a5)
        jmp     $010a3e.l

; ---------------------------------------------------------------------------
; Draw step-dependent header banner & NEXT/DONE button
; ---------------------------------------------------------------------------
kp_draw_chrome:
        movem.l d0-d4/a0/a3,-(sp)
        move.w  #8,d0
        move.w  #6,d1
        move.w  #304,d2
        move.w  #30,d3
        moveq   #4,d4                   ; pitch green banner fill
        bsr.w   kp_fill_box
        lea     $078000+11*160.l,a3
        lea     kp_title_h(pc),a0       ; "CHOOSE HOME KIT (1ST)" (21*5=105 -> x=107)
        tst.w   kp_step
        beq.s   .kdc_t
        lea     kp_title_a(pc),a0       ; "CHOOSE AWAY KIT (2ND)"
.kdc_t: moveq   #107,d4
        moveq   #5,d0                   ; gold
        bsr.w   draw_mini_str

        ; Draw chosen club name (-$2e6e(a4)) centred in white below title
        lea     -$2e6e(a4),a0
        moveq   #0,d4
.kdc_n: tst.b   (a0,d4.w)
        beq.s   .kdc_d
        addq.w  #1,d4
        cmpi.w  #20,d4
        blt.s   .kdc_n
.kdc_d: mulu.w  #5,d4
        neg.w   d4
        addi.w  #320,d4
        asr.w   #1,d4
        lea     $078000+23*160.l,a3
        lea     -$2e6e(a4),a0
        moveq   #1,d0                   ; crisp white
        bsr.w   draw_mini_str

        ; Bottom NEXT (step 0) / DONE (step 1) button (x=112..208, y=150..170)
        move.w  #112,d0
        move.w  #150,d1
        move.w  #96,d2
        move.w  #20,d3
        moveq   #7,d4                   ; bright green
        bsr.w   kp_fill_box
        lea     $078000+157*160.l,a3
        lea     kp_next_s(pc),a0        ; "NEXT: AWAY KIT" (14*5=70 -> x=125)
        moveq   #125,d4
        tst.w   kp_step
        beq.s   .kdc_b
        lea     kp_done_s(pc),a0        ; "DONE" (4*5=20 -> x=150)
        move.w  #150,d4
.kdc_b: moveq   #1,d0                   ; crisp white
        bsr.w   draw_mini_str
        movem.l (sp)+,d0-d4/a0/a3
        rts

; ---------------------------------------------------------------------------
; Redraw live palette slots 12 & 13, 3 value boxes, and 48x52 jersey preview!
; ---------------------------------------------------------------------------
kp_redraw_live:
        movem.l d0-d7/a0-a3,-(sp)
        ; 1. Update hardware palette col 12 = col1 RGB, col 13 = col2 RGB!
        lea     kp_rgb_tbl(pc),a0
        move.w  kp_col1(pc),d0
        add.w   d0,d0
        move.w  0(a0,d0.w),-(sp)
        move.w  #12,-(sp)
        move.w  #7,-(sp)                ; XBIOS Setcolor(12, rgb)
        trap    #14
        addq.l  #6,sp

        lea     kp_rgb_tbl(pc),a0
        move.w  kp_col2(pc),d0
        add.w   d0,d0
        move.w  0(a0,d0.w),-(sp)
        move.w  #13,-(sp)
        move.w  #7,-(sp)                ; XBIOS Setcolor(13, rgb)
        trap    #14
        addq.l  #6,sp

        ; 2. Redraw 3 value boxes (x=144..276, w=132, h=16 at y=56, 86, 116)
        ; Row 0: Style name
        move.w  #144,d0
        move.w  #56,d1
        move.w  #132,d2
        moveq   #16,d3
        moveq   #2,d4                   ; black box
        bsr.w   kp_fill_box
        move.w  kp_style(pc),d0
        mulu.w  #12,d0
        lea     kp_st_names(pc),a0
        adda.w  d0,a0
        lea     $078000+61*160.l,a3
        move.w  #154,d4
        moveq   #1,d0
        bsr.w   draw_mini_str

        ; Row 1: Shirt Col1 name + live colour swatch (col 12!)
        move.w  #144,d0
        move.w  #86,d1
        move.w  #132,d2
        moveq   #16,d3
        moveq   #2,d4
        bsr.w   kp_fill_box
        move.w  #148,d0
        move.w  #89,d1
        moveq   #14,d2
        moveq   #10,d3
        moveq   #12,d4                  ; live col1 swatch!
        bsr.w   kp_fill_rect
        move.w  kp_col1(pc),d0
        mulu.w  #12,d0
        lea     kp_col_names(pc),a0
        adda.w  d0,a0
        lea     $078000+91*160.l,a3
        move.w  #168,d4
        moveq   #1,d0
        bsr.w   draw_mini_str

        ; Row 2: Trim Col2 name + live colour swatch (col 13!)
        move.w  #144,d0
        move.w  #116,d1
        move.w  #132,d2
        moveq   #16,d3
        moveq   #2,d4
        bsr.w   kp_fill_box
        move.w  #148,d0
        move.w  #119,d1
        moveq   #14,d2
        moveq   #10,d3
        moveq   #13,d4                  ; live col2 swatch!
        bsr.w   kp_fill_rect
        move.w  kp_col2(pc),d0
        mulu.w  #12,d0
        lea     kp_col_names(pc),a0
        adda.w  d0,a0
        lea     $078000+121*160.l,a3
        move.w  #168,d4
        moveq   #1,d0
        bsr.w   draw_mini_str

        ; 3. Clear interior of Jersey Preview Box & draw big visual jersey + shorts!
        move.w  #26,d0
        move.w  #48,d1
        move.w  #80,d2
        move.w  #86,d3
        moveq   #4,d4
        bsr.w   kp_fill_rect

        ; Black outline behind jersey (sleeves x=38..94 y=57..75, torso x=48..84 y=57..99, shorts x=48..84 y=101..123)
        move.w  #37,d0
        move.w  #56,d1
        move.w  #58,d2
        move.w  #20,d3
        moveq   #2,d4
        bsr.w   kp_fill_rect
        move.w  #47,d0
        move.w  #56,d1
        move.w  #38,d2
        move.w  #44,d3
        moveq   #2,d4
        bsr.w   kp_fill_rect
        ; Base shirt fill in col 12 (primary col1)
        move.w  #39,d0
        move.w  #58,d1
        move.w  #54,d2
        move.w  #16,d3
        moveq   #12,d4
        bsr.w   kp_fill_rect
        move.w  #49,d0
        move.w  #58,d1
        move.w  #34,d2
        move.w  #40,d3
        moveq   #12,d4
        bsr.w   kp_fill_rect

        ; Style-specific secondary pattern (col 13) matching KO2's EXACT verified 6 styles (0..5)!
        move.w  kp_style(pc),d5
        beq.w   .kp_pat_done            ; Style 0: Plain shirt (col1) + col2 shorts
        cmpi.w  #1,d5
        beq.s   .kp_pat_stripes         ; Style 1: Vertical stripes
        cmpi.w  #2,d5
        beq.s   .kp_pat_band            ; Style 2: Chest band / hoop
        cmpi.w  #3,d5
        beq.s   .kp_pat_sleeves         ; Style 3: Contrasting sleeves
        cmpi.w  #4,d5
        beq.w   .kp_pat_yoke            ; Style 4: Contrasting shoulders/yoke (col1 top, col2 body)
        ; Style 5: Diagonal sash (top-right to bottom-left in col 13!)
        move.w  #75,d0                  ; start x
        move.w  #58,d1                  ; start y
        moveq   #6,d6                   ; 7 diagonal steps down torso
.ps_sa: moveq   #8,d2
        moveq   #6,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect
        subq.w  #4,d0
        addq.w  #5,d1
        dbra    d6,.ps_sa
        bra.w   .kp_pat_done

.kp_pat_stripes:
        ; 3 crisp vertical stripes in col 13 across torso (x=53, 63, 73, w=5)
        move.w  #53,d0
        moveq   #2,d6
.ps_lp: move.w  #58,d1
        moveq   #5,d2
        move.w  #40,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect
        addi.w  #10,d0
        dbra    d6,.ps_lp
        bra.s   .kp_pat_done

.kp_pat_band:
        ; Bold horizontal chest band in col 13 (matches KO2 style 2!)
        move.w  #49,d0
        move.w  #70,d1
        move.w  #34,d2
        moveq   #14,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect
        bra.s   .kp_pat_done

.kp_pat_sleeves:
        ; Left & right contrasting sleeves in col 13 (matches KO2 style 3!)
        move.w  #39,d0
        move.w  #58,d1
        moveq   #10,d2
        moveq   #16,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect
        move.w  #83,d0
        move.w  #58,d1
        moveq   #10,d2
        moveq   #16,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect
        bra.s   .kp_pat_done

.kp_pat_yoke:
        ; Lower torso body in col 13 leaving col 12 shoulders & sleeves (matches KO2 style 4!)
        move.w  #49,d0
        move.w  #72,d1
        move.w  #34,d2
        moveq   #26,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect

.kp_pat_done:
        ; Collar cutout (col 4 pitch green at top center x=61..70 y=56..61)
        move.w  #61,d0
        move.w  #56,d1
        moveq   #10,d2
        moveq   #5,d3
        moveq   #2,d4
        bsr.w   kp_fill_rect
        move.w  #62,d0
        move.w  #56,d1
        moveq   #8,d2
        moveq   #3,d3
        moveq   #4,d4
        bsr.w   kp_fill_rect

        ; Shorts below jersey (outlined in black col 2, filled in col 13 secondary colour!)
        move.w  #48,d0
        move.w  #101,d1
        move.w  #36,d2
        move.w  #22,d3
        moveq   #2,d4
        bsr.w   kp_fill_rect
        move.w  #50,d0
        move.w  #103,d1
        move.w  #32,d2
        move.w  #18,d3
        moveq   #13,d4
        bsr.w   kp_fill_rect
        ; Shorts leg split notch (x=64..67, y=114..122)
        move.w  #64,d0
        move.w  #114,d1
        moveq   #4,d2
        moveq   #9,d3
        moveq   #4,d4
        bsr.w   kp_fill_rect

        movem.l (sp)+,d0-d7/a0-a3
        rts

; ---------------------------------------------------------------------------
; Drawing primitives on $078000 (320x200 4bpp):
;   kp_fill_box(d0=x, d1=y, d2=w, d3=h, d4=col) : 1px white/black bevelled box
;   kp_fill_rect(d0=x, d1=y, d2=w, d3=h, d4=col): solid colour rectangle
; Preserves all registers!
; ---------------------------------------------------------------------------
kp_fill_box:
        movem.l d0-d4,-(sp)
        bsr.s   kp_fill_rect
        ; Top highlight (white col 1)
        movem.l (sp),d0-d4
        moveq   #1,d3
        moveq   #1,d4
        bsr.s   kp_fill_rect
        ; Left highlight (white col 1)
        movem.l (sp),d0-d4
        moveq   #1,d2
        moveq   #1,d4
        bsr.s   kp_fill_rect
        ; Bottom shadow (black col 2)
        movem.l (sp),d0-d4
        add.w   d3,d1
        subq.w  #1,d1
        moveq   #1,d3
        moveq   #2,d4
        bsr.s   kp_fill_rect
        ; Right shadow (black col 2)
        movem.l (sp),d0-d4
        add.w   d2,d0
        subq.w  #1,d0
        moveq   #1,d2
        moveq   #2,d4
        bsr.s   kp_fill_rect
        movem.l (sp)+,d0-d4
        rts

kp_fill_rect:
        movem.l d0-d7/a0-a3,-(sp)
        ; Fast 4bpp ST rectangle fill: d0=x, d1=y, d2=w, d3=h, d4=col (0..15)
        ; Uses word-stepped running bitmask (4x faster on 8 MHz 68000!)
        subq.w  #1,d3
        bmi.w   .fr_end
        tst.w   d2
        ble.w   .fr_end
        move.w  d1,d5
        mulu.w  #160,d5
        lea     $078000.l,a0
        adda.l  d5,a0
        ; Precompute start word offset (d0>>4)*8 -> a1, and start bitmask $8000>>(d0&15) -> a2
        move.w  d0,d7
        lsr.w   #4,d7
        lsl.w   #3,d7
        movea.w d7,a1                   ; start byte offset in row
        move.w  d0,d5
        andi.w  #15,d5
        move.w  #$8000,d1
        lsr.w   d5,d1
        movea.w d1,a2                   ; start bitmask
        ; Precompute 4-bit plane flags in d4 (bits 0..3)
.fr_y:  lea     (a0),a3
        adda.w  a1,a3                   ; a3 = current 4-plane word group
        move.w  a2,d1                   ; current bitmask
        move.w  d2,d6                   ; remaining pixels in row
        moveq   #0,d5                   ; accumulated mask for current 16px word
.fr_x:  or.w    d1,d5
        subq.w  #1,d6
        beq.w   .fr_fls
        lsr.w   #1,d1
        bne.s   .fr_x
        ; Flush full/partial 16px word (d5) in ONE shot across all 4 planes!
        move.w  d5,d7
        not.w   d7
        and.w   d7,(a3)
        and.w   d7,2(a3)
        and.w   d7,4(a3)
        and.w   d7,6(a3)
        btst    #0,d4
        beq.s   .fw1
        or.w    d5,(a3)
.fw1:   btst    #1,d4
        beq.s   .fw2
        or.w    d5,2(a3)
.fw2:   btst    #2,d4
        beq.s   .fw3
        or.w    d5,4(a3)
.fw3:   btst    #3,d4
        beq.s   .fwn
        or.w    d5,6(a3)
.fwn:   addq.l  #8,a3
        move.w  #$8000,d1
        moveq   #0,d5
        ; Fast-path: if remaining d6 >= 16, write whole 16px words directly!
        cmpi.w  #16,d6
        blt.s   .fr_x
        moveq   #-1,d5
        subi.w  #16,d6
        beq.s   .fr_fls
        ; Flush full word $ffff
        clr.w   (a3)
        clr.w   2(a3)
        clr.w   4(a3)
        clr.w   6(a3)
        btst    #0,d4
        beq.s   .ff1
        move.w  d5,(a3)
.ff1:   btst    #1,d4
        beq.s   .ff2
        move.w  d5,2(a3)
.ff2:   btst    #2,d4
        beq.s   .ff3
        move.w  d5,4(a3)
.ff3:   btst    #3,d4
        beq.s   .ffn
        move.w  d5,6(a3)
.ffn:   addq.l  #8,a3
        moveq   #0,d5
        bra.w   .fr_x
.fr_fls:
        move.w  d5,d7
        not.w   d7
        and.w   d7,(a3)
        and.w   d7,2(a3)
        and.w   d7,4(a3)
        and.w   d7,6(a3)
        btst    #0,d4
        beq.s   .fl1
        or.w    d5,(a3)
.fl1:   btst    #1,d4
        beq.s   .fl2
        or.w    d5,2(a3)
.fl2:   btst    #2,d4
        beq.s   .fl3
        or.w    d5,4(a3)
.fl3:   btst    #3,d4
        beq.s   .fr_ny
        or.w    d5,6(a3)
.fr_ny: lea     160(a0),a0
        dbra    d3,.fr_y
.fr_end:
        movem.l (sp)+,d0-d7/a0-a3
        rts

; --- Kit Picker Data ---
kp_step:        dc.w    0               ; 0 = Home (1st) kit, 1 = Away (2nd) kit
kp_style:       dc.w    0
kp_col1:        dc.w    1
kp_col2:        dc.w    4

kp_pal:
        dc.w    $0020,$0777,$0000,$0555,$0040,$0760,$0333,$0060
        dc.w    $0777,$0000,$0444,$0222,$0007,$0777,$0777,$0000

; Exact Kick Off 2 20-colour ST RGB palette (matches KO2 -$78fc(a4)!)
kp_rgb_tbl:
        dc.w    $0005,$0007,$0047,$0077,$0777,$0555,$0444,$0000
        dc.w    $0300,$0500,$0700,$0730,$0770,$0747,$0707,$0307
        dc.w    $0030,$0050,$0245,$0043

kp_title_h:     dc.b    "CHOOSE HOME KIT (1ST)",0
kp_title_a:     dc.b    "CHOOSE AWAY KIT (2ND)",0
kp_lbl_st:      dc.b    "KIT STYLE",0
kp_lbl_c1:      dc.b    "SHIRT COLOUR",0
kp_lbl_c2:      dc.b    "TRIM / SHORTS",0
kp_lt_s:        dc.b    "<",0
kp_gt_s:        dc.b    ">",0
kp_next_s:      dc.b    "NEXT: AWAY KIT",0
kp_done_s:      dc.b    "DONE",0
kp_hint_s:      dc.b    "CLICK ARROWS OR KEYS 1-3  -  SPACE TO CONFIRM",0

; Fixed 12-byte stride style names (0..5, verified 1-to-1 against Kick Off 2!)
kp_st_names:
        dc.b    "PLAIN      ",0
        dc.b    "STRIPES    ",0
        dc.b    "CHEST BAND ",0
        dc.b    "SLEEVES    ",0
        dc.b    "SHOULDERS  ",0
        dc.b    "SASH       ",0

; Fixed 12-byte stride colour names (0..19)
kp_col_names:
        dc.b    "NAVY BLUE  ",0
        dc.b    "ROYAL BLUE ",0
        dc.b    "SKY BLUE   ",0
        dc.b    "CYAN       ",0
        dc.b    "WHITE      ",0
        dc.b    "LIGHT GREY ",0
        dc.b    "DARK GREY  ",0
        dc.b    "BLACK      ",0
        dc.b    "CLARET     ",0
        dc.b    "DARK RED   ",0
        dc.b    "RED        ",0
        dc.b    "ORANGE     ",0
        dc.b    "YELLOW     ",0
        dc.b    "PINK       ",0
        dc.b    "MAGENTA    ",0
        dc.b    "PURPLE     ",0
        dc.b    "DARK GREEN ",0
        dc.b    "GREEN      ",0
        dc.b    "SLATE BLUE ",0
        dc.b    "TEAL       ",0
        even
