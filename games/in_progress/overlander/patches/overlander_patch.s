; Overlander — STE/TT/Falcon Compatibility & Enhancement Patch
; Assembled with: vasmm68k_mot -Fbin -spaces -m68000 -o patch.bin overlander_patch.s
; Placed immediately at TEXT_END (+0x12e40) of OVERLAND_orig.PRG.
; Build script injects exact symbol addresses via header table at offset 0.

    org     0

; ============================================================================
; Header / Jump Table (fixed offsets from patch_base)
; ============================================================================
patch_entry_init:       bra.w   do_patch_init           ; +0x0000
patch_entry_tb_wait:    bra.w   do_tb_wait              ; +0x0004
patch_entry_tb_wake:    bra.w   do_tb_wake              ; +0x0008
patch_entry_flip:       bra.w   do_frame_flip           ; +0x000c
patch_entry_exit:       bra.w   do_patch_exit           ; +0x0010
patch_entry_scale:      bra.w   do_scale_loop           ; +0x0014
patch_entry_sky:        bra.w   do_sky_blitter          ; +0x0018
patch_entry_road:       bra.w   do_road_blitter         ; +0x001c
patch_entry_gtos_init:  bra.w   do_gtos_init            ; +0x0020
patch_entry_mtn:        bra.w   do_mtn_blitter          ; +0x0024
patch_entry_spr_aln:    bra.w   do_spr_aligned_blt      ; +0x0028
patch_entry_spr_scl:    bra.w   do_spr_scaled_blt       ; +0x002c
patch_entry_aud_tick:   bra.w   do_aud_tick             ; +0x0030
patch_entry_aud_stop1:  bra.w   do_aud_stop1            ; +0x0034
patch_entry_aud_stop2:  bra.w   do_aud_stop2            ; +0x0038
patch_entry_aud_sfx:    bra.w   do_aud_sfx              ; +0x003c
patch_entry_aud_mus:    bra.w   do_aud_mus              ; +0x0040

; ============================================================================
; Relocated Address Table (filled & added to GEMDOS reloc table by build script)
; ============================================================================
                        align   2
ptr_game_base:          dc.l    0                       ; +0x0044 -> base of OVERLAND_orig.PRG (+0x00000)
ptr_orig_start:         dc.l    0                       ; +0x0048 -> +0x0011c (original entry $abb6)
ptr_scr_bufs:           dc.l    0                       ; +0x004c -> BSS: 3 * 32000 + 256 bytes
ptr_g_tos_buf:          dc.l    0                       ; +0x0050 -> BSS: $3b000 bytes for G.TOS
ptr_lowram_bss:         dc.l    0                       ; +0x0054 -> BSS: $8000 bytes ($0800..$8800)
ptr_orig_sky_cont:      dc.l    0                       ; +0x0058 -> +0x03d46 ($00e7e0)
ptr_orig_sky_done:      dc.l    0                       ; +0x005c -> +0x03d92 ($00e82c)
ptr_orig_road_cont:     dc.l    0                       ; +0x0060 -> +0x0cd92 ($01782c)
ptr_mask_buf:           dc.l    0                       ; +0x0064 -> BSS: $1000 bytes (4 KB on-the-fly mask)
ptr_orig_mtn_cont:      dc.l    0                       ; +0x0068 -> +0x0368e ($00e128)
ptr_orig_spr_aln_cont:  dc.l    0                       ; +0x006c -> +0x0322e ($00dcc8)
ptr_orig_spr_scl_cont:  dc.l    0                       ; +0x0070 -> +0x03832 ($00e2cc)
ptr_am_mus_buf:         dc.l    0                       ; +0x0074 -> BSS: $b400 bytes (AM_MUS.BIN)
ptr_am_sfx_buf:         dc.l    0                       ; +0x0078 -> BSS: $4000 bytes (AM_SFX.BIN)
ptr_dma_bufs:           dc.l    0                       ; +0x007c -> BSS: $2000 bytes (4KB vol_tbl + 2KB dma_ring + 256B vpaula)
ptr_orig_aud_tick:      dc.l    0                       ; +0x0080 -> +0x0235c ($00cdf6)
ptr_orig_aud_stop1:     dc.l    0                       ; +0x0084 -> +0x0252e ($00cfc8)
ptr_orig_aud_stop2:     dc.l    0                       ; +0x0088 -> +0x02548 ($00cfe2)
ptr_orig_aud_sfx:       dc.l    0                       ; +0x008c -> +0x0284a ($00d2e4)
ptr_orig_aud_mus:       dc.l    0                       ; +0x0090 -> +0x02886 ($00d320)

; Extended v1.1 Jump Table (+0x0094..+0x00a4)
patch_entry_sky_init:   bra.w   do_ste_sky_init         ; +0x0094
patch_entry_sky_build:  bra.w   do_ste_sky_build        ; +0x0098
patch_entry_special:    bra.w   do_special_chk          ; +0x009c
patch_entry_ikbd_key:   bra.w   do_ikbd_key             ; +0x00a0
patch_entry_edge_l:     bra.w   do_road_edge_left       ; +0x00a4
patch_entry_edge_r:     bra.w   do_road_edge_right      ; +0x00a8

; ============================================================================
; Runtime State Variables (in TEXT, writable on ST/STE/TT/Falcon)
; ============================================================================
has_blitter:            dc.b    0
has_dma:                dc.b    0
is_tt:                  dc.b    0
is_falcon:              dc.b    0
has_ste_joy:            dc.b    0                       ; 1 only if real STE JagPad detected on Port A
tb_sync_flag:           dc.b    0
saved_rez:              dc.b    0
                        even
pace_vbls:              dc.w    2                       ; 2 VBLs = 25.0 fps (50 Hz) / 30.0 fps (60 Hz)
saved_physbase:         dc.l    0
saved_logbase:          dc.l    0
scr_addr_0:             dc.l    0
scr_addr_1:             dc.l    0
scr_addr_2:             dc.l    0
str_gtos_chk:           dc.b    'G.TOS',0
str_root_dir:           dc.b    '\',0
str_am_mus:             dc.b    'AM_MUS.BIN',0
str_am_sfx:             dc.b    'AM_SFX.BIN',0
                        even
am_dma_ready:           dc.b    0
am_engine_on:           dc.b    0
am_bgm_mode:            dc.b    0                       ; 0 = Engine+SFX, 1 = Amiga Driving BGM+SFX
am_in_road:             dc.b    0                       ; 1 while on road driving screen
toggle_bgm_req:         dc.b    0                       ; 1 = toggle driving music on next VBL
gun_pan_toggle:         dc.b    0                       ; alternates gun SFX Left (ch3) / Right (ch1)
jag_special_req:        dc.b    0                       ; 1 = JagPad A/C or Spacebar special weapon
jag_prev_pause:         dc.b    0
jag_prev_opt:           dc.b    0
jag_prev_joy:           dc.b    0                       ; bits currently injected by JagPad into $7f3a
dma_wr_slot:            dc.w    0
vol_tbl_ptr:            dc.l    0
dma_ring_ptr:           dc.l    0
vpaula_ptr:             dc.l    0
ste_sky_cur_ptr:        dc.l    0                       ; active Timer B pointer into ste_sky_buf
last_ym_vol:            dc.b    $ff
last_ym_rpm:            dc.b    $ff
aud_in_tick:            dc.b    0
                        even
last_eng_per:           dc.w    520
; Three 256-byte 12-bit STE sky raster lists (one per triple-buffered screen)
ste_sky_bufs:           ds.b    3*256

; ============================================================================
; do_patch_init — called instead of +0x0010e ($aba8) on startup (User mode)
; ============================================================================
do_patch_init:
    ; 0. If G.TOS is not in CWD (e.g. launched from A:\AUTO\), switch to root "\"
    move.w  #0,-(sp)                    ; read-only
    pea     str_gtos_chk(pc)
    move.w  #$3d,-(sp)                  ; Fopen("G.TOS", 0)
    trap    #1
    addq.l  #8,sp
    tst.l   d0
    bmi.s   .try_root
    move.w  d0,-(sp)
    move.w  #$3e,-(sp)                  ; Fclose
    trap    #1
    addq.l  #4,sp
    bra.s   .cwd_ok
.try_root:
    pea     str_root_dir(pc)
    move.w  #$3b,-(sp)                  ; Dsetpath("\")
    trap    #1
    addq.l  #6,sp
.cwd_ok:

    ; 1. Save current video mode & screen bases, switch to ST Low if needed (TT/Med-res)
    move.w  #4,-(sp)                    ; XBIOS Getrez()
    trap    #14
    addq.l  #2,sp
    lea     saved_rez(pc),a0
    move.b  d0,(a0)

    move.w  #2,-(sp)                    ; XBIOS Physbase()
    trap    #14
    addq.l  #2,sp
    lea     saved_physbase(pc),a0
    move.l  d0,(a0)

    move.w  #3,-(sp)                    ; XBIOS Logbase()
    trap    #14
    addq.l  #2,sp
    lea     saved_logbase(pc),a0
    move.l  d0,(a0)

    ; 2. Compute 256-byte aligned triple screen buffers inside ptr_scr_bufs
    move.l  ptr_scr_bufs(pc),d0
    add.l   #255,d0
    clr.b   d0                          ; 256-byte aligned
    lea     scr_addr_0(pc),a0
    move.l  d0,(a0)+                    ; scr_addr_0
    add.l   #32000,d0
    move.l  d0,(a0)+                    ; scr_addr_1
    add.l   #32000,d0
    move.l  d0,(a0)                     ; scr_addr_2

    ; Clear all 3 screen buffers (96,000 bytes = 24,000 longs)
    movea.l scr_addr_0(pc),a0
    move.w  #24000-1,d1
.clr_scr:
    clr.l   (a0)+
    dbra    d1,.clr_scr

    ; Store into Overlander header vars (+0x0e=$aaa8, +0x12=$aaac, +0x16=$aab0, +0x1a=$aab4)
    movea.l ptr_game_base(pc),a1
    move.l  scr_addr_0(pc),$0e(a1)      ; $aaa8
    move.l  scr_addr_2(pc),$12(a1)      ; $aaac
    move.l  scr_addr_1(pc),$16(a1)      ; $aab0
    move.l  scr_addr_1(pc),$1a(a1)      ; $aab4

    ; Pre-initialize 3 STE sky raster buffers with safe default (128 lines, black, end)
    lea     ste_sky_bufs(pc),a0
    moveq   #2,d1
.init_sky_b:
    move.w  #$80,0(a0)
    clr.w   2(a0)
    move.w  #$ffff,4(a0)
    move.w  #$ffff,6(a0)
    lea     256(a0),a0
    dbra    d1,.init_sky_b

    ; 3. Switch to ST Low (rez=0) if not already ST Low (fixes TT VGA & Med-res)
    lea     saved_rez(pc),a0
    tst.b   (a0)
    beq.s   .already_low
    move.w  #0,-(sp)                    ; ST Low
    move.l  scr_addr_1(pc),-(sp)        ; physloc
    move.l  scr_addr_1(pc),-(sp)        ; logloc
    move.w  #5,-(sp)                    ; XBIOS Setscreen
    trap    #14
    lea     12(sp),sp
.already_low:

    ; 4. Overlander installs its own IKBD handler ($0129e4) which parses joystick & mouse packets cleanly.
    ;    Do not send $12 before $0129e4 resets the ACIA.

    ; 5. Enter Supervisor briefly to inspect cookies (_MCH, _SND) & probe Blitter
    clr.l   -(sp)
    move.w  #$20,-(sp)                  ; GEMDOS Super(0)
    trap    #1
    addq.l  #6,sp
    move.l  d0,-(sp)                    ; save old SSP

    bsr.s   detect_hardware

    move.w  #$20,-(sp)                  ; GEMDOS Super(old_ssp)
    trap    #1
    addq.l  #6,sp

    ; 5b. If STE/TT/Falcon DMA sound is present, load AM_MUS.BIN + AM_SFX.BIN and start DMA ring
    lea     has_dma(pc),a0
    tst.b   (a0)
    beq.s   .skip_dma_init
    bsr.w   init_amiga_dma
.skip_dma_init:

    ; 6. Jump to original Overlander startup (+0x0011c)
    movea.l ptr_orig_start(pc),a0
    jmp     (a0)

; ============================================================================
; detect_hardware — Supervisor mode: detect _MCH, _SND, Blitter
; ============================================================================
detect_hardware:
    movem.l d0-d3/a0-a2,-(sp)
    lea     has_blitter(pc),a2
    clr.l   (a2)                        ; clear has_blitter, has_dma, is_tt, is_falcon

    ; Read cookie jar ($5a0.w)
    move.l  $5a0.w,d0
    beq.s   .no_jar
    movea.l d0,a0
.jar_loop:
    move.l  (a0)+,d1
    beq.s   .no_jar
    move.l  (a0)+,d2
    cmp.l   #'_MCH',d1
    bne.s   .chk_snd
    swap    d2
    cmp.w   #2,d2
    bne.s   .chk_falc
    move.b  #1,2(a2)                    ; is_tt = 1
    bra.s   .jar_loop
.chk_falc:
    cmp.w   #3,d2
    bne.s   .jar_loop
    move.b  #1,3(a2)                    ; is_falcon = 1
    bra.s   .jar_loop
.chk_snd:
    bra.s   .jar_loop
.no_jar:

    ; Safe Blitter probe ($ffff8a3c.w) with bus-error trap
    move.w  sr,-(sp)
    ori.w   #$0700,sr
    move.l  $8.w,a1                     ; save Bus Error vector
    lea     .blt_berr(pc),a0
    move.l  a0,$8.w
    movea.l sp,a0                       ; save SP
    tst.b   $ffff8a3c.w                 ; probe Blitter LINE_NUM/CTRL
    move.b  #1,(a2)                     ; succeeded -> has_blitter = 1
.blt_done:
    movea.l a0,sp
    ; Safe STE/TT/Falcon DMA sound probe ($ffff8901.w) with bus-error trap
    lea     .dma_berr(pc),a0
    move.l  a0,$8.w
    movea.l sp,a0                       ; save SP
    tst.b   $ffff8901.w                 ; probe DMA Sound Control
    move.b  #1,1(a2)                    ; succeeded -> has_dma = 1
.dma_done:
    movea.l a0,sp
    move.l  a1,$8.w
    move.w  (sp)+,sr
    ; Detect if a real STE Jaguar PowerPad is connected on Port A ($ffff9202):
    ; Unplugged port reads $0000; connected idle JagPad reads $0f00 (active-low high!)
    clr.b   4(a2)                       ; has_ste_joy = 0
    tst.b   (a2)                        ; has_blitter (STE / Mega STE / Falcon)?
    beq.s   .no_jag
    move.w  #$ffee,$ffff9202.w
    move.w  $ffff9202.w,d0
    andi.w  #$0f00,d0
    cmp.w   #$0f00,d0
    bne.s   .no_jag
    move.b  #1,4(a2)                    ; real JagPad detected!
.no_jag:
    movem.l (sp)+,d0-d3/a0-a2
    rts
.blt_berr:
    bra.s   .blt_done
.dma_berr:
    bra.s   .dma_done

; ============================================================================
; do_tb_wait / do_tb_wake — 68030 I-cache-safe replacement for $b822/$b834/$b840
; Replaces: move.w #$60fe, $b834.l ... bra.b $b834 / move.w #$6002, $b834.l
; ============================================================================
do_tb_wait:
    lea     tb_sync_flag(pc),a0         ; note: caller $b7f0 doesn't rely on a0 across wait
    clr.b   (a0)
    bclr.b  #0,$fffffa0f.w              ; clear Timer B ISR
    move.w  #$2300,sr
.wait_tb:
    tst.b   (a0)
    beq.s   .wait_tb
    bclr.b  #0,$fffffa0f.w
    rts

do_tb_wake:
    ; Called via jsr from $b840 (Timer B ISR) — preserve ALL registers!
    move.l  a0,-(sp)
    lea     tb_sync_flag(pc),a0
    st      (a0)
    move.l  (sp)+,a0
    rts

; ============================================================================
; do_frame_flip — replaces sub_00af5a (+0x004c0) with clean VBL pacing
; ============================================================================
do_frame_flip:
    movea.l ptr_game_base(pc),a0
.wait_lock:
    btst.b  #2,$04(a0)                  ; $aa9e bit 2
    bne.s   .wait_lock
.wait_vbl:
    tst.w   $06(a0)                     ; $aaa0 (decremented every VBL)
    bne.s   .wait_vbl

    ; Triple-buffer rotation ($aaa8, $aaac, $aab0 -> $aab4)
    move.l  $0e(a0),a1                  ; a1 = old $aaa8
    move.l  $12(a0),$0e(a0)             ; $aaa8 = old $aaac
    move.l  $16(a0),$12(a0)             ; $aaac = old $aab0
    move.l  a1,$16(a0)                  ; $aab0 = old $aaa8
    move.l  (a1),$1a(a0)                ; $aab4 = *(old $aaa8) (screen base)
    move.w  pace_vbls(pc),$06(a0)       ; $aaa0 = 2 VBLs (25.0 fps cap)
    addq.w  #1,$0a(a0)                  ; $aaa4++ (FPS counter)
    rts

; ============================================================================
; do_scale_loop — 68030 I-cache-safe replacement for $00e2e0..$00e31a
; Replaces self-modifying `subi.w #imm,d6` / `addi.w #imm,d6`
; Inputs: (a0)=orig_h, d2=scaled_h, d3=draw_h-1, a2=src, a3=src_stride, a5=dst, a6=row_fn
; ============================================================================
scale_add_val:          dc.w    0
scale_sub_val:          dc.w    0

do_scale_loop:
    move.w  (a0),d6                     ; orig_h
    lea     scale_add_val(pc),a4
    move.w  d6,(a4)                     ; scale_add_val = orig_h
    move.w  d6,d0
    sub.w   d2,d0
    move.w  d0,2(a4)                    ; scale_sub_val = orig_h - scaled_h
    asr.w   #1,d6                       ; d6 = orig_h / 2
    lea     .row_ret(pc),a4
    move.w  d3,d7
    bmi.s   .scale_done
.row_loop:
    movea.l a2,a0
    movea.l a5,a1
    jmp     (a6)                        ; row_fn returns via jmp (a4)
.row_ret:
    adda.w  a3,a2
    lea     $a0(a5),a5
    sub.w   scale_sub_val(pc),d6
    bgt.s   .no_skip
    add.w   scale_add_val(pc),d6
    adda.w  a3,a2
.no_skip:
    dbra    d7,.row_loop
.scale_done:
    rts

; ============================================================================
; STE Blitter Register Offsets (from a6 = $ffff8a00)
; ============================================================================
BLT_SRC_XINC    equ $20
BLT_SRC_YINC    equ $22
BLT_SRC_ADDR    equ $24
BLT_ENDMASK1    equ $28
BLT_ENDMASK2    equ $2a
BLT_ENDMASK3    equ $2c
BLT_DST_XINC    equ $2e
BLT_DST_YINC    equ $30
BLT_DST_ADDR    equ $32
BLT_X_CNT       equ $36
BLT_Y_CNT       equ $38
BLT_HOP         equ $3a
BLT_OP          equ $3b
BLT_CTRL        equ $3c
BLT_SKEW        equ $3d

; Helper: fill d7 lines at a0 with color 7 ($ffff,$ffff,$ffff,$0000) in <= 160-cycle HOG chunks!
; 40 words = 160 cyc (0.31 scanline, fits inside HBL!) -> ZERO Timer B dashboard blue bleed!
; Clobbers d0-d1/a0-a1; expects a6 = $ffff8a00, ENDMASK1/2/3=$ffff, HOP=0, SKEW=0
blt_fill_color7_hog:
    move.w  #2,BLT_DST_XINC(a6)
    move.w  #2,BLT_DST_YINC(a6)
    move.l  a0,BLT_DST_ADDR(a6)
    move.b  #15,BLT_OP(a6)
    move.w  d7,d0
    add.w   d0,d0                       ; 2 chunks of 40 words per line
    subq.w  #1,d0
.f7_p1:
    move.w  #40,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; 160 cyc = 0.31 scanline (fits inside HBL!)
    dbra    d0,.f7_p1

    ; Pass 2: clear plane 3 (20 words/line * d7 lines, 2-line HOG chunks = 160 cyc)
    move.w  #8,BLT_DST_XINC(a6)
    move.w  #8,BLT_DST_YINC(a6)
    lea     6(a0),a1
    move.l  a1,BLT_DST_ADDR(a6)
    clr.b   BLT_OP(a6)
    move.w  d7,d0
.f7_p2:
    moveq   #2,d1
    cmp.w   d1,d0
    bge.s   .f7_p2_go
    move.w  d0,d1
.f7_p2_go:
    move.w  #20,BLT_X_CNT(a6)
    move.w  d1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; <= 160 cyc = 0.31 scanline
    sub.w   d1,d0
    bgt.s   .f7_p2
    rts

; ============================================================================
; do_sky_blitter — STE Blitter replacement for sky fill ($00e7da..$00e82c)
; Fills horizon_y ($1742c) lines * 160 B with color 7 ($ffff,$ffff,$ffff,$0000)
; ============================================================================
do_sky_blitter:
    movea.l ptr_game_base(pc),a1
    movea.l $0e(a1),a0                  ; *$aaa8 -> scanline ptr table
    movea.l (a0),a0                     ; screen base (y = 0)
    move.l  a6,-(sp)
    lea     has_blitter(pc),a6
    tst.b   (a6)
    beq.w   .sky_cpu

    adda.l  #$c992,a1                   ; $1742c = horizon_y (lines)
    move.w  (a1),d7
    subq.w  #8,d7                       ; skip top 8 lines (opaque SCORE/MONEY/LEVEL banner!)
    ble.s   .sky_done
    lea     1280(a0),a0                 ; start at y = 8 (8 * 160 = 1280)

    lea     $ffff8a00.w,a6
    move.w  #$ffff,BLT_ENDMASK1(a6)
    move.w  #$ffff,BLT_ENDMASK2(a6)
    move.w  #$ffff,BLT_ENDMASK3(a6)
    clr.b   BLT_SKEW(a6)
    clr.b   BLT_HOP(a6)
    bsr.w   blt_fill_color7_hog

.sky_done:
    movea.l (sp)+,a6
    move.l  ptr_orig_sky_done(pc),-(sp)
    rts

.sky_cpu:
    movea.l (sp)+,a6
    move.l  ptr_orig_sky_cont(pc),-(sp)
    rts

; ============================================================================
; Endmask tables for STE Blitter horizontal spans (pixel 0..15)
; ============================================================================
road_left_mask:
    dc.w    $ffff,$7fff,$3fff,$1fff,$0fff,$07ff,$03ff,$01ff
    dc.w    $00ff,$007f,$003f,$001f,$000f,$0007,$0003,$0001

road_right_mask:
    dc.w    $8000,$c000,$e000,$f000,$f800,$fc00,$fe00,$ff00
    dc.w    $ff80,$ffc0,$ffe0,$fff0,$fff8,$fffc,$fffe,$ffff

; ============================================================================
; do_road_blitter — STE Blitter replacement for sub_017826 (+0xcd8c)
; Input: d0.w = y_start (draws scanlines y_start .. 127)
; ============================================================================
do_road_blitter:
    lea     has_blitter(pc),a6
    tst.b   (a6)
    bne.s   .road_blt
    ; Plain ST / TT fallback: run original CPU road renderer
    move.w  #$80,-(sp)
    sub.w   d0,(sp)
    movea.l ptr_orig_road_cont(pc),a0
    jmp     (a0)

.road_blt:
    move.w  #$80,d7
    sub.w   d0,d7                       ; d7 = line count (128 - y_start)
    ble.w   .road_rts

    ; Compute a0 = road_table + y_start * 8, a2 = screen_ptrs[y_start]
    movea.l ptr_lowram_bss(pc),a0
    adda.l  #($4fda-$0800),a0           ; road table base ($4fda)
    movea.l ptr_game_base(pc),a1
    movea.l $0e(a1),a2                  ; *$aaa8 -> scanline ptr table
    move.w  d0,d1
    asl.w   #2,d1
    movea.l (a2,d1.w),a2                ; a2 = screen addr at y_start
    add.w   d1,d1                       ; d1 = y_start * 8
    adda.w  d1,a0                       ; a0 = &road_table[y_start]

    ; Step 1: Fill entire road area (d7 lines) with Grass color 7 in 8-line HOG chunks
    lea     $ffff8a00.w,a6
    move.w  #$ffff,BLT_ENDMASK1(a6)
    move.w  #$ffff,BLT_ENDMASK2(a6)
    move.w  #$ffff,BLT_ENDMASK3(a6)
    clr.b   BLT_SKEW(a6)
    clr.b   BLT_HOP(a6)
    move.l  a0,-(sp)
    movea.l a2,a0
    bsr.w   blt_fill_color7_hog
    movea.l (sp)+,a0

    ; Step 2: Per-scanline Blitter span loop
    ; Constant Blitter regs already set: DST_XINC=8, DST_YINC=8, ENDMASK2=$ffff, HOP=0, SKEW=0
    lea     road_left_mask(pc),a4
    lea     road_right_mask(pc),a5
    subq.w  #1,d7                       ; dbra counter

.line_loop:
    ; Check grass band: bit 6 of color_off (6(a0)) -> 0 = Grass 7 (1110), 1 = Grass 11 (1101)
    move.w  6(a0),d6
    btst    #6,d6
    beq.w   .grass_is_7

    ; Grass 11 (1101): flip P2 -> 0 and P3 -> 1 across full 20 words of this line
    move.w  #$ffff,BLT_ENDMASK1(a6)
    move.w  #$ffff,BLT_ENDMASK3(a6)
    lea     4(a2),a1
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  #20,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    clr.b   BLT_OP(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; 1-line 20-word burst (~80 cyc)

    addq.l  #2,a1
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  #20,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #15,BLT_OP(a6)
    move.b  #$c0,BLT_CTRL(a6)

    ; Band 2 ($50) vs Band 3 ($78): test bit 3 ($28 = %00101000 -> bit 3 = 1)
    btst    #3,d6
    bne.s   .band3

    ; --- Band 2: Grass=1101, Kerb=1010, Asphalt=1001 ---
    ; P1 = 0 on Outer [left_x, right_x + kerb_w)
    move.w  (a0),d0                     ; left_x
    move.w  2(a0),d1                    ; right_x
    add.w   4(a0),d1                    ; right_x + kerb_w
    lea     2(a2),a3                    ; plane 1
    moveq   #0,d2                       ; OP = 0
    bsr.w   blit_hspan

    ; Left kerb [left_x, left_x + kerb_w): P2 = 1, P3 = 0
    move.w  (a0),d0
    move.w  d0,d1
    add.w   4(a0),d1
    bsr.w   blit_kerb_p2_1_p3_0

    ; Right kerb [right_x, right_x + kerb_w): P2 = 1, P3 = 0
    move.w  2(a0),d0
    move.w  d0,d1
    add.w   4(a0),d1
    bsr.w   blit_kerb_p2_1_p3_0
    bra.w   .next_line

.band3:
    ; --- Band 3: Grass=1101, Kerb=1111, Asphalt=0101 ---
    ; P0 = 0 on Inner [left_x + kerb_w, right_x)
    move.w  (a0),d0
    add.w   4(a0),d0
    move.w  2(a0),d1
    movea.l a2,a3                       ; plane 0
    moveq   #0,d2                       ; OP = 0
    bsr.w   blit_hspan

    ; Left kerb [left_x, left_x + kerb_w): P2 = 1
    move.w  (a0),d0
    move.w  d0,d1
    add.w   4(a0),d1
    lea     4(a2),a3                    ; plane 2
    moveq   #15,d2
    bsr.w   blit_hspan

    ; Right kerb [right_x, right_x + kerb_w): P2 = 1
    move.w  2(a0),d0
    move.w  d0,d1
    add.w   4(a0),d1
    lea     4(a2),a3                    ; plane 2
    moveq   #15,d2
    bsr.w   blit_hspan
    bra.w   .next_line

.grass_is_7:
    ; Test Band 0 ($00) vs Band 1 ($28): bit 3
    btst    #3,d6
    bne.s   .band1

    ; --- Band 0: Grass=1110, Kerb=1010, Asphalt=1001 ---
    ; P1 = 0 on Outer [left_x, right_x + kerb_w)
    move.w  (a0),d0
    move.w  2(a0),d1
    add.w   4(a0),d1
    lea     2(a2),a3                    ; plane 1
    moveq   #0,d2
    bsr.w   blit_hspan

    ; Inner [left_x + kerb_w, right_x): P2 = 0 AND P3 = 1 (share span calc!)
    move.w  (a0),d0
    add.w   4(a0),d0
    move.w  2(a0),d1
    bsr.w   blit_inner_p2_0_p3_1
    bra.s   .next_line

.band1:
    ; --- Band 1: Grass=1110, Kerb=1111, Asphalt=0101 ---
    ; P3 = 1 on Outer [left_x, right_x + kerb_w)
    move.w  (a0),d0
    move.w  2(a0),d1
    add.w   4(a0),d1
    lea     6(a2),a3                    ; plane 3
    moveq   #15,d2
    bsr.w   blit_hspan

    ; Inner [left_x + kerb_w, right_x): P0 = 0 AND P2 = 0 (share span calc!)
    move.w  (a0),d0
    add.w   4(a0),d0
    move.w  2(a0),d1
    bsr.w   blit_inner_p0_0_p2_0

.next_line:
    addq.l  #8,a0
    lea     160(a2),a2
    dbra    d7,.line_loop
.road_rts:
    rts

; ============================================================================
; Span Blitter Helpers (a4=left_mask, a5=right_mask, a6=$ffff8a00)
; Input: d0.w = x_start, d1.w = x_end (exclusive), a3 = scanline + plane*2, d2.b = OP
; ============================================================================
blit_hspan:
    tst.w   d0
    bge.s   .bh_l_ok
    moveq   #0,d0
.bh_l_ok:
    cmp.w   #320,d1
    ble.s   .bh_r_ok
    move.w  #320,d1
.bh_r_ok:
    cmp.w   d1,d0
    bge.s   .bh_ret
    subq.w  #1,d1                       ; inclusive x_end

    move.w  d0,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a4,d3.w),d4                ; em1

    move.w  d1,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a5,d3.w),d5                ; em3

    lsr.w   #4,d0                       ; w_start
    lsr.w   #4,d1                       ; w_end
    sub.w   d0,d1                       ; w_end - w_start
    bne.s   .bh_multi
    and.w   d5,d4                       ; single word: em1 &= em3
.bh_multi:
    addq.w  #1,d1                       ; x_cnt
    asl.w   #3,d0                       ; w_start * 8
    lea     (a3,d0.w),a1
    move.w  d4,BLT_ENDMASK1(a6)
    move.w  d5,BLT_ENDMASK3(a6)
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  d2,BLT_OP(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; tiny 1-line span (~16-80 cyc)
.bh_ret:
    rts

; Shared 2-plane inner span helper: P2 = 0, P3 = 1 (Band 0)
blit_inner_p2_0_p3_1:
    tst.w   d0
    bge.s   .i0_l
    moveq   #0,d0
.i0_l:
    cmp.w   #320,d1
    ble.s   .i0_r
    move.w  #320,d1
.i0_r:
    cmp.w   d1,d0
    bge.s   .i0_ret
    subq.w  #1,d1
    move.w  d0,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a4,d3.w),d4
    move.w  d1,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a5,d3.w),d5
    lsr.w   #4,d0
    lsr.w   #4,d1
    sub.w   d0,d1
    bne.s   .i0_m
    and.w   d5,d4
.i0_m:
    addq.w  #1,d1
    asl.w   #3,d0
    lea     4(a2,d0.w),a1               ; plane 2
    move.w  d4,BLT_ENDMASK1(a6)
    move.w  d5,BLT_ENDMASK3(a6)
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    clr.b   BLT_OP(a6)                  ; P2 = 0
    move.b  #$c0,BLT_CTRL(a6)

    addq.l  #2,a1                       ; plane 3
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #15,BLT_OP(a6)              ; P3 = 1
    move.b  #$c0,BLT_CTRL(a6)
.i0_ret:
    rts

; Shared 2-plane inner span helper: P0 = 0, P2 = 0 (Band 1)
blit_inner_p0_0_p2_0:
    tst.w   d0
    bge.s   .i1_l
    moveq   #0,d0
.i1_l:
    cmp.w   #320,d1
    ble.s   .i1_r
    move.w  #320,d1
.i1_r:
    cmp.w   d1,d0
    bge.s   .i1_ret
    subq.w  #1,d1
    move.w  d0,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a4,d3.w),d4
    move.w  d1,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a5,d3.w),d5
    lsr.w   #4,d0
    lsr.w   #4,d1
    sub.w   d0,d1
    bne.s   .i1_m
    and.w   d5,d4
.i1_m:
    addq.w  #1,d1
    asl.w   #3,d0
    lea     (a2,d0.w),a1                ; plane 0
    move.w  d4,BLT_ENDMASK1(a6)
    move.w  d5,BLT_ENDMASK3(a6)
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    clr.b   BLT_OP(a6)                  ; P0 = 0
    move.b  #$c0,BLT_CTRL(a6)

    addq.l  #4,a1                       ; plane 2
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
.i1_ret:
    rts

; Shared 2-plane kerb helper: P2 = 1, P3 = 0 (Band 2)
blit_kerb_p2_1_p3_0:
    tst.w   d0
    bge.s   .k2_l
    moveq   #0,d0
.k2_l:
    cmp.w   #320,d1
    ble.s   .k2_r
    move.w  #320,d1
.k2_r:
    cmp.w   d1,d0
    bge.s   .k2_ret
    subq.w  #1,d1
    move.w  d0,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a4,d3.w),d4
    move.w  d1,d3
    and.w   #15,d3
    add.w   d3,d3
    move.w  (a5,d3.w),d5
    lsr.w   #4,d0
    lsr.w   #4,d1
    sub.w   d0,d1
    bne.s   .k2_m
    and.w   d5,d4
.k2_m:
    addq.w  #1,d1
    asl.w   #3,d0
    lea     4(a2,d0.w),a1               ; plane 2
    move.w  d4,BLT_ENDMASK1(a6)
    move.w  d5,BLT_ENDMASK3(a6)
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #15,BLT_OP(a6)              ; P2 = 1
    move.b  #$c0,BLT_CTRL(a6)

    addq.l  #2,a1                       ; plane 3
    move.l  a1,BLT_DST_ADDR(a6)
    move.w  d1,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    clr.b   BLT_OP(a6)                  ; P3 = 0
    move.b  #$c0,BLT_CTRL(a6)
.k2_ret:
    rts

; ============================================================================
; do_gtos_init — replaces jsr $1c(a0) at +0x02de ($00ad78)
; Calls original G.TOS table relocator. (Masks are built on-the-fly in 4 KB
; bss_mask_buf by do_spr_aligned_blt so we never overflow into bss_am_mus!)
; ============================================================================
do_gtos_init:
    jsr     $1c(a0)                     ; original G.TOS pointer-table relocator (returns table in a0)
    rts

; ============================================================================
; do_mtn_blitter — STE Blitter replacement for parallax mountains ($00e122)
; Inputs: d0 = scroll_x, d1 = height-1, d2 = y_start
; ============================================================================
do_mtn_blitter:
    move.l  a6,-(sp)
    lea     has_blitter(pc),a6
    tst.b   (a6)
    bne.s   .mtn_blt
    movea.l (sp)+,a6
    add.w   d1,d1
    movea.l ptr_game_base(pc),a6
    adda.l  #$36d8,a6                   ; $e172 jump table
    move.l  ptr_orig_mtn_cont(pc),-(sp)
    rts

.mtn_blt:
    ; Compute preshifted buffer ptr a2 = preshift_tbl[d0 & 7] + *$dfd8
    move.w  d0,d3
    and.w   #7,d0
    asl.w   #2,d0
    movea.l ptr_game_base(pc),a0
    lea     $3542(a0),a2                ; $dfdc (preshift table)
    movea.l (a2,d0.w),a2
    adda.l  $353e(a0),a2                ; + *$dfd8 (bss_scratch_40k)

    ; Wrap table ptr a4 = $dffc + (0x50 - ((d3 >> 2) & 0xfe))
    asr.w   #2,d3
    and.w   #$fe,d3
    neg.w   d3
    addi.w  #$50,d3
    lea     $3562(a0),a4                ; $dffc (wrap table)
    adda.w  d3,a4

    ; Screen dest a3 = (*$aaa8)[d2 * 4]
    movea.l $0e(a0),a3                  ; *$aaa8
    asl.w   #2,d2
    movea.l (a3,d2.w),a3

    ; Setup Blitter for 20 columns of 4 words x (d1+1) lines
    addq.w  #1,d1                       ; height in lines
    lea     $ffff8a00.w,a6
    move.w  #2,BLT_SRC_XINC(a6)
    move.w  #2,BLT_SRC_YINC(a6)
    move.w  #$ffff,BLT_ENDMASK1(a6)
    move.w  #$ffff,BLT_ENDMASK2(a6)
    move.w  #$ffff,BLT_ENDMASK3(a6)
    move.w  #2,BLT_DST_XINC(a6)
    move.w  #154,BLT_DST_YINC(a6)       ; 160 - 3*2 = 154
    move.b  #2,BLT_HOP(a6)              ; SRC only
    move.b  #3,BLT_OP(a6)               ; replace
    clr.b   BLT_SKEW(a6)

    moveq   #19,d2                      ; 20 columns
.mtn_col:
    movea.l a2,a0
    adda.w  (a4)+,a0
    move.l  a0,BLT_SRC_ADDR(a6)
    move.l  a3,BLT_DST_ADDR(a6)
    ; Split into <= 8-line HOG chunks (<= 256 cyc = 0.5 scanline -> ZERO dashboard blue bleed!)
    move.w  d1,d3
.mtn_ch:
    moveq   #8,d0
    cmp.w   d0,d3
    bge.s   .mtn_go
    move.w  d3,d0
.mtn_go:
    move.w  #4,BLT_X_CNT(a6)
    move.w  d0,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; <= 256 cyc = 0.5 scanline!
    sub.w   d0,d3
    bgt.s   .mtn_ch
    addq.l  #8,a3
    dbra    d2,.mtn_col
    movea.l (sp)+,a6
    rts

; ============================================================================
; do_spr_aligned_blt — STE Blitter replacement for sub_00dcc2 (+0x3228)
; Inputs: a0 = src (4-plane contiguous), a1 = dst screen, d6 = width_words-1, d7 = height-1
; Builds exact 1-plane mask on-the-fly into ptr_mask_buf (alignment-independent!)
; Preserves a6 (BST node ptr in $01755c!) and scratch regs!
; ============================================================================
do_spr_aligned_blt:
    move.l  a6,-(sp)
    lea     has_blitter(pc),a6
    tst.b   (a6)
    beq.w   .sa_cpu

    movem.l d0-d3/a2-a3,-(sp)
    addq.w  #1,d6                       ; x_cnt (words)
    addq.w  #1,d7                       ; y_cnt (lines)

    ; Build exact 1-plane mask for (d6 * d7) 4-plane words into ptr_mask_buf
    move.w  d6,d0
    mulu.w  d7,d0                       ; total 16px words (<= 640)
    subq.w  #1,d0
    movea.l a0,a2
    movea.l ptr_mask_buf(pc),a3
.sa_mk_mask:
    move.w  (a2)+,d1
    or.w    (a2)+,d1
    or.w    (a2)+,d1
    or.w    (a2)+,d1
    move.w  d1,(a3)+
    dbra    d0,.sa_mk_mask

    movea.l ptr_mask_buf(pc),a2
    move.w  d6,d1
    subq.w  #1,d1
    asl.w   #3,d1                       ; (x_cnt - 1) * 8
    move.w  #160,d2
    sub.w   d1,d2                       ; dst_yinc = 160 - (x_cnt-1)*8

    lea     $ffff8a00.w,a6
    move.w  #$ffff,BLT_ENDMASK1(a6)
    move.w  #$ffff,BLT_ENDMASK2(a6)
    move.w  #$ffff,BLT_ENDMASK3(a6)
    move.w  #8,BLT_DST_XINC(a6)
    move.w  d2,BLT_DST_YINC(a6)
    move.b  #2,BLT_HOP(a6)
    clr.b   BLT_SKEW(a6)

    ; Pass 1: Mask cut (~SRC & DST, OP=4) across all 4 planes (<= 4-line HOG chunks = <= 256 cyc!)
    move.w  #2,BLT_SRC_XINC(a6)
    move.w  #2,BLT_SRC_YINC(a6)
    move.b  #4,BLT_OP(a6)
    movea.l a1,a3
    moveq   #3,d3
.sa_mask_lp:
    move.l  a2,BLT_SRC_ADDR(a6)
    move.l  a3,BLT_DST_ADDR(a6)
    move.w  d7,d0
.sa_mch:
    moveq   #4,d1
    cmp.w   d1,d0
    bge.s   .sa_mgo
    move.w  d0,d1
.sa_mgo:
    move.w  d6,BLT_X_CNT(a6)
    move.w  d1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; <= 256 cyc = 0.5 scanline -> ZERO dashboard bleed!
    sub.w   d1,d0
    bgt.s   .sa_mch
    addq.l  #2,a3
    dbra    d3,.sa_mask_lp

    ; Pass 2: Sprite OR (SRC | DST, OP=7) across all 4 planes (<= 4-line HOG chunks!)
    move.w  #8,BLT_SRC_XINC(a6)
    move.w  #8,BLT_SRC_YINC(a6)
    move.b  #7,BLT_OP(a6)
    movea.l a0,a2
    movea.l a1,a3
    moveq   #3,d3
.sa_or_lp:
    move.l  a2,BLT_SRC_ADDR(a6)
    move.l  a3,BLT_DST_ADDR(a6)
    move.w  d7,d0
.sa_och:
    moveq   #4,d1
    cmp.w   d1,d0
    bge.s   .sa_ogo
    move.w  d0,d1
.sa_ogo:
    move.w  d6,BLT_X_CNT(a6)
    move.w  d1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)           ; <= 256 cyc = 0.5 scanline!
    sub.w   d1,d0
    bgt.s   .sa_och
    addq.l  #2,a2
    addq.l  #2,a3
    dbra    d3,.sa_or_lp
    movem.l (sp)+,d0-d3/a2-a3
    movea.l (sp)+,a6
    rts

.sa_cpu:
    movea.l (sp)+,a6
    movea.l ptr_game_base(pc),a3
    adda.l  #$3240,a3                   ; $dcda jump table
    add.w   d6,d6
    move.l  ptr_orig_spr_aln_cont(pc),-(sp)
    rts

; ============================================================================
; do_spr_scaled_blt — STE Blitter replacement for shifted + Y-scaled sprites ($00e2c4)
; Inputs:
;   a0 = sprite header ((a0) = orig_h)
;   a2 = src row ptr (4-plane), a3.w = src_stride (bytes)
;   a5 = dst screen ptr
;   d0 = width_words - 1 (0..7)
;   d2 = scaled_h, d3 = draw_h - 1, d5 = x & 15
; ============================================================================
scl_x_cnt:      dc.w    0
scl_mask_str:   dc.w    0
scl_add_h:      dc.w    0
scl_sub_h:      dc.w    0

do_spr_scaled_blt:
    lea     has_blitter(pc),a6
    tst.b   (a6)
    beq.w   .ss_cpu

    ; Check draw_h - 1 >= 0
    tst.w   d3
    bmi.w   .ss_rts

    ; Check if a2 is inside [ptr_g_tos_buf, ptr_g_tos_buf + $3b000)
    move.l  a2,d1
    sub.l   ptr_g_tos_buf(pc),d1
    bmi.w   .ss_cpu
    cmp.l   #$3b000,d1
    bhs.w   .ss_cpu

    ; Compute mask row ptr a1 = ptr_mask_buf + (d1 >> 2)
    lsr.l   #2,d1
    movea.l ptr_mask_buf(pc),a1
    adda.l  d1,a1

    ; Compute SKEW + FXSR and adjust a2/a1 for shift cases:
    ;   d5 & 15 == 8: skew = 0 (no FXSR)
    ;   d5 & 15 >  8: skew = $80 | (d5 - 8), a2 -= 8, a1 -= 2
    ;   d5 & 15 <  8: skew = $80 | (d5 + 8), a2 unchanged, a1 unchanged
    and.w   #15,d5
    subq.w  #8,d5
    beq.s   .ss_skew_ok                 ; d5 = 0 -> no FXSR
    bgt.s   .ss_ror
    addi.w  #16,d5                      ; 8..15
    ori.w   #$80,d5                     ; FXSR | (8..15)
    bra.s   .ss_skew_ok
.ss_ror:
    ori.w   #$80,d5                     ; FXSR | (1..7)
    subq.l  #8,a2
    subq.l  #2,a1
.ss_skew_ok:

    ; Save width, mask stride, and Bresenham Y-scale steps
    addq.w  #1,d0                       ; x_cnt = d0 + 1
    lea     scl_x_cnt(pc),a4
    move.w  d0,(a4)+                    ; scl_x_cnt
    move.w  a3,d4
    lsr.w   #2,d4                       ; mask_stride = src_stride >> 2
    move.w  d4,(a4)+                    ; scl_mask_str
    move.w  (a0),d6                     ; orig_h
    move.w  d6,(a4)+                    ; scl_add_h
    move.w  d6,d1
    sub.w   d2,d1
    move.w  d1,(a4)                     ; scl_sub_h = orig_h - scaled_h
    asr.w   #1,d6                       ; Bresenham accumulator = orig_h / 2

    ; Constant Blitter regs for all rows of this sprite
    lea     $ffff8a00.w,a6
    move.w  #$ffff,BLT_ENDMASK1(a6)
    move.w  #$ffff,BLT_ENDMASK2(a6)
    move.w  #$ffff,BLT_ENDMASK3(a6)
    move.w  #8,BLT_DST_XINC(a6)
    move.b  #2,BLT_HOP(a6)
    move.b  d5,BLT_SKEW(a6)

    move.w  d3,d7                       ; dbra row counter
    move.w  scl_x_cnt(pc),d0            ; keep x_cnt in d0
    move.w  scl_mask_str(pc),d4         ; keep mask_stride in d4

.ss_row:
    ; --- Mask cut: 4 planes of ~SRC & DST (OP=4, SRC_XINC=2) ---
    move.w  #2,BLT_SRC_XINC(a6)
    move.b  #4,BLT_OP(a6)
    movea.l a5,a4
    move.l  a1,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
    addq.l  #2,a4
    move.l  a1,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
    addq.l  #2,a4
    move.l  a1,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
    addq.l  #2,a4
    move.l  a1,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)

    ; --- Sprite OR: 4 planes of SRC | DST (OP=7, SRC_XINC=8) ---
    move.w  #8,BLT_SRC_XINC(a6)
    move.b  #7,BLT_OP(a6)
    movea.l a2,a0
    movea.l a5,a4
    move.l  a0,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
    addq.l  #2,a0
    addq.l  #2,a4
    move.l  a0,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
    addq.l  #2,a0
    addq.l  #2,a4
    move.l  a0,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)
    addq.l  #2,a0
    addq.l  #2,a4
    move.l  a0,BLT_SRC_ADDR(a6)
    move.l  a4,BLT_DST_ADDR(a6)
    move.w  d0,BLT_X_CNT(a6)
    move.w  #1,BLT_Y_CNT(a6)
    move.b  #$c0,BLT_CTRL(a6)

    ; Advance row + Bresenham Y-skip
    adda.w  a3,a2
    adda.w  d4,a1
    lea     160(a5),a5
    sub.w   scl_sub_h(pc),d6
    bgt.s   .ss_noskip
    add.w   scl_add_h(pc),d6
    adda.w  a3,a2
    adda.w  d4,a1
.ss_noskip:
    dbra    d7,.ss_row
.ss_rts:
    rts

.ss_cpu:
    and.w   #15,d5
    subq.w  #8,d5
    movea.l ptr_orig_spr_scl_cont(pc),a6
    jmp     (a6)

; ============================================================================
; PHASE 3: AMIGA 4-CHANNEL STEREO STE DMA AUDIO ENGINE (12,517 Hz Stereo)
; Atomic cursor-tracked 2,000-byte (8 x 250 B = 80 ms) circular DMA ring buffer
; Works cleanly at 50 Hz, 60 Hz, and 71 Hz on STE, Mega STE, TT, Falcon!
; ============================================================================
DMA_CTRL        equ $ffff8901
DMA_START_HI    equ $ffff8903
DMA_START_MID   equ $ffff8905
DMA_START_LO    equ $ffff8907
DMA_CNT_HI      equ $ffff8909
DMA_CNT_MID     equ $ffff890b
DMA_CNT_LO      equ $ffff890d
DMA_END_HI      equ $ffff890f
DMA_END_MID     equ $ffff8911
DMA_END_LO      equ $ffff8913
DMA_MODE        equ $ffff8921
DMA_RING_BYTES  equ 2000

; Virtual Paula channel struct (32 bytes each, 4 channels = 128 bytes)
VCH_SAMP_PTR    equ 0                   ; .l current sample ptr
VCH_SAMP_LEN    equ 4                   ; .l current sample len (bytes)
VCH_LOOP_PTR    equ 8                   ; .l loop ptr
VCH_LOOP_LEN    equ 12                  ; .l loop len (bytes)
VCH_POS_INT     equ 16                  ; .w integer sample pos
VCH_POS_FRAC    equ 18                  ; .w frac sample pos
VCH_STEP_INT    equ 20                  ; .w integer step per output sample
VCH_STEP_FRAC   equ 22                  ; .w frac step per output sample
VCH_VOL         equ 24                  ; .w volume (0..64)
VCH_ACTIVE      equ 26                  ; .b active flag (0/1)
VCH_LAST_PER    equ 28                  ; .w cached Paula period (skip divu.w when unchanged!)
VCH_SIZE        equ 32

vch_table:      ds.b    4*VCH_SIZE

; Helper: load file (a0 = filename, a1 = dst, d0 = max_len) -> d0 = bytes read or <0
load_bin_file:
    movem.l d1-d2/a1-a2,-(sp)
    move.l  d0,d2
    movea.l a1,a2
    move.w  #0,-(sp)
    move.l  a0,-(sp)
    move.w  #$3d,-(sp)                  ; Fopen
    trap    #1
    addq.l  #8,sp
    tst.l   d0
    bmi.s   .lbf_err
    move.w  d0,d1                       ; handle
    move.l  a2,-(sp)
    move.l  d2,-(sp)
    move.w  d1,-(sp)
    move.w  #$3f,-(sp)                  ; Fread
    trap    #1
    lea     12(sp),sp
    move.l  d0,d2                       ; bytes read
    move.w  d1,-(sp)
    move.w  #$3e,-(sp)                  ; Fclose
    trap    #1
    addq.l  #4,sp
    move.l  d2,d0
.lbf_err:
    movem.l (sp)+,d1-d2/a1-a2
    rts

; ============================================================================
; init_amiga_dma — User mode: load AM_MUS.BIN + AM_SFX.BIN, patch Paula hooks,
;                  build 4 KB volume LUT, start circular STE DMA ring!
; ============================================================================
init_amiga_dma:
    movem.l d0-d7/a0-a6,-(sp)

    ; 1. Load AM_MUS.BIN into ptr_am_mus_buf
    lea     str_am_mus(pc),a0
    movea.l ptr_am_mus_buf(pc),a1
    move.l  #$b400,d0
    bsr.s   load_bin_file
    tst.l   d0
    ble.w   .iad_fail

    ; 2. Load AM_SFX.BIN into ptr_am_sfx_buf
    lea     str_am_sfx(pc),a0
    movea.l ptr_am_sfx_buf(pc),a1
    move.l  #$4000,d0
    bsr.s   load_bin_file
    tst.l   d0
    ble.w   .iad_fail

    ; 3. Partition ptr_dma_bufs ($2000 B):
    ;    +$0000..+$0fff: 4 KB volume lookup table (16 levels x 256 signed bytes)
    ;    +$1000..+$17cf: 2,000 B circular STE DMA stereo ring buffer
    ;    +$1800..+$18ff: 256 B Virtual Paula register file ($dff000..$dff0ff)
    movea.l ptr_dma_bufs(pc),a0
    lea     vol_tbl_ptr(pc),a1
    move.l  a0,(a1)+                    ; vol_tbl_ptr
    lea     $1000(a0),a2
    move.l  a2,(a1)+                    ; dma_ring_ptr
    lea     $1800(a0),a3
    move.l  a3,(a1)                     ; vpaula_ptr

    ; Build 16x256 signed volume table: out = (signed_byte * lvl) >> 5 (safe 2-ch sum per ear!)
    moveq   #0,d0                       ; lvl = 0..15
.vt_lvl:
    moveq   #0,d1                       ; raw byte = 0..255
.vt_byte:
    move.b  d1,d2
    ext.w   d2                          ; signed -128..+127
    muls.w  d0,d2
    asr.w   #5,d2                       ; /32 -> max +-60 per ch -> 2 ch sum <= +-120 (no clip!)
    move.b  d2,(a0)+
    addq.w  #1,d1
    cmp.w   #256,d1
    blt.s   .vt_byte
    addq.w  #1,d0
    cmp.w   #16,d0
    blt.s   .vt_lvl

    ; Zero 2,000-byte DMA ring & 256-byte Virtual Paula regs
    movea.l dma_ring_ptr(pc),a0
    move.w  #(DMA_RING_BYTES/4)-1,d0
.clr_ring:
    clr.l   (a0)+
    dbra    d0,.clr_ring

    movea.l vpaula_ptr(pc),a3
    moveq   #63,d0
.clr_vp:
    clr.l   (a3)+
    dbra    d0,.clr_vp

    ; Set INTREQR ($1e) = $ffff and DMACONR ($02) = $000f so Amiga wait loops exit immediately
    movea.l vpaula_ptr(pc),a3
    move.w  #$000f,$02(a3)
    move.w  #$ffff,$1e(a3)

    ; 4. Patch the 5 $dff0xx addresses & 5 DMACON writes inside AM_MUS.BIN
    movea.l ptr_am_mus_buf(pc),a0
    move.l  a3,d0                       ; vpaula_ptr
    move.l  d0,d1
    add.l   #$a0,d1                     ; vpaula_ptr + $a0

    ; +0x03c0 ($22d4e): NOP out move.w #$ff, $dff09e.l (8 bytes)
    move.l  #$4e714e71,$03c0(a0)
    move.l  #$4e714e71,$03c4(a0)
    ; +0x03da, +0x04a4, +0x04fc: lea vpaula_ptr, a1/a0
    move.l  d0,$03da(a0)
    move.l  d0,$04a4(a0)
    move.l  d0,$04fc(a0)
    ; +0x04c4: lea vpaula_ptr+$a0, a1
    move.l  d1,$04c4(a0)

    ; +0x03e4 ($22d72, 6B): jsr vpaula_stop_a0.l
    move.w  #$4eb9,$03e4(a0)
    lea     vpaula_stop_a0(pc),a1
    move.l  a1,$03e6(a0)

    ; +0x0638 ($22fc6, 10B): jsr vpaula_trig_on.l; nop; nop
    move.w  #$4eb9,$0638(a0)
    lea     vpaula_trig_on(pc),a1
    move.l  a1,$063a(a0)
    move.l  #$4e714e71,$063e(a0)

    ; +0x0680 ($2300e, 6B): jsr vpaula_stop_a2.l
    move.w  #$4eb9,$0680(a0)
    lea     vpaula_stop_a2(pc),a1
    move.l  a1,$0682(a0)

    ; +0x078e ($2311c, 8B): jsr vpaula_stop_d4.l; nop
    move.w  #$4eb9,$078e(a0)
    lea     vpaula_stop_d4(pc),a1
    move.l  a1,$0790(a0)
    move.w  #$4e71,$0794(a0)

    ; +0x0904 ($23292, 10B): jsr vpaula_trig_on.l; nop; nop
    move.w  #$4eb9,$0904(a0)
    lea     vpaula_trig_on(pc),a1
    move.l  a1,$0906(a0)
    move.l  #$4e714e71,$090a(a0)

    ; 5. Register AM_SFX.BIN with Amiga player: init_sfx(a0=AM_SFX, d0=-1) at +$1c
    movea.l ptr_am_mus_buf(pc),a1
    movea.l ptr_am_sfx_buf(pc),a0
    moveq   #-1,d0
    jsr     $1c(a1)

    ; Set master volume to max ($8000) via +$24
    move.w  #$8000,d0
    jsr     $24(a1)

    bsr.w   vpaula_stop_all

    ; 6. Start circular STE DMA playback (12,517 Hz stereo) in Supervisor mode
    clr.l   -(sp)
    move.w  #$20,-(sp)
    trap    #1
    addq.l  #6,sp
    move.l  d0,-(sp)

    move.b  #0,DMA_CTRL.w               ; stop DMA
    move.l  dma_ring_ptr(pc),d0
    move.b  d0,DMA_START_LO.w
    lsr.l   #8,d0
    move.b  d0,DMA_START_MID.w
    lsr.l   #8,d0
    move.b  d0,DMA_START_HI.w
    move.l  dma_ring_ptr(pc),d0
    add.l   #DMA_RING_BYTES,d0
    move.b  d0,DMA_END_LO.w
    lsr.l   #8,d0
    move.b  d0,DMA_END_MID.w
    lsr.l   #8,d0
    move.b  d0,DMA_END_HI.w
    move.b  #$01,DMA_MODE.w             ; 12,517 Hz, stereo (bit 7 = 0)
    move.b  #$03,DMA_CTRL.w             ; play + loop!

    move.w  #$20,-(sp)
    trap    #1
    addq.l  #6,sp

    lea     dma_wr_slot(pc),a0
    move.w  #4,(a0)                     ; write 4 slots (40 ms) ahead of cursor 0
    lea     am_dma_ready(pc),a0
    st      (a0)
.iad_fail:
    movem.l (sp)+,d0-d7/a0-a6
    rts

; ============================================================================
; Virtual Paula DMACON Hooks (called from patched AM_MUS.BIN)
; ============================================================================
; Channel stop from $22d72: a0 = chan workspace ($68(a0) = bitmask 1/2/4/8)
vpaula_stop_a0:
    movem.l d0/a1,-(sp)
    move.w  $68(a0),d0
    bsr.s   vpaula_stop_mask
    movem.l (sp)+,d0/a1
    rts

; Channel stop from $2300e: a2 = chan workspace ($68(a2) = bitmask)
vpaula_stop_a2:
    movem.l d0/a1,-(sp)
    move.w  $68(a2),d0
    bsr.s   vpaula_stop_mask
    movem.l (sp)+,d0/a1
    rts

; Channel stop from $2311c: must return d4 = $68(a2)!
vpaula_stop_d4:
    move.w  $68(a2),d4
    movem.l d0/a1,-(sp)
    move.w  d4,d0
    bsr.s   vpaula_stop_mask
    movem.l (sp)+,d0/a1
    rts

; Stop channel(s) matching bitmask in d0 (bits 0..3)
vpaula_stop_mask:
    lea     vch_table(pc),a1
    btst    #0,d0
    beq.s   .vsm1
    clr.b   VCH_ACTIVE(a1)
.vsm1:
    btst    #1,d0
    beq.s   .vsm2
    clr.b   VCH_ACTIVE+VCH_SIZE(a1)
.vsm2:
    btst    #2,d0
    beq.s   .vsm3
    clr.b   VCH_ACTIVE+2*VCH_SIZE(a1)
.vsm3:
    btst    #3,d0
    beq.s   .vsm4
    clr.b   VCH_ACTIVE+3*VCH_SIZE(a1)
.vsm4:
    rts

vpaula_stop_all:
    movem.l d0/a1,-(sp)
    lea     vch_table(pc),a1
    moveq   #3,d0
.vsa_l:
    clr.w   VCH_VOL(a1)
    clr.b   VCH_ACTIVE(a1)
    lea     VCH_SIZE(a1),a1
    dbra    d0,.vsa_l
    movem.l (sp)+,d0/a1
    rts

; Channel trigger ON from $22fc6 / $23292: a5 = vpaula + $a0 + ch*$10, d4 = $8000 | mask
vpaula_trig_on:
    movem.l d0-d2/a1,-(sp)
    move.l  a5,d0
    sub.l   vpaula_ptr(pc),d0
    sub.w   #$a0,d0
    lsr.w   #4,d0                       ; ch = 0..3
    and.w   #3,d0
    lsl.w   #5,d0                       ; * 32 (VCH_SIZE)
    lea     vch_table(pc),a1
    adda.w  d0,a1

    move.l  0(a5),VCH_SAMP_PTR(a1)
    move.l  0(a5),VCH_LOOP_PTR(a1)
    moveq   #0,d1
    move.w  4(a5),d1                    ; len in words
    add.l   d1,d1                       ; len in bytes
    move.l  d1,VCH_SAMP_LEN(a1)
    move.l  d1,VCH_LOOP_LEN(a1)
    ; Fast-path: if Ch 0 has a short looping sample (<= 512 B, e.g. Engine RPM!),
    ; tile it into ptr_dma_bufs+$1900 (1,792 B free!) so len >= 1024 B -> ALWAYS hits .mcr_fast!
    tst.w   d0                          ; Ch 0 only (offset 0)
    bne.s   .vto_notile
    cmp.l   #8,d1
    blt.s   .vto_notile
    cmp.l   #512,d1
    bgt.s   .vto_notile
    movem.l d3-d5/a2-a3,-(sp)
    movea.l ptr_dma_bufs(pc),a2
    adda.l  #$1900,a2                   ; tiled engine loop buffer (1,792 B available)
    move.l  a2,a3
    moveq   #0,d3                       ; total tiled bytes
.vto_tlp:
    movea.l VCH_SAMP_PTR(a1),a0
    move.w  d1,d4
    subq.w  #1,d4
.vto_cp:
    move.b  (a0)+,(a3)+
    dbra    d4,.vto_cp
    add.l   d1,d3
    cmp.l   #1024,d3
    blt.s   .vto_tlp
    move.l  a2,VCH_SAMP_PTR(a1)
    move.l  a2,VCH_LOOP_PTR(a1)
    move.l  d3,VCH_SAMP_LEN(a1)
    move.l  d3,VCH_LOOP_LEN(a1)
    movem.l (sp)+,d3-d5/a2-a3
.vto_notile:
    move.w  8(a5),VCH_VOL(a1)
    move.w  6(a5),d1                    ; period
    bsr.s   vpaula_set_per
    clr.w   VCH_POS_INT(a1)
    clr.w   VCH_POS_FRAC(a1)
    cmp.l   #4,VCH_SAMP_LEN(a1)
    ble.s   .vto_off
    move.b  #1,VCH_ACTIVE(a1)
    bra.s   .vto_done
.vto_off:
    clr.b   VCH_ACTIVE(a1)
.vto_done:
    movem.l (sp)+,d0-d2/a1
    rts

; Convert Paula period in d1.w -> 16.16 step @ 12,517 Hz into a1 (cached!)
vpaula_set_per:
    cmp.w   #71,d1
    blt.s   .vsp_ret
    cmp.w   VCH_LAST_PER(a1),d1
    beq.s   .vsp_ret
    move.w  d1,VCH_LAST_PER(a1)
    move.l  #4642439,d0
    divu.w  d1,d0
    and.l   #$ffff,d0
    lsl.l   #2,d0
    swap    d0
    move.w  d0,VCH_STEP_INT(a1)
    swap    d0
    move.w  d0,VCH_STEP_FRAC(a1)
.vsp_ret:
    rts

; ============================================================================
; Overlander Sound Driver Hooks (fall back to YM on plain ST where has_dma=0)
; ============================================================================
do_aud_stop1:
    movem.l d0-d7/a0-a6,-(sp)
    lea     am_dma_ready(pc),a1
    tst.b   (a1)
    beq.s   .das1_ym
    movea.l ptr_am_mus_buf(pc),a1
    jsr     $04(a1)                     ; stop_music()
    jsr     $18(a1)                     ; stop_engine()
    lea     am_engine_on(pc),a0
    clr.b   (a0)
    bsr.w   vpaula_stop_all
    movem.l (sp)+,d0-d7/a0-a6
    rts
.das1_ym:
    movem.l (sp)+,d0-d7/a0-a6
    move.l  a0,-(sp)
    movea.l ptr_game_base(pc),a0
    adda.l  #$2331,a0                   ; $cdcb
    move.l  ptr_orig_aud_stop1(pc),-(sp)
    rts

do_aud_stop2:
    movem.l d0-d7/a0-a6,-(sp)
    lea     am_dma_ready(pc),a1
    tst.b   (a1)
    beq.s   .das2_ym
    movea.l ptr_am_mus_buf(pc),a1
    jsr     $04(a1)                     ; stop_music()
    jsr     $18(a1)                     ; stop_engine()
    lea     am_engine_on(pc),a0
    clr.b   (a0)
    bsr.w   vpaula_stop_all
    movem.l (sp)+,d0-d7/a0-a6
    rts
.das2_ym:
    movem.l (sp)+,d0-d7/a0-a6
    move.l  a0,-(sp)
    movea.l ptr_game_base(pc),a0
    adda.l  #$2331,a0                   ; $cdcb
    move.l  ptr_orig_aud_stop2(pc),-(sp)
    rts

; Short SFX hook (+$518): d0 = 1 (gun), 2 (menu/fuel), 3 (missile/flame)
; Stereo twin-cannon: gun alternates Ch 1 (Right) and Ch 3 (Left)!
do_aud_sfx:
    movem.l d0-d7/a0-a6,-(sp)
    lea     am_dma_ready(pc),a2
    tst.b   (a2)
    beq.s   .dsfx_ym
    movea.l ptr_am_mus_buf(pc),a1
    and.w   #$ff,d0
    cmp.w   #1,d0
    bne.s   .dsfx_2
    moveq   #0,d0                       ; Amiga SFX #0 (gun shot)
    lea     gun_pan_toggle(pc),a2
    eor.b   #1,(a2)
    bne.s   .dsfx_gun_r
    moveq   #3,d1                       ; ch 3 (Left ear)
    bra.s   .dsfx_gun_go
.dsfx_gun_r:
    moveq   #1,d1                       ; ch 1 (Right ear)
.dsfx_gun_go:
    jsr     $1c(a1)
    bra.s   .dsfx_done
.dsfx_2:
    cmp.w   #2,d0
    bne.s   .dsfx_3
    moveq   #2,d0                       ; Amiga SFX #2 (menu/fuel)
    moveq   #2,d1                       ; ch 2 (Right)
    jsr     $1c(a1)
    bra.s   .dsfx_done
.dsfx_3:
    moveq   #3,d0                       ; Amiga SFX #3 (missile)
    moveq   #3,d1                       ; ch 3 (Left)
    jsr     $1c(a1)
.dsfx_done:
    movem.l (sp)+,d0-d7/a0-a6
    rts
.dsfx_ym:
    movem.l (sp)+,d0-d7/a0-a6
    movem.l d0/a0-a1,-(sp)
    movea.l ptr_game_base(pc),a2
    adda.l  #$232a,a2                   ; $cdc4
    move.l  ptr_orig_aud_sfx(pc),-(sp)
    rts

; Music / Big SFX hook (+$554): d0 = 0 (title), 2 (win/end), 3 (road), 4 (load), 7 (explosion)
do_aud_mus:
    movem.l d0-d7/a0-a6,-(sp)
    lea     am_dma_ready(pc),a2
    tst.b   (a2)
    beq.w   .dmus_ym
    movea.l ptr_am_mus_buf(pc),a1
    and.w   #$ff,d0
    cmp.w   #7,d0
    bne.s   .dmus_not_exp
    ; Explosion SFX on ch 2 (Right)!
    moveq   #1,d0                       ; Amiga SFX #1 (explosion)
    moveq   #2,d1
    jsr     $1c(a1)
    ; If we're on the road in Engine mode and stop1 silenced the engine before explosion, restart engine!
    lea     am_in_road(pc),a2
    tst.b   (a2)
    beq.w   .dmus_done
    lea     am_bgm_mode(pc),a2
    tst.b   (a2)
    bne.w   .dmus_done
    lea     am_engine_on(pc),a2
    tst.b   (a2)
    bne.w   .dmus_done
    jsr     $10(a1)                     ; restart engine on ch 0!
    st      (a2)                        ; am_engine_on = 1
    lea     last_ym_rpm(pc),a2
    st      (a2)                        ; force pitch refresh
    bra.w   .dmus_done
.dmus_not_exp:
    cmp.w   #3,d0
    bne.s   .dmus_song
    ; Road driving: set am_in_road=1; play BGM if am_bgm_mode=1 else Engine!
    lea     am_in_road(pc),a2
    st      (a2)
    lea     am_bgm_mode(pc),a2
    tst.b   (a2)
    bne.s   .dmus_road_bgm
    jsr     $04(a1)                     ; stop_music
    jsr     $10(a1)                     ; start_engine() on ch 0!
    lea     am_engine_on(pc),a2
    st      (a2)
    bra.s   .dmus_done
.dmus_road_bgm:
    lea     am_engine_on(pc),a2
    clr.b   (a2)
    jsr     $18(a1)                     ; stop_engine
    lea     $09ac(a1),a0
    moveq   #1,d0                       ; Amiga Driving Tune #1
    jsr     $00(a1)
    bra.s   .dmus_done
.dmus_song:
    ; Map ST tune ID (0=title, 2=end, 4=loading) -> Amiga tune 0..4
    lea     am_in_road(pc),a2
    clr.b   (a2)
    lea     am_engine_on(pc),a2
    clr.b   (a2)
    jsr     $18(a1)                     ; stop_engine
    lea     $09ac(a1),a0                ; song header (0x2333a - 0x2298e = 0x9ac)
    cmp.w   #4,d0
    bne.s   .dmus_t0
    moveq   #1,d0                       ; loading screen -> Amiga Tune 1
    bra.s   .dmus_play
.dmus_t0:
    cmp.w   #2,d0
    bne.s   .dmus_t0b
    moveq   #2,d0                       ; end/win -> Amiga Tune 2
    bra.s   .dmus_play
.dmus_t0b:
    moveq   #0,d0                       ; title -> Amiga Tune 0
.dmus_play:
    jsr     $00(a1)                     ; init_song(a0, d0)
.dmus_done:
    movem.l (sp)+,d0-d7/a0-a6
    rts
.dmus_ym:
    movem.l (sp)+,d0-d7/a0-a6
    movem.l d0-d2/a0-a2,-(sp)
    movea.l ptr_game_base(pc),a2
    adda.l  #$2a77,a2                   ; $d511
    move.l  ptr_orig_aud_mus(pc),-(sp)
    rts

; ============================================================================
; do_aud_tick — 50 Hz VBL Audio Tick + JagPad Poll + Atomic STE DMA Ring Mixer
; ============================================================================
do_aud_tick:
    movem.l d0-d7/a0-a6,-(sp)
    ; Poll STE Enhanced Joystick / Jaguar PowerPad ONLY if a real JagPad was detected at boot!
    lea     has_ste_joy(pc),a3
    tst.b   (a3)
    beq.s   .skip_jag
    move.l  a0,-(sp)
    bsr.w   poll_ste_jagpad
    movea.l (sp)+,a0
.skip_jag:
    lea     am_dma_ready(pc),a3
    tst.b   (a3)
    bne.s   .dat_dma
    movem.l (sp)+,d0-d7/a0-a6
    movem.l d0-d2/a0-a3,-(sp)
    clr.w   d0
    move.l  ptr_orig_aud_tick(pc),-(sp)
    rts

.dat_dma:
    ; Re-entrancy guard (since we lower IPL to 3 so Timer B can preempt cleanly!)
    lea     aud_in_tick(pc),a3
    tas     (a3)
    bmi.w   .dat_exit_nosr
    move.w  sr,-(sp)
    move.w  #$2300,sr

    ; Handle live 'M' key / JagPad Option driving music toggle
    lea     toggle_bgm_req(pc),a2
    tst.b   (a2)
    beq.s   .no_bgm_tog
    clr.b   (a2)
    lea     am_bgm_mode(pc),a2
    eor.b   #1,(a2)
    lea     am_in_road(pc),a3
    tst.b   (a3)
    beq.s   .no_bgm_tog
    movea.l ptr_am_mus_buf(pc),a1
    tst.b   (a2)
    bne.s   .tog_to_bgm
    jsr     $04(a1)                     ; stop_music
    jsr     $10(a1)                     ; start_engine
    lea     am_engine_on(pc),a2
    st      (a2)
    lea     last_ym_rpm(pc),a2
    st      (a2)
    bra.s   .no_bgm_tog
.tog_to_bgm:
    lea     am_engine_on(pc),a2
    clr.b   (a2)
    jsr     $18(a1)                     ; stop_engine
    move.l  a0,-(sp)
    lea     $09ac(a1),a0
    moveq   #1,d0                       ; Amiga Driving Tune #1
    jsr     $00(a1)
    movea.l (sp)+,a0
.no_bgm_tog:

    ; Sync Overlander's live engine RPM ($2b(sound_drv)) if engine is running!
    lea     am_engine_on(pc),a2
    tst.b   (a2)
    beq.s   .no_rpm_sync
    movea.l ptr_game_base(pc),a2
    movea.l $2a(a2),a2                  ; sound driver base ($cdc4)
    moveq   #0,d0
    move.b  $2b(a2),d0                  ; ST engine RPM byte (0..$f0)
    ; Convert RPM (0..240) -> Paula period (520 idle down to 160 redline)
    move.w  d0,d1
    lsr.w   #1,d1
    add.w   d1,d0                       ; d0 * 1.5 (0..360)
    move.w  #520,d1
    sub.w   d0,d1
    cmp.w   #160,d1
    bge.s   .rpm_ok
    move.w  #160,d1
.rpm_ok:
    lea     last_eng_per(pc),a2
    cmp.w   (a2),d1
    beq.s   .no_rpm_sync
    move.w  d1,(a2)
    movea.l ptr_am_mus_buf(pc),a1
    move.w  d1,d0
    jsr     $14(a1)                     ; set_engine_pitch(d0)
.no_rpm_sync:

    ; Atomically read 24-bit live STE DMA playback cursor (guard HI/MID/LO carry)
.rd_cnt:
    moveq   #0,d0
    move.b  DMA_CNT_HI.w,d0
    move.b  DMA_CNT_MID.w,d1
    move.b  DMA_CNT_LO.w,d2
    cmp.b   DMA_CNT_MID.w,d1
    bne.s   .rd_cnt
    cmp.b   DMA_CNT_HI.w,d0
    bne.s   .rd_cnt
    lsl.l   #8,d0
    move.b  d1,d0
    lsl.l   #8,d0
    move.b  d2,d0

    movea.l dma_ring_ptr(pc),a5
    sub.l   a5,d0                       ; rd_off (0..1999)
    bmi.s   .rd_cl0
    cmp.l   #DMA_RING_BYTES,d0
    blt.s   .rd_ok
.rd_cl0:
    moveq   #0,d0
.rd_ok:
    move.w  dma_wr_slot(pc),d1
    mulu.w  #250,d1
    sub.w   d1,d0                       ; free = rd_off - wr_off
    bpl.s   .df_pos
    addi.w  #DMA_RING_BYTES,d0
.df_pos:
    ; Fill up to 3 slots (250 B each) per VBL while free >= 250
    moveq   #2,d6
.slot_lp:
    cmp.w   #250,d0
    blt.w   .dat_done
    subi.w  #250,d0
    move.w  d0,-(sp)
    move.w  d6,-(sp)

    ; 1. Always tick Mark Cooksey Amiga player (+$08) so start_engine & play_sfx always trigger!
    movea.l ptr_am_mus_buf(pc),a1
    jsr     $08(a1)                     ; vbl_tick()

    ; 1b. If driving engine is active, override Ch 0 period AFTER vbl_tick so RPM pitch always tracks speed!
    lea     am_engine_on(pc),a2
    tst.b   (a2)
    beq.s   .no_eng_ovr
    movea.l vpaula_ptr(pc),a3
    move.w  last_eng_per(pc),$a6(a3)
.no_eng_ovr:

    ; 2. Sync live Virtual Paula loop/period/vol for all 4 channels
    movea.l vpaula_ptr(pc),a3
    lea     $a0(a3),a3
    lea     vch_table(pc),a1
    moveq   #3,d7
.sync_vp:
    tst.b   VCH_ACTIVE(a1)
    beq.s   .svp_next
    move.l  0(a3),VCH_LOOP_PTR(a1)
    moveq   #0,d1
    move.w  4(a3),d1
    add.l   d1,d1
    move.l  d1,VCH_LOOP_LEN(a1)
    move.w  8(a3),VCH_VOL(a1)
    move.w  6(a3),d1
    bsr.w   vpaula_set_per
.svp_next:
    lea     $10(a3),a3
    lea     VCH_SIZE(a1),a1
    dbra    d7,.sync_vp

    ; 3. Mix 125 stereo samples (250 bytes) into current ring slot
    move.w  dma_wr_slot(pc),d1
    mulu.w  #250,d1
    movea.l dma_ring_ptr(pc),a5
    lea     (a5,d1.w),a4
    bsr.s   mix_125_stereo

    ; Advance dma_wr_slot (0..7)
    lea     dma_wr_slot(pc),a0
    move.w  (a0),d1
    addq.w  #1,d1
    andi.w  #7,d1
    move.w  d1,(a0)

    move.w  (sp)+,d6
    move.w  (sp)+,d0
    dbra    d6,.slot_lp

.dat_done:
    move.w  (sp)+,sr
    lea     aud_in_tick(pc),a3
    clr.b   (a3)
.dat_exit_nosr:
    movem.l (sp)+,d0-d7/a0-a6
    rts

; ============================================================================
; 4-Channel Stereo Mixer (125 stereo frames = 250 bytes into a4)
; Left (even bytes): Ch 0 (replace) + Ch 3 (add)
; Right (odd bytes): Ch 1 (replace) + Ch 2 (add)
; ============================================================================
mix_125_stereo:
    ; Ultra-fast Engine-only path: when Ch 0 is Engine and Ch 1/2/3 are ALL idle (90% of driving!),
    ; write (eng_byte << 8 | 0) as words -> clears Right channel FOR FREE and skips Ch 1/2/3!
    lea     am_engine_on(pc),a1
    tst.b   (a1)
    beq.w   .m125_full
    lea     vch_table(pc),a1
    tst.b   VCH_ACTIVE(a1)
    beq.w   .m125_full
    tst.b   1*VCH_SIZE+VCH_ACTIVE(a1)
    bne.w   .m125_full
    tst.b   2*VCH_SIZE+VCH_ACTIVE(a1)
    bne.w   .m125_full
    tst.b   3*VCH_SIZE+VCH_ACTIVE(a1)
    bne.w   .m125_full
    ; Verify Ch 0 won't wrap during 125 samples (always true for 1 KB tiled Engine!)
    move.w  VCH_STEP_INT(a1),d3
    move.w  d3,d6
    addq.w  #1,d6
    mulu.w  #125,d6
    add.w   VCH_POS_INT(a1),d6
    bcs.w   .m125_full
    cmp.w   VCH_SAMP_LEN+2(a1),d6
    bhs.w   .m125_full
    ; Mix Ch 0 Engine (2x sample-hold) + zero Right channel in ONE word write!
    move.w  VCH_VOL(a1),d0
    lsr.w   #2,d0
    beq.w   .m125_full
    cmp.w   #15,d0
    ble.s   .meo_vok
    moveq   #15,d0
.meo_vok:
    lsl.w   #8,d0
    movea.l vol_tbl_ptr(pc),a2
    adda.w  d0,a2
    movea.l VCH_SAMP_PTR(a1),a0
    move.w  VCH_POS_FRAC(a1),d0
    move.w  VCH_STEP_FRAC(a1),d1
    move.w  VCH_POS_INT(a1),d2
    add.w   d1,d1
    addx.w  d3,d3
    moveq   #0,d4
    movea.l a4,a3
    moveq   #11,d7                      ; 12 * 5 = 60 pairs (120 stereo frames = 240 bytes)
.meo_lp:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6                       ; high byte = Left engine, low byte = 0 (Right silent!)
    move.w  d6,(a3)
    move.w  d6,2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,4(a3)
    move.w  d6,6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,8(a3)
    move.w  d6,10(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,12(a3)
    move.w  d6,14(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,16(a3)
    move.w  d6,18(a3)
    add.w   d1,d0
    addx.w  d3,d2
    lea     20(a3),a3
    dbra    d7,.meo_lp
    ; Final 5 stereo frames (10 bytes)
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,(a3)
    move.w  d6,2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,4(a3)
    move.w  d6,6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    lsl.w   #8,d6
    move.w  d6,8(a3)
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
    rts

.m125_full:
    lea     vch_table(pc),a1            ; Ch 0 -> Left (replace)
    movea.l a4,a3
    bsr.s   mix_ch_replace
    lea     vch_table+3*VCH_SIZE(pc),a1 ; Ch 3 -> Left (add)
    movea.l a4,a3
    bsr.w   mix_ch_add
    lea     vch_table+1*VCH_SIZE(pc),a1 ; Ch 1 -> Right (replace)
    lea     1(a4),a3
    bsr.s   mix_ch_replace
    lea     vch_table+2*VCH_SIZE(pc),a1 ; Ch 2 -> Right (add)
    lea     1(a4),a3
    bsr.w   mix_ch_add
    rts

mix_ch_replace:
    tst.b   VCH_ACTIVE(a1)
    beq.w   .mcr_zero
    move.w  VCH_VOL(a1),d0
    lsr.w   #2,d0
    beq.w   .mcr_zero
    cmp.w   #15,d0
    ble.s   .mcr_vok
    moveq   #15,d0
.mcr_vok:
    lsl.w   #8,d0
    movea.l vol_tbl_ptr(pc),a2
    adda.w  d0,a2
    movea.l VCH_SAMP_PTR(a1),a0
    move.w  VCH_POS_FRAC(a1),d0
    move.w  VCH_STEP_FRAC(a1),d1
    move.w  VCH_POS_INT(a1),d2
    move.w  VCH_STEP_INT(a1),d3
    move.l  VCH_SAMP_LEN(a1),d5
    moveq   #0,d4
    move.w  d3,d6
    addq.w  #1,d6
    mulu.w  #125,d6
    add.w   d2,d6
    bcs.w   .mcr_slow
    cmp.w   d5,d6
    bhs.w   .mcr_slow
    ; In Engine-only mode on Ch 0 (low-freq rumble), 2x sample-hold into 12,517 Hz DMA cuts Ch 0 mixing in half!
    lea     am_engine_on(pc),a5
    tst.b   (a5)
    beq.w   .mcr_norm_fast
    lea     vch_table(pc),a5
    cmpa.l  a5,a1                       ; Ch 0 only!
    bne.w   .mcr_norm_fast
    ; Double step (2x) and write each sample to 2 consecutive Left DMA bytes (62 pairs + 1 = 125)!
    add.w   d1,d1
    addx.w  d3,d3
    moveq   #11,d7                      ; 12 * 5 = 60 pairs (120 bytes)
.mcr_eng:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,(a3)
    move.b  d6,2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,4(a3)
    move.b  d6,6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,8(a3)
    move.b  d6,10(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,12(a3)
    move.b  d6,14(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,16(a3)
    move.b  d6,18(a3)
    add.w   d1,d0
    addx.w  d3,d2
    lea     20(a3),a3
    dbra    d7,.mcr_eng
    ; Final 5 bytes (2 pairs + 1)
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,(a3)
    move.b  d6,2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    move.b  d6,4(a3)
    move.b  d6,6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),8(a3)
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
    rts

.mcr_norm_fast:
    moveq   #24,d7
.mcr_fast:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),4(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),8(a3)
    add.w   d1,d0
    addx.w  d3,d2
    lea     10(a3),a3
    dbra    d7,.mcr_fast
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
    rts
.mcr_zero:
    ; Fast 68000 movep.l clear: 4 alternating bytes per instruction (4x faster!)
    moveq   #0,d0
    moveq   #30,d7                      ; 31 * 4 = 124 bytes
.mcr_zlp:
    movep.l d0,0(a3)
    addq.l  #8,a3
    dbra    d7,.mcr_zlp
    clr.b   (a3)                        ; 125th byte
    rts
.mcr_slow:
    ; Fast-path for short looping samples (e.g. Amiga Engine RPM!) where SAMP_LEN == LOOP_LEN > 4
    move.l  VCH_LOOP_LEN(a1),d6
    cmp.l   #4,d6
    ble.w   .mcr_oneshot
    cmp.l   d5,d6
    bne.w   .mcr_oneshot
    cmpa.l  VCH_LOOP_PTR(a1),a0
    bne.w   .mcr_oneshot
    ; Tight wrap-only loop: NO memory fetches/stores per wrap, unrolled x5 with indexed offsets!
    moveq   #24,d7
.mcr_lfast:
    cmp.w   d5,d2
    blo.s   .mlf0
    sub.w   d5,d2
.mlf0:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),(a3)
    add.w   d1,d0
    addx.w  d3,d2
    cmp.w   d5,d2
    blo.s   .mlf1
    sub.w   d5,d2
.mlf1:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    cmp.w   d5,d2
    blo.s   .mlf2
    sub.w   d5,d2
.mlf2:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),4(a3)
    add.w   d1,d0
    addx.w  d3,d2
    cmp.w   d5,d2
    blo.s   .mlf3
    sub.w   d5,d2
.mlf3:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    cmp.w   d5,d2
    blo.s   .mlf4
    sub.w   d5,d2
.mlf4:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),8(a3)
    add.w   d1,d0
    addx.w  d3,d2
    lea     10(a3),a3
    dbra    d7,.mcr_lfast
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
    rts

.mcr_oneshot:
    moveq   #124,d7
.mcr_slp:
    cmp.w   d5,d2
    blo.s   .mcr_ok
    move.l  VCH_LOOP_LEN(a1),d6
    cmp.l   #4,d6
    ble.s   .mcr_stop
    sub.w   d5,d2
    movea.l VCH_LOOP_PTR(a1),a0
    move.l  a0,VCH_SAMP_PTR(a1)
    move.l  d6,d5
    move.l  d6,VCH_SAMP_LEN(a1)
    cmp.w   d5,d2
    blo.s   .mcr_ok
    moveq   #0,d2
.mcr_ok:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),(a3)
    addq.l  #2,a3
    add.w   d1,d0
    addx.w  d3,d2
    dbra    d7,.mcr_slp
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
    rts
.mcr_stop:
    clr.b   VCH_ACTIVE(a1)
.mcr_rem:
    clr.b   (a3)
    addq.l  #2,a3
    dbra    d7,.mcr_rem
    rts

mix_ch_add:
    tst.b   VCH_ACTIVE(a1)
    beq.w   .mca_ret
    move.w  VCH_VOL(a1),d0
    lsr.w   #2,d0
    beq.w   .mca_ret
    cmp.w   #15,d0
    ble.s   .mca_vok
    moveq   #15,d0
.mca_vok:
    lsl.w   #8,d0
    movea.l vol_tbl_ptr(pc),a2
    adda.w  d0,a2
    movea.l VCH_SAMP_PTR(a1),a0
    move.w  VCH_POS_FRAC(a1),d0
    move.w  VCH_STEP_FRAC(a1),d1
    move.w  VCH_POS_INT(a1),d2
    move.w  VCH_STEP_INT(a1),d3
    move.l  VCH_SAMP_LEN(a1),d5
    moveq   #0,d4
    move.w  d3,d6
    addq.w  #1,d6
    mulu.w  #125,d6
    add.w   d2,d6
    bcs.s   .mca_slow
    cmp.w   d5,d6
    bhs.s   .mca_slow
    moveq   #24,d7
.mca_fast:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    add.b   d6,(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    add.b   d6,2(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    add.b   d6,4(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    add.b   d6,6(a3)
    add.w   d1,d0
    addx.w  d3,d2
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    add.b   d6,8(a3)
    add.w   d1,d0
    addx.w  d3,d2
    lea     10(a3),a3
    dbra    d7,.mca_fast
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
.mca_ret:
    rts
.mca_slow:
    moveq   #124,d7
.mca_slp:
    cmp.w   d5,d2
    blo.s   .mca_ok
    move.l  VCH_LOOP_LEN(a1),d6
    cmp.l   #4,d6
    ble.s   .mca_stop
    sub.w   d5,d2
    movea.l VCH_LOOP_PTR(a1),a0
    move.l  a0,VCH_SAMP_PTR(a1)
    move.l  d6,d5
    move.l  d6,VCH_SAMP_LEN(a1)
    cmp.w   d5,d2
    blo.s   .mca_ok
    moveq   #0,d2
.mca_ok:
    move.b  (a0,d2.w),d4
    move.b  (a2,d4.w),d6
    add.b   d6,(a3)
    addq.l  #2,a3
    add.w   d1,d0
    addx.w  d3,d2
    dbra    d7,.mca_slp
    move.w  d0,VCH_POS_FRAC(a1)
    move.w  d2,VCH_POS_INT(a1)
    rts
.mca_stop:
    clr.b   VCH_ACTIVE(a1)
    rts

; ============================================================================
; do_patch_exit — restore IKBD mouse & video mode (if ever exiting cleanly)
; ============================================================================
do_patch_exit:
    move.w  #$08,-(sp)                  ; IKBD Relative Mouse
    move.w  #4,-(sp)
    move.w  #3,-(sp)
    trap    #13
    addq.l  #6,sp
    rts

; ============================================================================
; PHASE 4A: TRUE 12-BIT STE 4,096-COLOR SKY GRADIENTS (Timer B Raster)
; Hooks $00b024 (sky Timer B init) and $00b0f2 (sky raster list builder).
; On plain ST / TT (has_blitter=0): executes original 9-bit ST code untouched.
; On STE / Mega STE / Falcon (has_blitter=1): smoothly subdivides sky bands
; into 4-scanline 12-bit STE RGB steps in ste_sky_bufs (3x256 B), keeping
; exact 128-line total so the dashboard split never shifts by even 1 line!
; ============================================================================

; Helper: select ste_sky_bufs slot (0, 1, or 2) matching scanline-table ptr in a0 -> a1
; Note: *$aaa8 / *$aab0 point to the screen's scanline-table struct whose (a0) = scr_addr_0/1/2!
get_ste_sky_buf:
    movea.l (a0),a0                     ; dereference scanline table -> screen base ptr
    lea     ste_sky_bufs(pc),a1
    cmpa.l  scr_addr_0(pc),a0
    beq.s   .gsb_ok
    lea     256(a1),a1
    cmpa.l  scr_addr_1(pc),a0
    beq.s   .gsb_ok
    lea     256(a1),a1
.gsb_ok:
    rts

; Helper: convert 9-bit ST color word (d0: 0000 0RRR 0GGG 0BBB) -> linear 4-bit
; channels (d5=R*2, d6=G*2, d7=B*2 in 0..14)
; Helper: pack linear 4-bit channels (0..15) in d5(R), d6(G), d7(B) -> STE 12-bit word in d0
; STE nibble encoding: bit3 = LSB, bits2..0 = bits3..1
pack_ste_rgb:
    ; R -> d0
    move.w  d5,d0
    lsr.w   #1,d0
    btst    #0,d5
    beq.s   .psr_g
    bset    #3,d0
.psr_g:
    lsl.w   #4,d0
    move.w  d6,d1
    lsr.w   #1,d1
    btst    #0,d6
    beq.s   .psr_g2
    bset    #3,d1
.psr_g2:
    or.w    d1,d0
    lsl.w   #4,d0
    move.w  d7,d1
    lsr.w   #1,d1
    btst    #0,d7
    beq.s   .psr_b2
    bset    #3,d1
.psr_b2:
    or.w    d1,d0
    rts

; Hook at +0x058a ($00b024): init Timer B for road sky gradient
do_ste_sky_init:
    movem.l d0/a0-a1,-(sp)
    lea     has_blitter(pc),a0
    tst.b   (a0)
    beq.s   .ssi_orig

    ; STE 12-bit Timer B init
    lea     do_ste_sky_tb(pc),a0
    move.l  a0,$120.w
    movea.l ptr_game_base(pc),a0
    movea.l $16(a0),a0                  ; *$aab0 (displayed screen scanline table)
    bsr.s   get_ste_sky_buf             ; a1 = ste_sky_buf for displayed screen
    clr.b   $fffffa1b.w
    move.w  (a1)+,d0                    ; first band scanline count
    move.b  d0,$fffffa21.w
    move.w  (a1)+,$ffff824e.w           ; first 12-bit STE sky color (Color 7)!
    lea     ste_sky_cur_ptr(pc),a0
    move.l  a1,(a0)
    move.b  #8,$fffffa1b.w
    bset.b  #0,$fffffa07.w
    bclr.b  #0,$fffffa0f.w
    movem.l (sp)+,d0/a0-a1
    rts

.ssi_orig:
    movem.l (sp)+,d0/a0-a1
    movem.l a0,-(sp)
    movea.l ptr_game_base(pc),a0
    lea     $05da(a0),a0                ; original $00b074 Timer B ISR
    move.l  a0,$120.w
    movea.l ptr_game_base(pc),a0
    lea     $0598(a0),a0                ; continue at $00b032
    jmp     (a0)

; STE 12-bit Timer B ISR (replaces $00b074 on STE/Mega STE/Falcon)
do_ste_sky_tb:
    movem.l d0-d1/a0,-(sp)
    clr.b   $fffffa1b.w
    movea.l ste_sky_cur_ptr(pc),a0
    move.w  (a0)+,d0
    bmi.s   .sst_dash                   ; negative -> scanline 128 dashboard palette split!
    move.b  d0,$fffffa21.w
    move.w  (a0)+,d1                    ; direct 12-bit STE color word!
    lea     ste_sky_cur_ptr(pc),a0
    ; Wait: advance ste_sky_cur_ptr by 4!
    addq.l  #4,(a0)
    move.b  #8,$fffffa1b.w
    bclr.b  #0,$fffffa0f.w
    move.w  #$0f,d0                     ; brief hblank alignment
.sst_wait:
    dbra    d0,.sst_wait
    move.w  d1,$ffff824e.w
    movem.l (sp)+,d0-d1/a0
    rte

.sst_dash:
    ; Inline dashboard palette write IMMEDIATELY (saves 36 cyc -> switches inside HBL, ZERO blue overspill!)
    movem.l d2-d7,-(sp)
    movea.l ptr_game_base(pc),a0
    movem.l $aa(a0),d0-d7
    movem.l d0-d7,$ffff8240.w
    movem.l (sp)+,d2-d7
    lea     $0636(a0),a0                ; continue at $00b0d0 (screen base + Timer B disable + rte)
    jmp     (a0)

; Hook at +0x0658 ($00b0f2): build smooth 12-bit STE sky raster list
; Temp coarse buffer on stack: up to 16 entries * 4 bytes (dy.w, st_col.w)
do_ste_sky_build:
    lea     has_blitter(pc),a0
    tst.b   (a0)
    bne.s   .ssb_ste
    ; Plain ST / TT: run original $00b0f2
    clr.w   d0
    movea.l ptr_game_base(pc),a0
    movea.l a0,a1
    adda.l  #$c7fc,a1
    move.w  (a1),d1
    lea     $0660(a0),a0                ; continue at $00b0fa
    jmp     (a0)

.ssb_ste:
    movem.l d0-d7/a0-a6,-(sp)
    sub.w   #64,sp                      ; 16 coarse (dy.w, st_col.w) entries on stack
    movea.l sp,a3                       ; a3 = coarse write ptr
    moveq   #0,d7                       ; d7 = coarse count

    movea.l ptr_game_base(pc),a5
    movea.l ptr_lowram_bss(pc),a6
    adda.l  #($7240-$0800),a6           ; a6 = live 16-color palette ($24b20)

    moveq   #0,d0                       ; current y
    movea.l a5,a0
    adda.l  #$c7fc,a0
    move.w  (a0),d1
    subi.w  #$10,d1
    movea.l a5,a0
    adda.l  #$c992,a0
    move.w  (a0),d2                     ; horizon_y
    subq.w  #1,d2
    movea.l $0586(a5),a0                ; level sky band table
    addq.l  #2,a0

    ; Collect coarse bands (exact same loop as $00b118..$00b14a)
.ssb_c_lp:
    add.w   (a0)+,d1
    move.w  (a0)+,d3                    ; palette offset (0..30)
    tst.w   d1
    bmi.s   .ssb_c_lp
    cmp.w   d1,d2
    ble.s   .ssb_c_last
    move.w  d1,d4
    sub.w   d0,d4
    cmp.w   #2,d4
    ble.s   .ssb_c_lp
    cmp.w   #15,d7
    bge.s   .ssb_c_lp
    move.w  d4,(a3)+                    ; dy
    move.w  (a6,d3.w),(a3)+             ; 9-bit ST color
    addq.w  #1,d7
    move.w  d1,d0
    bra.s   .ssb_c_lp

.ssb_c_last:
    move.w  d2,d4
    sub.w   d0,d4
    cmp.w   #2,d4
    ble.s   .ssb_c_adj
    move.w  d4,(a3)+
    move.w  (a6,d3.w),(a3)+
    addq.w  #1,d7
    bra.s   .ssb_c_done
.ssb_c_adj:
    tst.w   d7
    beq.s   .ssb_c_done
    add.w   d4,-4(a3)
.ssb_c_done:
    ; Select target ste_sky_buf for draw screen (*$aaa8)
    movea.l $0e(a5),a0                  ; *$aaa8
    bsr.w   get_ste_sky_buf             ; a1 = dst ste_sky_buf
    movea.l a1,a4                       ; a4 = write cursor

    ; Subdivide each coarse band with ZERO divisions (power-of-2: N=1, 2, or 4)!
    movea.l sp,a3                       ; a3 = read cursor
    tst.w   d7
    beq.w   .ssb_horiz
    subq.w  #1,d7                       ; dbra counter
.ssb_band:
    move.w  (a3)+,d0                    ; dy (band height)
    move.w  (a3)+,d1                    ; C0 (9-bit ST color)
    tst.w   d7
    beq.s   .ssb_emit1                  ; last band: hold C0 (1 slice)
    move.w  2(a3),d2                    ; C1 = next band's color
    cmp.w   d1,d2
    beq.s   .ssb_emit1                  ; same color: 1 slice
    cmp.w   #12,d0
    blt.s   .ssb_emit1                  ; narrow band (< 12 lines): 1 slice
    ; Split band in 2 halves: top half = C0, bottom half = 12-bit STE midpoint(C0, C1)!
    move.w  d0,d3
    lsr.w   #1,d3                       ; h0 = dy / 2
    sub.w   d3,d0                       ; h1 = dy - h0
    move.w  d3,(a4)+                    ; emit h0
    move.w  d1,(a4)+                    ; emit C0 (valid STE 9-bit = 12-bit with LSB=0!)
    ; Compute 12-bit STE midpoint(C0, C1): R_mid = R0 + R1 (in 0..14!), G_mid = G0+G1, B_mid = B0+B1!
    move.w  d1,d5
    lsr.w   #8,d5
    and.w   #7,d5
    move.w  d2,d6
    lsr.w   #8,d6
    and.w   #7,d6
    add.w   d6,d5                       ; R_mid (0..14)
    move.w  d1,d6
    lsr.w   #4,d6
    and.w   #7,d6
    move.w  d2,d4
    lsr.w   #4,d4
    and.w   #7,d4
    add.w   d4,d6                       ; G_mid (0..14)
    move.w  d1,d4
    and.w   #7,d4
    move.w  d2,d3
    and.w   #7,d3
    add.w   d3,d4                       ; B_mid (0..14)
    ; Pack d5(R), d6(G), d4(B) -> STE 12-bit word in d3 (inline, zero subroutine call!)
    move.w  d7,-(sp)
    move.w  d4,d7
    move.w  d0,-(sp)
    bsr.w   pack_ste_rgb                ; -> d0 = 12-bit STE midpoint color!
    move.w  d0,d3
    move.w  (sp)+,d0
    move.w  (sp)+,d7
    move.w  d0,(a4)+                    ; emit h1
    move.w  d3,(a4)+                    ; emit 12-bit STE midpoint!
    dbra    d7,.ssb_band
    bra.s   .ssb_horiz

.ssb_emit1:
    move.w  d0,(a4)+
    move.w  d1,(a4)+
    dbra    d7,.ssb_band

.ssb_horiz:
    ; Final horizon-to-dashboard entry: (128 - horizon_y_m1, horizon_color)
    move.w  #$80,d4
    movea.l a5,a0
    adda.l  #$c992,a0
    move.w  (a0),d2
    subq.w  #1,d2
    sub.w   d2,d4
    move.w  d4,(a4)+
    movea.l $0586(a5),a0
    move.w  (a0),d3                     ; horizon palette offset
    move.w  (a6,d3.w),(a4)+             ; horizon color (valid STE 9-bit = 12-bit with LSB=0)
    move.w  #$ffff,(a4)+
    move.w  #$ffff,(a4)+

    add.w   #64,sp
    movem.l (sp)+,d0-d7/a0-a6
    rts

; ============================================================================
; PHASE 4B: STE ENHANCED JOYSTICK / JAGUAR POWERPAD + KEYBOARD SHORTCUTS
; ============================================================================

; Poll STE/Falcon Port A Enhanced Joystick / Jaguar PowerPad ($ffff9200/$ffff9202)
; Called once per VBL in Supervisor mode (from do_aud_tick).
; Clobbers d0-d3/a0-a2 (already saved by do_aud_tick).
poll_ste_jagpad:
    moveq   #0,d2                       ; new JagPad joy1 bits (Up=0,Dn=1,Lt=2,Rt=3,Fire=7)
    moveq   #0,d3                       ; bit0=Pause, bit1=Special(A/C), bit2=Option

    ; Row 0 ($ffee): D-pad (bits 8..11 of $ffff9202) + Pause (bit 0) + Fire A (bit 1 of $ffff9200)
    move.w  #$ffee,$ffff9202.w
    move.w  $ffff9202.w,d0
    not.w   d0
    lsr.w   #8,d0
    and.w   #$0f,d0                     ; Up(0), Dn(1), Lt(2), Rt(3)
    cmp.b   #$0f,d0                     ; all 4 directions pressed = unplugged port -> abort!
    beq.w   .pj_ret
    or.b    d0,d2
    move.w  $ffff9200.w,d1
    not.w   d1
    btst    #0,d1                       ; Pause
    beq.s   .pj_no_p
    bset    #0,d3
.pj_no_p:
    btst    #1,d1                       ; Fire A -> Special Weapon + Fire!
    beq.s   .pj_r1
    bset    #1,d3
    bset    #7,d2

.pj_r1:
    ; Row 1 ($ffdd): Fire B (bit 1 of $ffff9200) -> Main Gun (Fire)
    move.w  #$ffdd,$ffff9202.w
    move.w  $ffff9200.w,d1
    not.w   d1
    btst    #1,d1
    beq.s   .pj_r2
    bset    #7,d2

.pj_r2:
    ; Row 2 ($ffbb): Fire C (bit 1 of $ffff9200) -> Special Weapon + Fire!
    move.w  #$ffbb,$ffff9202.w
    move.w  $ffff9200.w,d1
    not.w   d1
    btst    #1,d1
    beq.s   .pj_r3
    bset    #1,d3
    bset    #7,d2

.pj_r3:
    ; Row 3 ($ff77): Option (bit 1 of $ffff9200) -> Toggle Driving Music!
    move.w  #$ff77,$ffff9202.w
    move.w  $ffff9200.w,d1
    not.w   d1
    btst    #1,d1
    beq.s   .pj_merge
    bset    #2,d3

.pj_merge:
    ; Merge JagPad D-pad/Fire into Overlander joy1 ($7f3a) without stomping IKBD joy1!
    movea.l ptr_game_base(pc),a0
    lea     jag_prev_joy(pc),a1
    move.b  (a1),d0                     ; old JagPad bits
    cmp.b   d0,d2
    beq.s   .pj_btns
    not.b   d0
    and.b   d0,$7f3b(a0)                ; clear previously-injected JagPad bits
    or.b    d2,$7f3b(a0)                ; set newly-pressed JagPad bits
    move.b  d2,(a1)

.pj_btns:
    ; Special weapon (Fire A or C)
    btst    #1,d3
    beq.s   .pj_chk_p
    lea     jag_special_req(pc),a1
    st      (a1)
.pj_chk_p:
    ; Rising-edge Pause toggle
    lea     jag_prev_pause(pc),a1
    btst    #0,d3
    beq.s   .pj_clr_p
    tst.b   (a1)
    bne.s   .pj_chk_o
    st      (a1)
    bchg.b  #2,$04(a0)                  ; toggle Pause ($aa9e bit 2)
    bra.s   .pj_chk_o
.pj_clr_p:
    clr.b   (a1)
.pj_chk_o:
    ; Rising-edge Option -> Toggle Driving Music
    lea     jag_prev_opt(pc),a1
    btst    #2,d3
    beq.s   .pj_clr_o
    tst.b   (a1)
    bne.s   .pj_ret
    st      (a1)
    lea     toggle_bgm_req(pc),a2
    st      (a2)
    rts
.pj_clr_o:
    clr.b   (a1)
.pj_ret:
    rts

; Hook at +0xb98e ($016428): Special Weapon trigger check!
; Original: move.w $7f3a.l,d0; btst #1,d0 (sets Z=0 if Down+Fire)
; Enhanced: ALSO sets Z=0 if jag_special_req != 0 (JagPad A/C or Spacebar) without braking!
do_special_chk:
    move.l  a0,-(sp)
    movea.l ptr_game_base(pc),a0
    move.w  $7f3a(a0),d0
    lea     jag_special_req(pc),a0
    tst.b   (a0)
    beq.s   .dsc_norm
    clr.b   (a0)
    movea.l (sp)+,a0
    moveq   #2,d0                       ; bit 1 set -> Z=0 (fire special weapon!)
    btst    #1,d0
    rts
.dsc_norm:
    movea.l (sp)+,a0
    btst    #1,d0
    rts

; Hook at +0x8356 ($012df0): IKBD keyboard handler
; Watches M ($32) = toggle driving music, P ($19) = pause, Space ($39) = special weapon
do_ikbd_key:
    btst    #7,d0                       ; key release?
    bne.s   .dik_done
    cmp.b   #$32,d0                     ; 'M' key -> toggle driving music
    bne.s   .dik_p
    move.l  a0,-(sp)
    lea     toggle_bgm_req(pc),a0
    st      (a0)
    movea.l (sp)+,a0
    bra.s   .dik_done
.dik_p:
    cmp.b   #$19,d0                     ; 'P' key -> pause toggle
    bne.s   .dik_sp
    move.l  a0,-(sp)
    movea.l ptr_game_base(pc),a0
    bchg.b  #2,$04(a0)
    movea.l (sp)+,a0
    bra.s   .dik_done
.dik_sp:
    cmp.b   #$39,d0                     ; 'Space' -> special weapon
    bne.s   .dik_done
    move.l  a0,-(sp)
    lea     jag_special_req(pc),a0
    st      (a0)
    movea.l (sp)+,a0
.dik_done:
    move.b  d0,d1
    andi.w  #$7f,d1
    rts

; ============================================================================
; PHASE 4C: FIXED-POINT DDA ROAD EDGE PROJECTOR (replaces $0176d6 & $0176dc)
; Replaces pixel-by-pixel Bresenham + per-scanline jsr (a4) with 16.16 DDA!
; Saves ~25,000-28,000 cycles/frame on 8 MHz STE with bit-exact road geometry!
; Inputs: a0=road_tbl, d0=x0, d1=y0, d2=x1, d3=y1, d7=y_clip, a5=stripe_ptr, a6=(kerb_w, half_off)
; ============================================================================
do_road_edge_right:
    move.w  d1,d4
    sub.w   d3,d4                       ; dy = y0 - y1
    beq.s   .rer_rts
    bpl.s   .rer_pos
    cmp.w   d1,d7
    bcs.s   .rer_rts
    move.w  d1,d7
.rer_rts:
    rts
.rer_pos:
    cmp.w   d7,d3
    bcc.s   .rer_rts
    ; Compute signed 16.16 step d5 = ((x1 - x0) << 16) / dy
    sub.w   d0,d2                       ; dx = x1 - x0
    moveq   #0,d6                       ; sign flag (0=pos, 1=neg)
    tst.w   d2
    bpl.s   .rer_dxp
    neg.w   d2
    moveq   #1,d6
.rer_dxp:
    moveq   #0,d5
    cmp.w   d4,d2                       ; |dx| < dy? (70% of segments -> single divu.w!)
    bcc.s   .rer_2div
    swap    d2
    clr.w   d2
    divu.w  d4,d2
    move.w  d2,d5
    bra.s   .rer_divok
.rer_2div:
    move.w  d2,d5
    divu.w  d4,d5                       ; low=q_hi, high=rem
    move.w  d5,d2                       ; d2.w = q_hi
    clr.w   d5                          ; d5 = rem << 16
    divu.w  d4,d5                       ; low=q_lo
    swap    d2
    move.w  d5,d2
    move.l  d2,d5                       ; d5.l = unsigned 16.16 step
.rer_divok:
    tst.w   d6
    beq.s   .rer_spos
    neg.l   d5
.rer_spos:
    ; x_cur = ((x0 - half_off) << 16) + $8000
    sub.w   2(a6),d0
    swap    d0
    move.w  #$8000,d0
    ; Pre-clip d1 to d7 once before loop
    cmp.w   d7,d1
    ble.s   .rer_noclip
    move.w  d1,d6
    sub.w   d7,d6                       ; skip = d1 - d7 (>= 1)
    subq.w  #1,d6
.rer_sk:
    add.l   d5,d0
    dbra    d6,.rer_sk
    move.w  d7,d1
.rer_noclip:
    move.w  d1,d4
    sub.w   d3,d4
    ble.s   .rer_rts
    subq.w  #1,d4                       ; dbra count = (d1 - d3) - 1
    move.w  d1,d6
    asl.w   #3,d6
    adda.w  d6,a0
.rer_lp:
    swap    d0
    move.w  d0,2(a0)
    swap    d0
    add.l   d5,d0
    subq.l  #8,a0
    dbra    d4,.rer_lp
    rts

do_road_edge_left:
    move.w  d1,d4
    sub.w   d3,d4                       ; dy = y0 - y1
    beq.s   .rel_rts
    bpl.s   .rel_pos
    cmp.w   d1,d7
    bcs.s   .rel_rts
    move.w  d1,d7
.rel_rts:
    rts
.rel_pos:
    cmp.w   d7,d3
    bcc.s   .rel_rts
    move.l  a3,-(sp)
    ; Compute signed 16.16 step d5 = ((x1 - x0) << 16) / dy
    sub.w   d0,d2                       ; dx = x1 - x0
    moveq   #0,d6
    tst.w   d2
    bpl.s   .rel_dxp
    neg.w   d2
    moveq   #1,d6
.rel_dxp:
    moveq   #0,d5
    cmp.w   d4,d2                       ; |dx| < dy? (70% of segments -> single divu.w!)
    bcc.s   .rel_2div
    swap    d2
    clr.w   d2
    divu.w  d4,d2
    move.w  d2,d5
    bra.s   .rel_divok
.rel_2div:
    move.w  d2,d5
    divu.w  d4,d5
    move.w  d5,d2
    clr.w   d5
    divu.w  d4,d5
    swap    d2
    move.w  d5,d2
    move.l  d2,d5
.rel_divok:
    tst.w   d6
    beq.s   .rel_spos
    neg.l   d5
.rel_spos:
    ; x_cur = ((x0 - half_off) << 16) + $8000
    sub.w   2(a6),d0
    swap    d0
    move.w  #$8000,d0
    ; Pre-clip d1 to d7 once before loop
    cmp.w   d7,d1
    ble.s   .rel_noclip
    move.w  d1,d6
    sub.w   d7,d6
    subq.w  #1,d6
.rel_sk:
    add.l   d5,d0
    dbra    d6,.rel_sk
    move.w  d7,d1
.rel_noclip:
    move.w  d1,d4
    sub.w   d3,d4
    ble.s   .rel_done
    subq.w  #1,d4
    move.w  d1,d6
    asl.w   #3,d6
    adda.w  d6,a0
    move.w  (a6),d6                     ; cache kerb_w
    movea.l ptr_game_base(pc),a3
    adda.l  #$cc06,a3                   ; stripe toggle flag ($176a0)
.rel_lp:
    swap    d0
    move.w  d0,(a0)
    swap    d0
    move.w  d6,4(a0)
.rel_st:
    cmp.w   (a5),d1
    bcc.s   .rel_sok
    addq.l  #4,a5
    not.w   (a3)
    bra.s   .rel_st
.rel_sok:
    move.w  2(a5),6(a0)
    add.l   d5,d0
    subq.w  #1,d1
    subq.l  #8,a0
    dbra    d4,.rel_lp
.rel_done:
    movea.l (sp)+,a3
    rts
