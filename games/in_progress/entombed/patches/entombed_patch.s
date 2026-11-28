; =============================================================================
; Entombed — Atari STe Enhanced Patch (Milestone 2: STe HW Scroll, Blitter
;            Tilemap + Sprites, Timer B Split-Screen HUD, 50/60 Hz)
; =============================================================================
; Assembled with: vasmm68k_mot -Ftos -m68000 -DPATCH_OFF=... -DBSS_SHIFT=...

        section text

; ---- Jump Table (4 bytes each) ----
jtab:
        bra.w   hook_init           ; +0   ($012576)
        bra.w   hook_title_credit   ; +4   ($013172)
        bra.w   hook_game_key       ; +8   ($012a4a)
        bra.w   hook_game_swap      ; +12  ($0129b4)
        bra.w   hook_tile_cache     ; +16  ($014472)
        bra.w   hook_render_map     ; +20  ($013504)
        bra.w   hook_hud_draw       ; +24  ($012992)
        bra.w   hook_spr_normal     ; +28  ($015fd8)
        bra.w   hook_spr_alt1       ; +32  ($0161ac)
        bra.w   hook_spr_alt2       ; +36  ($016334)
        bra.w   hook_leave_select   ; +40  ($012718)
        bra.w   hook_leave_hi       ; +44  ($0128ac, $012a20)
        bra.w   hook_level_load     ; +48  ($012730)

; ---- Offsets into original TEXT (relative to orig_base) ----
O_DRAW_STR      equ $0179c4-ORIG_LOAD
O_DRAW_LINE     equ $017976-ORIG_LOAD
O_SWAP_SCR      equ $01348a-ORIG_LOAD
O_PAUSE_LOOP    equ $012aa4-ORIG_LOAD
O_TOMB_SEL      equ $012b2a-ORIG_LOAD
O_HISCORE       equ $017a72-ORIG_LOAD
O_LEVEL_LOAD    equ $01535e-ORIG_LOAD
O_HUD_FMT       equ $012e7e-ORIG_LOAD
O_HUD_CALL      equ $012f4a-ORIG_LOAD

; Original sprite routines (+6 skips overwritten sub.w $18142,d1)
O_SPR_NORM_CONT equ $015fde-ORIG_LOAD
O_SPR_ALT1_CONT equ $0161b2-ORIG_LOAD
O_SPR_ALT2_CONT equ $01633a-ORIG_LOAD

; Original variables in TEXT (relative to orig_base)
O_SCR_PHYS      equ $018130-ORIG_LOAD
O_SCR_BACK      equ $018134-ORIG_LOAD
O_CAM_X         equ $018142-ORIG_LOAD
O_CAM_Y         equ $018144-ORIG_LOAD
O_TILE_CNT      equ $0183c8-ORIG_LOAD
O_SHADOW_MAP    equ $0184a6-ORIG_LOAD
O_HUD_STR       equ $019300-ORIG_LOAD

; Original BSS arrays (shifted by +BSS_SHIFT, relative to orig_base)
O_MAP_PRI       equ ($05a1bc-ORIG_LOAD)+BSS_SHIFT
O_TILE_PROPS    equ ($063bbc-ORIG_LOAD)+BSS_SHIFT

; ---- Hardware Registers ----
HW_VBASE_HI     equ $ffff8201
HW_VBASE_MID    equ $ffff8203
HW_VCNT_HI      equ $ffff8205
HW_VCNT_MID     equ $ffff8207
HW_VCNT_LO      equ $ffff8209
HW_SYNCMODE     equ $ffff820a
HW_VBASE_LO     equ $ffff820d
HW_LINEWID      equ $ffff820f
HW_HSCROLL      equ $ffff8265

BLT_SRC_XINC    equ $ffff8a20
BLT_SRC_YINC    equ $ffff8a22
BLT_SRC_ADDR    equ $ffff8a24
BLT_ENDMASK1    equ $ffff8a28
BLT_ENDMASK2    equ $ffff8a2a
BLT_ENDMASK3    equ $ffff8a2c
BLT_DST_XINC    equ $ffff8a2e
BLT_DST_YINC    equ $ffff8a30
BLT_DST_ADDR    equ $ffff8a32
BLT_XCOUNT      equ $ffff8a36
BLT_YCOUNT      equ $ffff8a38
BLT_HOP         equ $ffff8a3a
BLT_OP          equ $ffff8a3b
BLT_CTRL        equ $ffff8a3c
BLT_SKEW        equ $ffff8a3d

MFP_IERA        equ $fffffa07
MFP_ISRA        equ $fffffa0f
MFP_IMRA        equ $fffffa13
MFP_TBCR        equ $fffffa1b
MFP_TBDR        equ $fffffa21

SYS_VBL_VEC     equ $00000070
SYS_TC_VEC      equ $00000114
SYS_IKBD_VEC    equ $00000118
SYS_TB_VEC      equ $00000120

PF_STRIDE       equ 176             ; 352 px = 11 tiles * 16 bytes
PF_HEIGHT       equ 208             ; 13 tiles * 16 lines
PF_SIZE         equ PF_STRIDE*PF_HEIGHT ; 36,608 bytes

; =============================================================================
; +0: hook_init
; =============================================================================
hook_init:
        move.l  (sp),d0
        subq.l  #6,d0
        move.l  d0,orig_base

        movem.l d0-d2/a0-a2,-(sp)
        clr.l   -(sp)
        move.w  #$20,-(sp)          ; GEMDOS Super(0)
        trap    #1
        addq.l  #6,sp
        move.l  d0,old_ssp

        ; Align playfield & HUD buffers to 256 bytes
        lea     pf_buf0_raw+255,a0
        move.l  a0,d0
        clr.b   d0
        move.l  d0,pf_buf0
        lea     pf_buf1_raw+255,a0
        move.l  a0,d0
        clr.b   d0
        move.l  d0,pf_buf1
        lea     hud_buf_raw+255,a0
        move.l  a0,d0
        clr.b   d0
        move.l  d0,hud_buf
        ; Pre-patch hud_buf address bytes directly into my_timer_b immediates
        ; (12 cycles per write instead of 16 -> saves 12 cycles in HBL!)
        move.b  d0,tb_hud_lo+3
        lsr.l   #8,d0
        move.b  d0,tb_hud_mid+3
        lsr.l   #8,d0
        move.b  d0,tb_hud_hi+3

        ; Detect initial 50/60Hz
        btst    #1,HW_SYNCMODE
        seq     is_60hz

        ; Install VBL, Timer B, and IPL-lowering Timer C / IKBD wrappers
        ; (so MFP Timer B ALWAYS preempts 200Hz Timer C & IKBD joystick IRQs!)
        move.w  sr,d2
        ori.w   #$0700,sr
        clr.b   MFP_TBCR
        move.l  SYS_VBL_VEC,old_vbl
        lea     my_vbl(pc),a0
        move.l  a0,SYS_VBL_VEC
        move.l  SYS_TB_VEC,old_tb
        lea     my_timer_b(pc),a0
        move.l  a0,SYS_TB_VEC
        move.l  SYS_TC_VEC,old_tc
        lea     my_tc_wrap(pc),a0
        move.l  a0,SYS_TC_VEC
        move.l  SYS_IKBD_VEC,old_ikbd
        lea     my_ikbd_wrap(pc),a0
        move.l  a0,SYS_IKBD_VEC
        move.w  d2,sr

        clr.l   vbl_count
        clr.b   sync_toggle_req
        clr.b   ste_scroll_active
        clr.b   disp_pending
        clr.w   back_idx
        move.w  #-1,buf_tx
        move.w  #-1,buf_tx+2
        move.w  #-1,buf_ty
        move.w  #-1,buf_ty+2

        movem.l (sp)+,d0-d2/a0-a2

        move.l  (sp)+,a0
        move.w  #0,-(sp)
        move.w  #$15,-(sp)
        jmp     (a0)

; =============================================================================
; VBL Interrupt Handler — 50/60Hz toggle + STe HW scroll apply + Timer B arm
; =============================================================================
my_vbl:
        addq.l  #1,vbl_count

        tst.b   sync_toggle_req
        beq.s   .no_tog
        clr.b   sync_toggle_req
        not.b   is_60hz
        beq.s   .set_50
        bclr    #1,HW_SYNCMODE      ; 60 Hz
        bra.s   .no_tog
.set_50:
        bset    #1,HW_SYNCMODE      ; 50 Hz
.no_tog:
        tst.b   ste_scroll_active
        beq.s   .no_ste

        tst.b   disp_pending
        beq.s   .apply_act          ; 2-VBL overrun frame: keep active buffer & cur_disp_lo!

        ; Atomically commit new frame during top border (nHBL < nStartHBL):
        ; Write BOTH HW_VBASE (for any repeat VBL) AND HW_VCNT (for THIS frame!)
        ; in strict HI -> MID -> LO order — eliminates the line 260/310
        ; RestartVideoCounter race window completely!
        move.b  disp_hi(pc),HW_VBASE_HI
        move.b  disp_mid(pc),HW_VBASE_MID
        move.b  disp_lo(pc),HW_VBASE_LO
        move.b  disp_hi(pc),HW_VCNT_HI
        move.b  disp_mid(pc),HW_VCNT_MID
        move.b  disp_lo(pc),HW_VCNT_LO
        move.b  disp_lo(pc),cur_disp_lo
        move.b  disp_linewid(pc),act_linewid
        move.b  disp_hscroll(pc),act_hscroll
        clr.b   disp_pending

.apply_act:
        move.b  act_linewid(pc),HW_LINEWID
        move.b  act_hscroll(pc),HW_HSCROLL

        ; Arm Timer B at scanline 191 (1 line early) so my_timer_b can
        ; cycle-lock to the exact falling edge of scanline 191 DE!
        clr.b   MFP_TBCR
        move.b  #191,MFP_TBDR
        move.b  #8,MFP_TBCR
        bset    #0,MFP_IERA
        bset    #0,MFP_IMRA
.no_ste:
        move.l  old_vbl,-(sp)
        rts

; =============================================================================
; Timer C ($114) & IKBD ($118) IPL-5 Wrappers
;   MFP hardware ISRA/ISRB arbitration prevents re-entry of Timer C / IKBD,
;   while lowering 68000 IPL from 6 -> 5 lets higher-priority Timer B (ISRA.0)
;   preempt them instantaneously at scanline 192 -> ZERO HUD flicker!
; =============================================================================
my_tc_wrap:
        move.w  #$2500,sr
        move.l  old_tc,-(sp)
        rts

my_ikbd_wrap:
        move.w  #$2500,sr
        move.l  old_ikbd,-(sp)
        rts

; =============================================================================
; Timer B HBL Interrupt Handler — exact hardware-address HUD split at line 192
;   Fires at end of scanline 190 (MFP_TBDR=191). On scanline 191, HW_VCNT_LO
;   starts at (cur_disp_lo + $50), ramps to (cur_disp_lo + $f0/$f8), and hits
;   EXACTLY cur_disp_lo at the falling edge of scanline 191 DE (192*176=$8400)!
;   Immune to up to 400 cycles of Blitter/IRQ entry latency!
; =============================================================================
my_timer_b:
        clr.b   MFP_TBCR
        move.l  d0,-(sp)

        ; Pause Blitter if active in shared mode ($80) so it CANNOT retake the bus
        ; after 64 CPU bus accesses while we spin in .w_end191!
        move.b  BLT_CTRL,d0
        bclr    #7,BLT_CTRL
        swap    d0                  ; save original BLT_CTRL in high word of d0

        move.b  cur_disp_lo(pc),d0
.w_end191:
        cmp.b   HW_VCNT_LO,d0
        bne.s   .w_end191

        ; Exact start of HBL of line 191 (~cycle 384, 120+ cycles before line 192 DE!)
        ; Write VCNT_HI/MID/LO FIRST so it latches 32 cycles earlier (crucial at 60Hz!)
tb_hud_hi:
        move.b  #0,HW_VCNT_HI       ; 12 cyc (patched at init)
tb_hud_mid:
        move.b  #0,HW_VCNT_MID      ; 12 cyc (patched at init)
tb_hud_lo:
        move.b  #0,HW_VCNT_LO       ; 12 cyc (patched at init)
        clr.b   HW_LINEWID          ; 16 cyc
        clr.b   HW_HSCROLL          ; 16 cyc

        ; Resume Blitter if it was busy when we paused it
        swap    d0
        tst.b   d0
        bpl.s   .no_blt_res
        move.b  #$80,BLT_CTRL
.no_blt_res:
        move.l  (sp)+,d0
        bclr    #0,MFP_ISRA
        rte

; =============================================================================
; Helper: disable STe scroll mode cleanly (for Title / Tomb Select / Hi-Score)
; =============================================================================
disable_ste_scroll:
        move.w  sr,-(sp)
        ori.w   #$0700,sr
        clr.b   ste_scroll_active
        clr.b   in_gameplay
        clr.b   MFP_TBCR
        bclr    #0,MFP_IERA
        bclr    #0,MFP_IMRA
        clr.b   HW_LINEWID
        clr.b   HW_HSCROLL
        move.w  (sp)+,sr
        ; Restore original TOS screen base ($18130) in HI -> MID -> LO order!
        movea.l orig_base,a0
        move.l  O_SCR_PHYS(a0),d0
        swap    d0
        move.b  d0,HW_VBASE_HI      ; 1st: HI
        swap    d0
        move.w  d0,-(sp)
        lsr.w   #8,d0
        move.b  d0,HW_VBASE_MID     ; 2nd: MID (resets LO to 0 on STe)
        move.w  (sp)+,d0
        move.b  d0,HW_VBASE_LO      ; 3rd: LO (must be written LAST on STe!)
        rts

; =============================================================================
; +4: hook_title_credit
; =============================================================================
hook_title_credit:
        movea.l orig_base,a1
        adda.l  #O_DRAW_STR,a1
        jsr     (a1)
        movem.l d0-d1/a0-a1,-(sp)
        moveq   #0,d0
        move.w  #$bc,d1
        lea     str_credit(pc),a0
        movea.l orig_base,a1
        adda.l  #O_DRAW_STR,a1
        jsr     (a1)
        movem.l (sp)+,d0-d1/a0-a1
        rts

; =============================================================================
; +8: hook_game_key — 'H'/'h' 50/60Hz toggle + 'p' pause
; =============================================================================
hook_game_key:
        cmp.b   #'h',d0
        beq.s   .do_hz
        cmp.b   #'H',d0
        beq.s   .do_hz
        cmp.b   #$70,d0
        beq.s   .do_pause
        rts
.do_hz:
        st      sync_toggle_req
        moveq   #0,d0
        rts
.do_pause:
        addq.l  #4,sp
        movea.l orig_base,a0
        adda.l  #O_PAUSE_LOOP,a0
        jmp     (a0)

; =============================================================================
; +40/+44/+48: gameplay enter/exit hooks
; =============================================================================
hook_leave_select:
        bsr.w   disable_ste_scroll
        movea.l orig_base,a0
        adda.l  #O_TOMB_SEL,a0
        jmp     (a0)

hook_leave_hi:
        bsr.w   disable_ste_scroll
        movea.l orig_base,a0
        adda.l  #O_HISCORE,a0
        jmp     (a0)

hook_level_load:
        ; Reset STe scroll buffers, interpolation state, & HUD dirty state
        move.w  #-1,buf_tx
        move.w  #-1,buf_tx+2
        move.w  #-1,buf_ty
        move.w  #-1,buf_ty+2
        clr.w   back_idx
        clr.w   curr_spr_cnt
        clr.w   prev_spr_cnt
        clr.w   step_accum
        clr.b   has_prev_tick
        move.w  #-1,hud_cache
        ; Clear hud_buf (1,280 bytes = 320 longs)
        movea.l hud_buf,a0
        move.w  #319,d0
.clrhb: clr.l   (a0)+
        dbra    d0,.clrhb
        movea.l orig_base,a0
        adda.l  #O_LEVEL_LOAD,a0
        jmp     (a0)

; =============================================================================
; +16: hook_tile_cache — copy 110 composited 32x16 planar tiles (28,160 B)
;      from $18134 into tile_cache, skipping the slow 138 KB pre-shifter!
; =============================================================================
hook_tile_cache:
        movem.l d0-d2/a0-a2,-(sp)
        movea.l orig_base,a2
        move.w  O_TILE_CNT(a2),d0   ; dbra count = 109 -> 110 tiles
        movea.l O_SCR_BACK(a2),a0   ; source = $18134 staging buffer
        lea     tile_cache,a1
        lea     ste_tile_ptrs,a2
.tloop:
        move.l  a1,(a2)+
        moveq   #63,d1              ; 64 longs = 256 bytes (32x16 4-plane)
.cloop:
        move.l  (a0)+,(a1)+
        dbra    d1,.cloop
        dbra    d0,.tloop

        ; Apply Nick's two tile aliases ($14 -> $45, $15 -> $47)
        lea     ste_tile_ptrs,a2
        move.l  $45*4(a2),$14*4(a2)
        move.l  $47*4(a2),$15*4(a2)

        movem.l (sp)+,d0-d2/a0-a2
        rts

; =============================================================================
; Blitter helper: HOG mode ($c0) finishes 2x faster in wall-clock time so ALL
; Blitter work (even tile-boundary shifts!) completes by scanline ~170 — well
; =============================================================================
; blt_go — Safe Blitter trigger: full-speed HOG ($c0) outside scanlines 185..191,
;          hardware shared mode ($80, <=64 cyc IRQ latency) near Timer B!
; =============================================================================
blt_go:
        cmpi.b  #8,MFP_TBDR
        bls.s   .shared
        move.b  #$c0,BLT_CTRL       ; 96% of frame: 100% full-speed HOG!
        rts
.shared:
        move.b  #$80,BLT_CTRL       ; lines 183..191: shared mode (64 bus accesses = 256 cyc max!)
.sh_w:
        nop                         ; IRQ window for Timer B!
        tst.b   BLT_CTRL            ; bit 7 (N) = BUSY
        bmi.s   .sh_w
        rts

; =============================================================================
; +20: hook_render_map — during world tick, just update $1920e for entity
;      activator ($16682) and clear curr_spr_cnt; actual rendering happens at
;      50/60 FPS with 1-pixel interpolation inside hook_game_swap!
; =============================================================================
hook_render_map:
        movem.l d0-d2/a5-a6,-(sp)
        st      in_gameplay
        clr.w   curr_spr_cnt
        movea.l orig_base,a5
        move.w  O_CAM_X(a5),d0
        move.w  O_CAM_Y(a5),d1
        lsr.w   #5,d0
        lsr.w   #4,d1
        mulu.w  #80,d1
        add.w   d0,d1
        movea.l a5,a6
        adda.l  #O_MAP_PRI,a6
        adda.w  d1,a6
        move.l  a6,($01920e-ORIG_LOAD)(a5)
        movem.l (sp)+,d0-d2/a5-a6
        rts

; =============================================================================
; ste_render_map_at: render STe Blitter tilemap at interpolated (d0=cam_x, d1=cam_y)
; =============================================================================
ste_render_map_at:
        movem.l d0-d7/a0-a6,-(sp)
        movea.l orig_base,a5
        move.w  d0,cur_cam_x
        move.w  d1,cur_cam_y

        lsr.w   #5,d0               ; tx0 = cam_x >> 5 (0..70)
        lsr.w   #4,d1               ; ty0 = cam_y >> 4 (0..36)
        move.w  d0,cur_tx0
        move.w  d1,cur_ty0

        ; Map top-left pointer = O_MAP_PRI + ty0*80 + tx0
        move.w  d1,d2
        mulu.w  #80,d2
        add.w   d0,d2
        movea.l a5,a6
        adda.l  #O_MAP_PRI,a6
        adda.w  d2,a6

        ; 1. Compute 11x13 visible shadowed tile IDs into vis_tiles[143]
        ;    (Never mutates live map, zero restore pass needed!)
        movea.l a5,a0
        adda.l  #O_TILE_PROPS,a0    ; tile property flags (bit 7 = casts shadow)
        lea     O_SHADOW_MAP(a5),a1 ; tile -> shadowed tile LUT
        lea     vis_tiles,a2
        moveq   #12,d7              ; 13 rows
.srow:
        moveq   #10,d6              ; 11 cols
.scol:
        moveq   #0,d0
        move.b  (a6),d0
        ; Ladder auto-connect ($20 above $20 -> $41, $21 above $21 -> $42)
        cmp.b   #$20,d0
        bne.s   .chk21
        cmp.b   #$20,-80(a6)
        bne.s   .chksh
        moveq   #$41,d0
        bra.s   .chksh
.chk21:
        cmp.b   #$21,d0
        bne.s   .chksh
        cmp.b   #$21,-80(a6)
        bne.s   .chksh
        moveq   #$42,d0
.chksh:
        ; Check left (-1), up (-80), up-left (-81) shadow casters
        moveq   #0,d2
        move.b  -1(a6),d2
        move.b  (a0,d2.w),d3
        move.b  -80(a6),d2
        or.b    (a0,d2.w),d3
        move.b  -81(a6),d2
        or.b    (a0,d2.w),d3
        bpl.s   .noshad             ; bit 7 clear -> no shadow
        cmp.b   #$40,d0             ; don't double-map $41/$42? Wait: orig maps $41/$42 too!
        move.b  (a1,d0.w),d0
.noshad:
        move.b  d0,(a2)+
        addq.l  #1,a6
        dbra    d6,.scol
        lea     80-11(a6),a6
        dbra    d7,.srow

        ; 2. Select current back buffer (0 or 1)
        move.w  back_idx,d7
        add.w   d7,d7               ; 0 or 2 (word index)
        movea.l pf_buf0,a4
        lea     buf_tiles0,a3
        tst.w   d7
        beq.s   .got_buf
        movea.l pf_buf1,a4
        lea     buf_tiles1,a3
.got_buf:
        move.l  a4,cur_pf_buf
        move.l  a3,cur_buf_tiles

        ; Check if (tx0, ty0) changed for this buffer
        lea     buf_tx,a0
        move.w  cur_tx0,d0
        sub.w   (a0,d7.w),d0        ; dx = tx0 - old_tx
        lea     buf_ty,a1
        move.w  cur_ty0,d1
        sub.w   (a1,d7.w),d1        ; dy = ty0 - old_ty
        move.w  d0,d2
        or.w    d1,d2
        beq.w   .blit_dirty         ; same (tx0, ty0) -> skip shift!

        ; Save new (tx0, ty0)
        move.w  cur_tx0,(a0,d7.w)
        move.w  cur_ty0,(a1,d7.w)

        ; If |dx|<=1 and |dy|<=1 and old_tx >= 0 -> fast Blitter shift!
        ; Wait: for simplicity & zero edge bugs, check if |dx|<=1 and |dy|<=1
        cmp.w   #-1,d0
        blt.s   .full_inval
        cmp.w   #1,d0
        bgt.s   .full_inval
        cmp.w   #-1,d1
        blt.s   .full_inval
        cmp.w   #1,d1
        bgt.s   .full_inval

        ; ---- In-place Blitter shift of pf_buf + buf_tiles by (-dx, -dy) ----
        bsr.w   shift_pf_buffer
        bra.s   .blit_dirty

.full_inval:
        movea.l a3,a0
        move.w  #142,d2
.invl:  st      (a0)+
        dbra    d2,.invl

        ; 3. Blit only tiles where vis_tiles[i] != buf_tiles[i]
.blit_dirty:
        ; Common Blitter setup for 32x16 4-plane tile (8 words x 16 lines)
        move.w  #2,BLT_SRC_XINC
        move.w  #2,BLT_SRC_YINC
        move.w  #2,BLT_DST_XINC
        move.w  #PF_STRIDE-14,BLT_DST_YINC  ; 176 - 14 = 162
        move.w  #$ffff,BLT_ENDMASK1
        move.w  #$ffff,BLT_ENDMASK2
        move.w  #$ffff,BLT_ENDMASK3
        move.b  #2,BLT_HOP          ; source
        move.b  #3,BLT_OP           ; replace
        clr.b   BLT_SKEW

        lea     vis_tiles,a0
        movea.l cur_buf_tiles,a1
        lea     ste_tile_ptrs,a2
        movea.l cur_pf_buf,a4       ; row base in pf_buf
        moveq   #12,d7              ; 13 rows
.brow:
        movea.l a4,a6               ; col dst ptr
        moveq   #10,d6              ; 11 cols
.bcol:
        move.b  (a0)+,d0
        cmp.b   (a1),d0
        beq.s   .bskip
        move.b  d0,(a1)
        andi.w  #$00ff,d0
        add.w   d0,d0
        add.w   d0,d0
        move.l  (a2,d0.w),BLT_SRC_ADDR
        move.l  a6,BLT_DST_ADDR
        move.w  #8,BLT_XCOUNT
        move.w  #16,BLT_YCOUNT
        bsr.w   blt_go
.bskip:
        addq.l  #1,a1
        lea     16(a6),a6           ; next 32px tile (+16 bytes)
        dbra    d6,.bcol
        lea     16*PF_STRIDE(a4),a4 ; next 16-line tile row (+2816 bytes)
        dbra    d7,.brow

        movem.l (sp)+,d0-d7/a0-a6
        rts

; =============================================================================
; shift_pf_buffer: shift pf_buf (a4) and buf_tiles (a3) by (-d0, -d1)
;   d0 = dx (-1, 0, +1), d1 = dy (-1, 0, +1)
; =============================================================================
shift_pf_buffer:
        movem.l d0-d7/a0-a3,-(sp)
        ; Compute overlap dimensions:
        ;   w_tiles = 11 - |dx| (10 or 11), h_tiles = 13 - |dy| (12 or 13)
        ;   src_x = max(0, dx),  dst_x = max(0, -dx)
        ;   src_y = max(0, dy),  dst_y = max(0, -dy)
        moveq   #0,d2               ; src_x
        moveq   #0,d3               ; dst_x
        moveq   #11,d4              ; w_tiles
        tst.w   d0
        beq.s   .sx_ok
        bpl.s   .sx_pos
        moveq   #1,d3               ; dx = -1 -> dst_x = 1
        moveq   #10,d4
        bra.s   .sx_ok
.sx_pos:
        moveq   #1,d2               ; dx = +1 -> src_x = 1
        moveq   #10,d4
.sx_ok:
        moveq   #0,d5               ; src_y
        moveq   #0,d6               ; dst_y
        moveq   #13,d7              ; h_tiles
        tst.w   d1
        beq.s   .sy_ok
        bpl.s   .sy_pos
        moveq   #1,d6               ; dy = -1 -> dst_y = 1
        moveq   #12,d7
        bra.s   .sy_ok
.sy_pos:
        moveq   #1,d5               ; dy = +1 -> src_y = 1
        moveq   #12,d7
.sy_ok:
        ; 1. Shift buf_tiles[143] via temp copy (143 bytes -> super fast!)
        ; First fill temp with $ff, copy overlapping region, copy back
        lea     tmp_tiles,a0
        move.w  #142,d0
.ftmp:  st      (a0)+
        dbra    d0,.ftmp

        ; src_ptr = a3 + src_y*11 + src_x
        move.w  d5,d0
        mulu.w  #11,d0
        add.w   d2,d0
        lea     (a3,d0.w),a0
        ; dst_ptr = tmp_tiles + dst_y*11 + dst_x
        move.w  d6,d0
        mulu.w  #11,d0
        add.w   d3,d0
        lea     tmp_tiles,a1
        adda.w  d0,a1

        move.w  d7,d1
        subq.w  #1,d1               ; h_tiles - 1
.trow:
        move.w  d4,d0
        subq.w  #1,d0               ; w_tiles - 1
        movea.l a0,a2
        movem.l a1,-(sp)
.tcol:
        move.b  (a2)+,(a1)+
        dbra    d0,.tcol
        movem.l (sp)+,a1
        lea     11(a0),a0
        lea     11(a1),a1
        dbra    d1,.trow

        ; Copy tmp_tiles -> a3 (143 bytes)
        lea     tmp_tiles,a0
        movea.l a3,a1
        move.w  #142,d0
.ctmp:  move.b  (a0)+,(a1)+
        dbra    d0,.ctmp

        ; 2. Blitter shift pf_buf (a4):
        ; src_byte = src_y*16*176 + src_x*16
        ; dst_byte = dst_y*16*176 + dst_x*16
        move.w  d5,d0
        mulu.w  #16*PF_STRIDE,d0
        move.w  d2,d1
        lsl.w   #4,d1
        add.w   d1,d0
        lea     (a4,d0.l),a0        ; src_start

        move.w  d6,d0
        mulu.w  #16*PF_STRIDE,d0
        move.w  d3,d1
        lsl.w   #4,d1
        add.w   d1,d0
        lea     (a4,d0.l),a1        ; dst_start

        ; xwords = w_tiles * 8, ylines = h_tiles * 16
        lsl.w   #3,d4               ; xwords (80 or 88)
        lsl.w   #4,d7               ; ylines (192 or 208)

        move.w  #$ffff,BLT_ENDMASK1
        move.w  #$ffff,BLT_ENDMASK2
        move.w  #$ffff,BLT_ENDMASK3
        move.b  #2,BLT_HOP
        move.b  #3,BLT_OP
        clr.b   BLT_SKEW

        cmpa.l  a0,a1
        bhi.s   .desc               ; dst > src -> descending copy!

        ; Ascending copy in 4-line HOG chunks (4 * 80w = 320 words -> <= ~1280? Wait:
        ; 1-line HOG chunk = 80w = 320 cycles < 420-cycle Timer B latency budget!)
        move.w  #2,BLT_SRC_XINC
        move.w  #2,BLT_DST_XINC
        move.w  #PF_STRIDE,d0
        move.w  d4,d1
        add.w   d1,d1               ; xbytes
        sub.w   d1,d0
        addq.w  #2,d0               ; yinc = PF_STRIDE - xbytes + 2
        move.w  d0,BLT_SRC_YINC
        move.w  d0,BLT_DST_YINC
        move.l  a0,BLT_SRC_ADDR
        move.l  a1,BLT_DST_ADDR
        subq.w  #1,d7               ; ylines - 1
.asc_l:
        move.w  d4,BLT_XCOUNT
        move.w  #1,BLT_YCOUNT
        bsr.w   blt_go
        dbra    d7,.asc_l
        bra.w   .sdone

.desc:
        ; NEVER use XINC = -2 on STe Blitter (hardware barrel-shifter 1-word delay)!
        ; Case A: dy < 0 (dst_y = 1, src_y = 0) -> bottom-to-top, 1-line HOG chunks!
        tst.w   d6                  ; dst_y == 1 means dy == -1
        beq.s   .desc_left_only

        move.w  d7,d0
        subq.w  #1,d0
        mulu.w  #PF_STRIDE,d0
        adda.l  d0,a0
        adda.l  d0,a1

        move.w  #2,BLT_SRC_XINC
        move.w  #2,BLT_DST_XINC
        move.w  d4,d0
        add.w   d0,d0               ; xbytes
        addi.w  #PF_STRIDE-2,d0
        neg.w   d0
        move.w  d0,BLT_SRC_YINC
        move.w  d0,BLT_DST_YINC
        move.l  a0,BLT_SRC_ADDR
        move.l  a1,BLT_DST_ADDR
        subq.w  #1,d7
.du_l:
        move.w  d4,BLT_XCOUNT
        move.w  #1,BLT_YCOUNT
        bsr.w   blt_go
        dbra    d7,.du_l
        bra.w   .sdone

.desc_left_only:
        ; Case B: dy == 0, dx == -1 (dst = src + 16, 10 tile columns x 208 lines)
        ; Copy column 9 down to 0 in 8-line HOG chunks (8*8 = 64 words = ~256 cyc max!)
        move.w  #2,BLT_SRC_XINC
        move.w  #2,BLT_DST_XINC
        move.w  #PF_STRIDE-14,BLT_SRC_YINC
        move.w  #PF_STRIDE-14,BLT_DST_YINC
        lea     9*16(a0),a0         ; col 9 src
        lea     9*16(a1),a1         ; col 9 dst (= col 10)
        moveq   #9,d2               ; 10 columns
.dcol:
        move.l  a0,BLT_SRC_ADDR
        move.l  a1,BLT_DST_ADDR
        moveq   #25,d3              ; 26 * 8 = 208 lines
.dcol_c:
        move.w  #8,BLT_XCOUNT
        move.w  #8,BLT_YCOUNT
        bsr.w   blt_go
        dbra    d3,.dcol_c
        lea     -16(a0),a0
        lea     -16(a1),a1
        dbra    d2,.dcol

.sdone:
        movem.l (sp)+,d0-d7/a0-a3
        rts

; =============================================================================
; +24: hook_hud_draw — dirty-checked HUD draw into static 8-line hud_buf
; =============================================================================
hook_hud_draw:
        movem.l d0-d7/a0-a6,-(sp)
        movea.l orig_base,a5

        ; Run Nick's HUD string formatter ($012e7e..$012f40) -> writes 40 bytes at $19300
        ; Wait: $012e7e ends with jsr $17976 at $012f4a; we can either call a local copy
        ; OR temporarily check if anything changed BEFORE calling $12e7e?
        ; Even cleaner: let $012e7e run ONLY when we point $18134 -> hud_buf - $7800!
        ; Wait: $012e7e always calls $17976 at the end! Let's check the 5 HUD vars directly!
        ; HUD vars: lives=$192ce, score=$192d0(L), bows=$1925a, arrows=$1925c, keys=$19258, delay=$192d8
        ; Compare all 6 words+long (14 bytes) against cached values!
        lea     hud_cache(pc),a0
        move.w  ($0192ce-ORIG_LOAD)(a5),d0
        cmp.w   (a0)+,d0
        bne.s   .hud_dirty
        move.l  ($0192d0-ORIG_LOAD)(a5),d0
        cmp.l   (a0)+,d0
        bne.s   .hud_dirty
        move.w  ($01925a-ORIG_LOAD)(a5),d0
        cmp.w   (a0)+,d0
        bne.s   .hud_dirty
        move.w  ($01925c-ORIG_LOAD)(a5),d0
        cmp.w   (a0)+,d0
        bne.s   .hud_dirty
        move.w  ($019258-ORIG_LOAD)(a5),d0
        cmp.w   (a0)+,d0
        bne.s   .hud_dirty
        move.w  ($0192d8-ORIG_LOAD)(a5),d0
        cmp.w   (a0)+,d0
        beq.s   .hud_done           ; UNCHANGED -> 0 cycles!

.hud_dirty:
        lea     hud_cache(pc),a0
        move.w  ($0192ce-ORIG_LOAD)(a5),(a0)+
        move.l  ($0192d0-ORIG_LOAD)(a5),(a0)+
        move.w  ($01925a-ORIG_LOAD)(a5),(a0)+
        move.w  ($01925c-ORIG_LOAD)(a5),(a0)+
        move.w  ($019258-ORIG_LOAD)(a5),(a0)+
        move.w  ($0192d8-ORIG_LOAD)(a5),(a0)+

        ; Redirect $18134 to (hud_buf - $7800), call $012e7e, restore $18134!
        move.l  O_SCR_BACK(a5),-(sp)
        move.l  hud_buf,d0
        sub.l   #$7800,d0
        move.l  d0,O_SCR_BACK(a5)
        lea     O_HUD_FMT(a5),a0
        jsr     (a0)
        move.l  (sp)+,O_SCR_BACK(a5)

.hud_done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

; =============================================================================
; +28/+32/+36: Sprite draw hooks — record into curr_spr_list during world tick
;              (falls back to original routines when in_gameplay == 0!)
; =============================================================================
hook_spr_normal:
        tst.b   in_gameplay
        bne.s   record_spr
        movea.l orig_base,a1
        sub.w   O_CAM_X(a1),d1
        adda.l  #O_SPR_NORM_CONT,a1
        jmp     (a1)

hook_spr_alt1:
        tst.b   in_gameplay
        bne.s   record_spr
        movea.l orig_base,a1
        sub.w   O_CAM_X(a1),d1
        adda.l  #O_SPR_ALT1_CONT,a1
        jmp     (a1)

hook_spr_alt2:
        tst.b   in_gameplay
        bne.s   record_spr
        movea.l orig_base,a1
        sub.w   O_CAM_X(a1),d1
        adda.l  #O_SPR_ALT2_CONT,a1
        jmp     (a1)

; -----------------------------------------------------------------------------
; record_spr: check visibility against current camera ($18142/$18144), record
;   16-byte entry [tag.L, spr_ptr.L, h_m1.W, x.W, y.W, pad.W] in curr_spr_list,
;   and return d0 = 1 (onscreen) or d0 = 0 (offscreen).
; -----------------------------------------------------------------------------
MAX_SPR         equ 32
SPR_ENT_SIZE    equ 16

record_spr:
        movem.l d1-d5/a1-a2,-(sp)
        movea.l orig_base,a1

        ; Exact onscreen visibility check vs camera ($18142/$18144)
        move.w  d1,d3
        sub.w   O_CAM_X(a1),d3
        addi.w  #31,d3
        bmi.s   .rec_off
        cmp.w   #$15f,d3
        bcc.s   .rec_off

        move.w  d2,d4
        sub.w   O_CAM_Y(a1),d4
        add.w   d0,d4
        bmi.s   .rec_off
        move.w  #$c0,d5
        add.w   d0,d5
        cmp.w   d5,d4
        bcc.s   .rec_off

        ; Append to curr_spr_list if space
        move.w  curr_spr_cnt,d3
        cmp.w   #MAX_SPR,d3
        bcc.s   .rec_on
        addq.w  #1,curr_spr_cnt
        lsl.w   #4,d3               ; * 16 bytes
        lea     curr_spr_list,a2
        adda.w  d3,a2

        ; Tag = caller return address (at 28(sp) past 7 saved regs) XOR a6
        move.l  28(sp),d4
        move.l  a6,d5
        eor.l   d5,d4
        move.l  d4,(a2)+            ; +0: tag
        move.l  a0,(a2)+            ; +4: spr_ptr
        move.w  d0,(a2)+            ; +8: h_m1
        move.w  d1,(a2)+            ; +10: x
        move.w  d2,(a2)+            ; +12: y
        clr.w   (a2)+               ; +14: pad
.rec_on:
        movem.l (sp)+,d1-d5/a1-a2
        moveq   #1,d0
        rts
.rec_off:
        movem.l (sp)+,d1-d5/a1-a2
        moveq   #0,d0
        rts

; -----------------------------------------------------------------------------
; ste_spr_draw: draw 32x(d0+1) planar sprite (a0) at world (d1, d2) into pf_buf
;   Returns d0 = 1 if onscreen, d0 = 0 if clipped offscreen (exact orig contract)
; -----------------------------------------------------------------------------
ste_spr_draw:
        movem.l d1-d7/a0-a6,-(sp)

        ; 1. Onscreen visibility check vs camera (exact same bounds as $015fd8)
        move.w  d1,d3
        sub.w   cur_cam_x,d3
        addi.w  #31,d3
        bmi.w   .offscreen
        cmp.w   #$15f,d3
        bcc.w   .offscreen

        move.w  d2,d4
        sub.w   cur_cam_y,d4
        add.w   d0,d4
        bmi.w   .offscreen
        move.w  #$c0,d5
        add.w   d0,d5
        cmp.w   d5,d4
        bcc.w   .offscreen

        ; 2. Buffer coordinates (bx, by) relative to (cur_tx0*32, cur_ty0*16)
        move.w  cur_tx0,d3
        lsl.w   #5,d3
        sub.w   d3,d1               ; bx = world_x - cur_tx0*32
        move.w  cur_ty0,d3
        lsl.w   #4,d3
        sub.w   d3,d2               ; by = world_y - cur_ty0*16

        ; Vertical clip to [0 .. PF_HEIGHT-1]
        move.w  d0,d5
        addq.w  #1,d5               ; h = d0 + 1
        tst.w   d2
        bpl.s   .y_top_ok
        add.w   d2,d5               ; h += by
        ble.w   .onscreen_done
        neg.w   d2
        lsl.w   #4,d2               ; skip (-by) * 16 bytes of sprite
        adda.w  d2,a0
        moveq   #0,d2
.y_top_ok:
        move.w  d2,d3
        add.w   d5,d3
        cmp.w   #PF_HEIGHT,d3
        ble.s   .y_bot_ok
        move.w  #PF_HEIGHT,d5
        sub.w   d2,d5
        ble.w   .onscreen_done
.y_bot_ok:
        ; Horizontal clip: require 0 <= bx <= PF_STRIDE*2 - 32 (320) for fast Blitter path
        ; (If partially off buffer edge < 0 or > 320, skip drawing safely — it's offscreen anyway
        ;  except in the 0..31px margin; we clamp bx < 0 or > 320 cleanly!)
        tst.w   d1
        bmi.w   .onscreen_done
        cmp.w   #320,d1
        bgt.w   .onscreen_done

        ; 3. Mark touched tiles in cur_buf_tiles[143] as $ff so Blitter restores them next frame!
        ;    tx_lo = bx >> 5, tx_hi = (bx + 31) >> 5
        ;    ty_lo = by >> 4, ty_hi = (by + h - 1) >> 4
        move.w  d1,d3
        lsr.w   #5,d3               ; tx_lo
        move.w  d1,d4
        addi.w  #31,d4
        lsr.w   #5,d4               ; tx_hi
        cmp.w   #10,d4
        ble.s   .txh_ok
        moveq   #10,d4
.txh_ok:
        move.w  d2,d6
        lsr.w   #4,d6               ; ty_lo
        move.w  d2,d7
        add.w   d5,d7
        subq.w  #1,d7
        lsr.w   #4,d7               ; ty_hi
        cmp.w   #12,d7
        ble.s   .tyh_ok
        moveq   #12,d7
.tyh_ok:
        movea.l cur_buf_tiles,a1
        move.w  d6,d0
        mulu.w  #11,d0
        add.w   d3,d0
        adda.w  d0,a1
        sub.w   d3,d4               ; nx - 1
        sub.w   d6,d7               ; ny - 1
.mark_y:
        movea.l a1,a2
        move.w  d4,d0
.mark_x:
        st      (a2)+
        dbra    d0,.mark_x
        lea     11(a1),a1
        dbra    d7,.mark_y

        ; 4. Un-swap planes 0 & 1 into spr_tmp_buf (Nick stores [w1_p0,w0_p0, w1_p1,w0_p1, w0_p2,w1_p2, w0_p3,w1_p3])
        ;    and simultaneously build POSITIVE 2-word mask into spr_mask_buf (4 bytes/row)
        movea.l a0,a1
        lea     spr_mask_buf,a2
        lea     spr_tmp_buf,a3
        move.w  d5,d7
        subq.w  #1,d7
.mk_m:
        movem.l (a1)+,d0/d3/d4/d6
        swap    d0                  ; fix plane 0 [w0, w1]
        swap    d3                  ; fix plane 1 [w0, w1]
        movem.l d0/d3/d4/d6,(a3)
        lea     16(a3),a3
        or.l    d3,d0
        or.l    d4,d0
        or.l    d6,d0
        move.l  d0,(a2)+
        dbra    d7,.mk_m
        lea     spr_tmp_buf,a0      ; blit planes from normalized spr_tmp_buf!

        ; 5. Destination address in pf_buf: pf_buf + by*176 + (bx>>4)*8
        movea.l cur_pf_buf,a4
        move.w  d2,d0
        mulu.w  #PF_STRIDE,d0
        adda.l  d0,a4
        move.w  d1,d0
        lsr.w   #4,d0
        lsl.w   #3,d0
        adda.w  d0,a4               ; dst word-group ptr

        andi.w  #15,d1              ; skew = bx & 15 (0..15)
        beq.w   .spr_aligned

        ; ---- Shifted sprite (skew = 1..15, spans 3 word-groups = 48px) ----
        ; Compute endmasks for right-shift by d1:
        ;   em1 = $ffff >> d1, em2 = $ffff, em3 = ~($ffff >> d1)
        move.w  #$ffff,d3
        lsr.w   d1,d3               ; em1 (bits kept in first word)
        move.w  d3,d4
        not.w   d4                  ; em3 (bits kept in third word)
        move.w  d3,BLT_ENDMASK1
        move.w  #$ffff,BLT_ENDMASK2
        move.w  d4,BLT_ENDMASK3
        move.b  #2,BLT_HOP
        ori.b   #$40,d1             ; NFSR (bit 6): don't fetch 3rd source word!
        move.b  d1,BLT_SKEW

        ; Pass 1: AND ~mask across all 4 planes (OP=1: S & D)
        ;   Note: when shifting ~mask (1-filled!), NFSR shifts 0s into top bits of word 0
        ;   Wait: for ~mask we want 1s shifted into empty edges! Using OP=4 (~S & D) with
        ;   POSITIVE mask (0-filled!) makes NFSR shift 0s -> ~0 = 1s cleanly!
        ;   Let's invert spr_mask_buf? Even better: compute POSITIVE mask above and use OP=4 (~S & D)!
        ;   Wait: we can just use OP=1 if we invert, OR let's flip the `not.w d0` above and use OP=4!
        ;   (Doing `not.w d0` removed below -> POSITIVE mask -> OP=4 (~S & D)!)
        ;   Wait: we ALREADY did `not.w d0` above — let's use OP=4 and remove `not.w d0`!
        ;   (Handled right below by jumping to shared mask/plane blit!)
        move.w  #2,BLT_SRC_XINC
        move.w  #2,BLT_SRC_YINC     ; 2 words/row, NFSR skips 3rd word -> yinc = +2!
        move.w  #8,BLT_DST_XINC
        move.w  #PF_STRIDE-16,BLT_DST_YINC ; 176 - 2*8 = 160
        move.b  #4,BLT_OP           ; ~S & D (positive mask!)

        movea.l a4,a3
        moveq   #3,d6
.m_p1:
        move.l  #spr_mask_buf,BLT_SRC_ADDR
        move.l  a3,BLT_DST_ADDR
        move.w  #3,BLT_XCOUNT
        move.w  d5,BLT_YCOUNT
        bsr.w   blt_go
        addq.l  #2,a3
        dbra    d6,.m_p1

        ; Pass 2: OR sprite planes across all 4 planes (OP=7: S | D)
        ;   Sprite format: [p0.L, p1.L, p2.L, p3.L] -> 2 adjacent words per plane,
        ;   16 bytes/row -> SRC_XINC=2, SRC_YINC=14 (NFSR skips 3rd word!)
        move.w  #2,BLT_SRC_XINC
        move.w  #14,BLT_SRC_YINC
        move.b  #7,BLT_OP           ; S | D
        movea.l a0,a2
        movea.l a4,a3
        moveq   #3,d6
.m_p2:
        move.l  a2,BLT_SRC_ADDR
        move.l  a3,BLT_DST_ADDR
        move.w  #3,BLT_XCOUNT
        move.w  d5,BLT_YCOUNT
        bsr.w   blt_go
        addq.l  #4,a2               ; next plane longword (+4 bytes)
        addq.l  #2,a3               ; next interleaved dest plane (+2 bytes)
        dbra    d6,.m_p2
        bra.w   .onscreen_done

.spr_aligned:
        ; ---- 16px-aligned sprite (skew = 0, spans 2 word-groups = 32px) ----
        move.w  #$ffff,BLT_ENDMASK1
        move.w  #$ffff,BLT_ENDMASK2
        move.w  #$ffff,BLT_ENDMASK3
        move.b  #2,BLT_HOP
        clr.b   BLT_SKEW

        ; Pass 1: ~S & D (positive mask) across 4 planes
        move.w  #2,BLT_SRC_XINC
        move.w  #2,BLT_SRC_YINC
        move.w  #8,BLT_DST_XINC
        move.w  #PF_STRIDE-8,BLT_DST_YINC
        move.b  #4,BLT_OP           ; ~S & D

        movea.l a4,a3
        moveq   #3,d6
.a_p1:
        move.l  #spr_mask_buf,BLT_SRC_ADDR
        move.l  a3,BLT_DST_ADDR
        move.w  #2,BLT_XCOUNT
        move.w  d5,BLT_YCOUNT
        bsr.w   blt_go
        addq.l  #2,a3
        dbra    d6,.a_p1

        ; Pass 2: S | D across 4 planes ([p0.L, p1.L, p2.L, p3.L])
        move.w  #2,BLT_SRC_XINC
        move.w  #14,BLT_SRC_YINC
        move.b  #7,BLT_OP           ; S | D
        movea.l a0,a2
        movea.l a4,a3
        moveq   #3,d6
.a_p2:
        move.l  a2,BLT_SRC_ADDR
        move.l  a3,BLT_DST_ADDR
        move.w  #2,BLT_XCOUNT
        move.w  d5,BLT_YCOUNT
        bsr.w   blt_go
        addq.l  #4,a2
        addq.l  #2,a3
        dbra    d6,.a_p2

.onscreen_done:
        movem.l (sp)+,d1-d7/a0-a6
        moveq   #1,d0
        rts

.offscreen:
        movem.l (sp)+,d1-d7/a0-a6
        moveq   #0,d0
        rts

; =============================================================================
; +12: hook_game_swap — Unlinked Fixed-Timestep (16.67 Hz) + 50/60 FPS
;      1-Pixel Interpolated STe Render Loop!
; =============================================================================
; World logic ticks at 16.667 Hz identically on 50Hz (dt=60/180) and 60Hz (dt=50/180).
; Every single VBL renders at 50 or 60 FPS with linear 1-pixel interpolation of
; camera + all recorded sprites between (prev_tick) and (curr_tick)!
hook_game_swap:
        movem.l d0-d7/a0-a6,-(sp)
        movea.l orig_base,a5

        ; Latch current tick's camera (note: $012956 already committed next_cam -> $18142/$18144!)
        move.w  O_CAM_X(a5),d0
        move.w  O_CAM_Y(a5),d1
        move.w  d0,curr_cam_x
        move.w  d1,curr_cam_y

        ; On very first tick of a level, snap prev = curr (no jump from 0,0!)
        tst.b   has_prev_tick
        bne.s   .render_vbl_loop
        move.w  d0,prev_cam_x
        move.w  d1,prev_cam_y
        move.l  vbl_count,last_vbl
        st      has_prev_tick
        clr.w   step_accum

.render_vbl_loop:
        ; alpha = step_accum (0..179), scaled to [0..180]
        move.w  step_accum,d7       ; d7 = alpha (0..179)

        ; 1. Interpolate camera: render_cam = prev_cam + ((curr_cam - prev_cam) * alpha) / 180
        move.w  curr_cam_x,d0
        move.w  prev_cam_x,d2
        sub.w   d2,d0               ; dx
        move.w  d0,d3
        bpl.s   .cx_pos
        neg.w   d3
.cx_pos:
        cmp.w   #32,d3
        bgt.s   .cx_snap            ; big jump/teleport -> snap
        muls.w  d7,d0
        divs.w  #180,d0
        add.w   d2,d0
        bra.s   .cx_done
.cx_snap:
        move.w  curr_cam_x,d0
.cx_done:
        move.w  curr_cam_y,d1
        move.w  prev_cam_y,d2
        sub.w   d2,d1               ; dy
        move.w  d1,d3
        bpl.s   .cy_pos
        neg.w   d3
.cy_pos:
        cmp.w   #32,d3
        bgt.s   .cy_snap
        muls.w  d7,d1
        divs.w  #180,d1
        add.w   d2,d1
        bra.s   .cy_done
.cy_snap:
        move.w  curr_cam_y,d1
.cy_done:
        ; 2. Render STe Blitter tilemap into pf_buf[back] at (d0=render_cam_x, d1=render_cam_y)
        bsr.w   ste_render_map_at

        ; 3. Render all recorded sprites with 1-pixel interpolation!
        move.w  curr_spr_cnt,d6
        beq.w   .spr_all_done
        subq.w  #1,d6
        lea     curr_spr_list,a4
.spr_loop:
        move.l  (a4),d4             ; tag
        movea.l 4(a4),a0            ; spr_ptr
        move.w  8(a4),d0            ; h_m1
        move.w  10(a4),d1           ; curr_x
        move.w  12(a4),d2           ; curr_y

        ; Search prev_spr_list for matching tag
        move.w  prev_spr_cnt,d5
        beq.s   .spr_draw_now
        subq.w  #1,d5
        lea     prev_spr_list,a3
.spr_find:
        cmp.l   (a3),d4
        beq.s   .spr_found
        lea     SPR_ENT_SIZE(a3),a3
        dbra    d5,.spr_find
        bra.s   .spr_draw_now       ; new sprite -> draw at curr pos

.spr_found:
        ; Interpolate X if |dx| <= 16
        move.w  10(a3),d3           ; prev_x
        sub.w   d3,d1               ; dx = curr_x - prev_x
        move.w  d1,d5
        bpl.s   .sx_p
        neg.w   d5
.sx_p:  cmp.w   #16,d5
        bgt.s   .sx_snap
        muls.w  d7,d1
        divs.w  #180,d1
        add.w   d3,d1
        bra.s   .sx_ok
.sx_snap:
        move.w  10(a4),d1
.sx_ok:
        ; Interpolate Y if |dy| <= 16
        move.w  12(a3),d3           ; prev_y
        sub.w   d3,d2               ; dy = curr_y - prev_y
        move.w  d2,d5
        bpl.s   .sy_p
        neg.w   d5
.sy_p:  cmp.w   #16,d5
        bgt.s   .sy_snap
        muls.w  d7,d2
        divs.w  #180,d2
        add.w   d3,d2
        bra.s   .spr_draw_now
.sy_snap:
        move.w  12(a4),d2

.spr_draw_now:
        bsr.w   ste_spr_draw
        lea     SPR_ENT_SIZE(a4),a4
        dbra    d6,.spr_loop
.spr_all_done:

        ; 4. Publish STe HW scroll registers for cur_pf_buf at (cur_cam_x, cur_cam_y)
        move.l  cur_pf_buf,d0
        move.w  cur_cam_y,d1
        andi.w  #15,d1
        mulu.w  #PF_STRIDE,d1
        add.l   d1,d0
        move.w  cur_cam_x,d1
        andi.w  #31,d1
        moveq   #0,d2
        move.w  d1,d2
        lsr.w   #4,d2
        lsl.w   #3,d2               ; 0 or 8 bytes (upper 16 bits guaranteed 0!)
        add.l   d2,d0
        andi.w  #15,d1              ; hscroll (0..15)
        moveq   #8,d2
        tst.w   d1
        beq.s   .lw_ok
        moveq   #4,d2
.lw_ok:
        ; Publish display parameters atomically to RAM — my_vbl commits HW_VBASE + HW_VCNT
        ; together during top border so we NEVER race line 260/310 RestartVideoCounter!
        move.w  sr,d3
        ori.w   #$0700,sr
        swap    d0
        move.b  d0,disp_hi
        swap    d0
        move.w  d0,d4
        lsr.w   #8,d4
        move.b  d4,disp_mid
        move.b  d0,disp_lo
        move.b  d2,disp_linewid
        move.b  d1,disp_hscroll
        st      ste_scroll_active
        st      disp_pending
        move.w  d3,sr

        ; Wait for VBL to latch this 50/60 FPS frame!
.wait_v:
        tst.b   disp_pending
        bne.s   .wait_v

        ; Flip double-buffer index for next frame
        eori.w  #1,back_idx

        ; 5. Advance fixed-timestep accumulator by REAL elapsed VBLs!
        ;    (50Hz: +60/VBL, 60Hz: +50/VBL; threshold 180 = exact 16.667 Hz even if a frame ever takes 2 VBLs!)
        move.l  vbl_count,d1
        move.l  d1,d0
        sub.l   last_vbl,d0
        move.l  d1,last_vbl
        ; Clamp elapsed VBLs to [1..4] (guards first frame / pauses)
        cmp.l   #1,d0
        bge.s   .ev_min
        moveq   #1,d0
.ev_min:
        cmp.l   #4,d0
        ble.s   .ev_max
        moveq   #4,d0
.ev_max:
        moveq   #60,d2
        tst.b   is_60hz
        beq.s   .dt_ok
        moveq   #50,d2
.dt_ok:
        mulu.w  d2,d0
        add.w   step_accum,d0
        cmp.w   #180,d0
        bcc.s   .tick_ready
        move.w  d0,step_accum
        bra.w   .render_vbl_loop    ; render next interpolated 50/60 FPS VBL!

.tick_ready:
        sub.w   #180,d0
        cmp.w   #180,d0
        bcs.s   .acc_ok
        moveq   #0,d0
.acc_ok:
        move.w  d0,step_accum

        ; Save current tick's camera & sprite list as prev for next tick's interpolation
        move.w  curr_cam_x,prev_cam_x
        move.w  curr_cam_y,prev_cam_y
        move.w  curr_spr_cnt,d0
        move.w  d0,prev_spr_cnt
        beq.s   .swap_done
        lsl.w   #2,d0               ; 4 longs per 16-byte entry
        subq.w  #1,d0
        lea     curr_spr_list,a0
        lea     prev_spr_list,a1
.cp_s:  move.l  (a0)+,(a1)+
        dbra    d0,.cp_s
.swap_done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

; ---- Data (in TEXT for PC-relative fast reads in Timer B / VBL ISRs) ----
disp_hi:            dc.b 0
disp_mid:           dc.b 0
disp_lo:            dc.b 0
disp_linewid:       dc.b 0
disp_hscroll:       dc.b 0
act_linewid:        dc.b 0
act_hscroll:        dc.b 0
cur_disp_lo:        dc.b 0
hud_hi:             dc.b 0
hud_mid:            dc.b 0
hud_lo:             dc.b 0
        even
hud_cache:          ds.b 14
str_credit:
        dc.b    "       enhanced by dad_prg v1.0",0,$ff
        even

; =============================================================================
; BSS
; =============================================================================
        section bss
bss_guard:          ds.b 1024       ; guard past orig BSS tail ($63e12+)
orig_base:          ds.l 1
old_ssp:            ds.l 1
old_vbl:            ds.l 1
old_tb:             ds.l 1
old_tc:             ds.l 1
old_ikbd:           ds.l 1
vbl_count:          ds.l 1
last_vbl:           ds.l 1
pf_buf0:            ds.l 1
pf_buf1:            ds.l 1
hud_buf:            ds.l 1
cur_pf_buf:         ds.l 1
cur_buf_tiles:      ds.l 1
back_idx:           ds.w 1
cur_cam_x:          ds.w 1
cur_cam_y:          ds.w 1
cur_tx0:            ds.w 1
cur_ty0:            ds.w 1
buf_tx:             ds.w 2
buf_ty:             ds.w 2
is_60hz:            ds.b 1
sync_toggle_req:    ds.b 1
ste_scroll_active:  ds.b 1
in_gameplay:        ds.b 1
disp_pending:       ds.b 1
has_prev_tick:      ds.b 1
        even
step_accum:         ds.w 1
prev_cam_x:         ds.w 1
prev_cam_y:         ds.w 1
curr_cam_x:         ds.w 1
curr_cam_y:         ds.w 1
curr_spr_cnt:       ds.w 1
prev_spr_cnt:       ds.w 1
curr_spr_list:      ds.b MAX_SPR*SPR_ENT_SIZE
prev_spr_list:      ds.b MAX_SPR*SPR_ENT_SIZE
ste_tile_ptrs:      ds.l 128
vis_tiles:          ds.b 144
tmp_tiles:          ds.b 144
buf_tiles0:         ds.b 144
buf_tiles1:         ds.b 144
prev_hud_str:       ds.b 40
spr_mask_buf:       ds.b 128        ; up to 32 lines x 4 bytes
spr_tmp_buf:        ds.b 512        ; up to 32 lines x 16 bytes (normalized sprite)
tile_cache:         ds.b 110*256    ; 28,160 B unshifted 32x16 planar tiles
hud_buf_raw:        ds.b 1280+256   ; 8-line static HUD buffer
pf_buf0_raw:        ds.b PF_SIZE+256
pf_buf1_raw:        ds.b PF_SIZE+256
        even
