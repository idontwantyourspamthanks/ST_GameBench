; ============================================================================
; Flood (Bullfrog, 1990) — STE Blitter + 25 Hz Pacer + Amiga Visuals + Full Amiga STE DMA Audio
; Assembled with: vasmm68k_mot -Ftos -m68000 -spaces -o flood_patch.tos flood_patch.s
; Linked into FLO.PRG by tools/build_flood.py (relocatable TOS .PRG).
; ============================================================================

; Hardware registers
BLT_BASE        equ     $ffff8a00
BLT_SRC_XINC    equ     $20
BLT_SRC_YINC    equ     $22
BLT_SRC_ADDR    equ     $24
BLT_ENDMASK1    equ     $28
BLT_ENDMASK2    equ     $2a
BLT_ENDMASK3    equ     $2c
BLT_DST_XINC    equ     $2e
BLT_DST_YINC    equ     $30
BLT_DST_ADDR    equ     $32
BLT_XCOUNT      equ     $36
BLT_YCOUNT      equ     $38
BLT_HOP         equ     $3a
BLT_OP          equ     $3b
BLT_LINE_NUM    equ     $3c
BLT_SKEW        equ     $3d

DMA_CTRL        equ     $ffff8901
DMA_START_HI    equ     $ffff8903
DMA_START_MID   equ     $ffff8905
DMA_START_LO    equ     $ffff8907
DMA_CNT_HI      equ     $ffff8909
DMA_CNT_MID     equ     $ffff890b
DMA_CNT_LO      equ     $ffff890d
DMA_END_HI      equ     $ffff890f
DMA_END_MID     equ     $ffff8911
DMA_END_LO      equ     $ffff8913
DMA_MODE        equ     $ffff8921
DMA_RING_SLOTS  equ     8               ; 8 x 250 B = 2000 B ring buffer (80ms @ 12517Hz)
DMA_RING_BYTES  equ     2000

; Virtual Paula channel struct (32 bytes per channel, 4 channels = 128 bytes)
VCH_SAMP_PTR    equ     0       ; .l sample start addr
VCH_SAMP_LEN    equ     4       ; .l sample length in bytes
VCH_LOOP_PTR    equ     8       ; .l loop start addr
VCH_LOOP_LEN    equ     12      ; .l loop length in bytes (<=4 = one-shot)
VCH_POS_INT     equ     16      ; .w integer byte offset
VCH_POS_FRAC    equ     18      ; .w 16-bit fractional offset
VCH_STEP_INT    equ     20      ; .w integer step per 12517 Hz sample
VCH_STEP_FRAC   equ     22      ; .w fractional step per 12517 Hz sample
VCH_VOL         equ     24      ; .w volume (0..64)
VCH_ACTIVE      equ     26      ; .b 0=off, 1=playing
VCH_SIZE        equ     32

; Exported jump table at start of patch (fixed offsets for build_flood.py):
;   +0:  patch_init        (replaces jsr $1ab48 at text+$0042)
;   +4:  patch_vbl_pace    (replaces jsr $126dc at text+$0d18)
;   +8:  patch_draw_tiles  (replaces code at text+$1170)
;   +12: patch_spr32       (replaces code at text+$bcd2)
;   +16: patch_ym_safe     (replaces movep.l/w at text+$875e)
;   +20: patch_cam_x       (replaces jerky chunk scroll at text+$1090 = RAM $13606)
;   +24: patch_vbl_audio   (replaces jsr $1b4fa at text+$012e)
;   +28: patch_title_hook  (replaces jsr $14d08 at text+$0606)
;   +32: patch_game_hook   (replaces jsr $12dec at text+$0632)
;   +36: patch_sfx_hook    (replaces entry of sub_01b7be at text+$9248)
;   +40: patch_exit_hook   (replaces jsr $1b598 at text+$0668)
;   +44: vpaula_update     (called from Amiga blob +$0aa2)
;   +48: vpaula_stop_ch    (called from Amiga blob +$0e8c)
;   +52: vpaula_stop_all   (called from Amiga blob +$06ee)
;   +56: patch_water_scroll (replaces entry of sub_013988 at text+$1412)
;
; Pointer slots patched by build_flood.py (and relocated by TOS):
;   +60:  ptr_orig_init      (.l -> text+$85d2)
;   +64:  ptr_vbl_cnt        (.l -> BSS VBL counter)
;   +68:  ptr_vbl_flag       (.l -> BSS VBL flag)
;   +72:  ptr_tiles_cpu_eq   (.l -> text+$11f6)
;   +76:  ptr_tiles_cpu_ne   (.l -> text+$1178)
;   +80:  ptr_spr32_cpu      (.l -> text+$bcd8)
;   +84:  ptr_scroll_x       (.l -> BSS $1e874)
;   +88:  ptr_player_x       (.l -> BSS $1e6f8)
;   +92:  ptr_orig_vbl_mus   (.l -> text+$8f84 = RAM $1b4fa)
;   +96:  ptr_orig_title     (.l -> text+$2792 = RAM $14d08)
;   +100: ptr_orig_game      (.l -> text+$0876 = RAM $12dec)
;   +104: ptr_orig_sfx_cont  (.l -> text+$9250 = RAM $1b7c6)
;   +108: ptr_orig_exit      (.l -> text+$9022 = RAM $1b598)
;   +112: ptr_am_blob        (.l -> relocated 3932B Amiga sequencer blob)
;   +116: ptr_max_scroll_x   (.l -> text+$926a = RAM $1b7e0)
;   +120: ptr_cam_y_cont     (.l -> text+$1134 = RAM $136aa)
;   +124: ptr_cam_x_cpu      (.l -> text+$1096 = RAM $1360c)
;   +128: ptr_water_map      (.l -> BSS $1e75c)
;   +132: ptr_wblocks_ptr    (.l -> BSS $1e7de)
;   +136: ptr_water_tog      (.l -> BSS $1e674)
;   +140: ptr_scroll_y       (.l -> BSS $1e876)
;   +144: ptr_backbuf        (.l -> BSS $2695a)
;   +148: ptr_water_cpu      (.l -> text+$141c = RAM $13992)

        section text

patch_entry:
        bra.w   patch_init              ; +0
        bra.w   patch_vbl_pace          ; +4
        bra.w   patch_draw_tiles        ; +8
        bra.w   patch_spr32             ; +12
        bra.w   patch_ym_safe           ; +16
        bra.w   patch_cam_x             ; +20
        bra.w   patch_vbl_audio         ; +24
        bra.w   patch_title_hook        ; +28
        bra.w   patch_game_hook         ; +32
        bra.w   patch_sfx_hook          ; +36
        bra.w   patch_exit_hook         ; +40
        bra.w   vpaula_update           ; +44
        bra.w   vpaula_stop_ch          ; +48
        bra.w   vpaula_stop_all         ; +52
        bra.w   patch_water_scroll      ; +56

ptr_orig_init:     dc.l 0               ; +60
ptr_vbl_cnt:       dc.l 0               ; +64
ptr_vbl_flag:      dc.l 0               ; +68
ptr_tiles_cpu_eq:  dc.l 0               ; +72
ptr_tiles_cpu_ne:  dc.l 0               ; +76
ptr_spr32_cpu:     dc.l 0               ; +80
ptr_scroll_x:      dc.l 0               ; +84
ptr_player_x:      dc.l 0               ; +88
ptr_orig_vbl_mus:  dc.l 0               ; +92
ptr_orig_title:    dc.l 0               ; +96
ptr_orig_game:     dc.l 0               ; +100
ptr_orig_sfx_cont: dc.l 0               ; +104
ptr_orig_exit:     dc.l 0               ; +108
ptr_am_blob:       dc.l 0               ; +112
ptr_max_scroll_x:  dc.l 0               ; +116
ptr_cam_y_cont:    dc.l 0               ; +120
ptr_cam_x_cpu:     dc.l 0               ; +124
ptr_water_map:     dc.l 0               ; +128
ptr_wblocks_ptr:   dc.l 0               ; +132
ptr_water_tog:     dc.l 0               ; +136
ptr_scroll_y:      dc.l 0               ; +140
ptr_backbuf:       dc.l 0               ; +144
ptr_water_cpu:     dc.l 0               ; +148
ptr_frontbuf:      dc.l 0               ; +152
ptr_joy_byte:      dc.l 0               ; +156 (BSS $26a68 = Joy 1 state)
ptr_orig_kbd_key:  dc.l 0               ; +160 (text+$02ce = RAM $012844)
        bra.w   patch_ikbd_isr          ; +164 (replaces IKBD vector $127f0)
ptr_surf_bits:     dc.l 0               ; +168 (DATA $1e7be = surface contact bits)
ptr_water_depth:   dc.l 0               ; +172 (TEXT $1a192 = sub_01a192)
        bra.w   patch_anim_step         ; +176 (replaces add.w $1e674.l,d5 at text+$ae4e)

; ============================================================================
; 1. patch_init — switch to ST Low (fixes TT Medium / ST Med), call orig init,
;                 probe STE Blitter/DMA, load Amiga audio
; ============================================================================
patch_init:
        ; Save current rez and switch to ST Low (0 = 320x200x16) if needed (fixes TT Medium!)
        movem.l d0-d2/a0-a2, -(a7)
        move.w  #4, -(a7)               ; XBIOS Getrez()
        trap    #14
        addq.l  #2, a7
        move.w  d0, orig_rez
        tst.w   d0
        beq.s   .already_low
        clr.w   -(a7)                   ; rez = 0 (ST Low)
        move.l  #-1, -(a7)              ; phys = unchanged
        move.l  #-1, -(a7)              ; log  = unchanged
        move.w  #5, -(a7)               ; XBIOS Setscreen
        trap    #14
        lea     12(a7), a7
.already_low:
        movem.l (a7)+, d0-d2/a0-a2

        move.l  ptr_orig_init(pc), a0
        jsr     (a0)

        movem.l d0-d7/a0-a6, -(a7)
        move.w  sr, -(a7)
        ori.w   #$0700, sr

        ; Probe STE Blitter ($ffff8a3c.w)
        move.l  $8.w, a2
        move.l  a7, a1
        lea     .no_blitter(pc), a0
        move.l  a0, $8.w
        clr.b   has_blitter
        tst.b   $ffff8a3c.w
        st.b    has_blitter
.no_blitter:
        move.l  a1, a7
        move.l  a2, $8.w

        ; Probe STE DMA audio ($ffff8901.w)
        lea     .no_dma(pc), a0
        move.l  a0, $8.w
        clr.b   has_dma
        tst.b   $ffff8901.w
        st.b    has_dma
.no_dma:
        move.l  a1, a7
        move.l  a2, $8.w

        ; Disable IKBD mouse reporting ($12) so mouse motion never corrupts Joy1/keys!
.ikbd_wait_m:
        btst.b  #1, $fffffc00.w
        beq.s   .ikbd_wait_m
        move.b  #$12, $fffffc02.w

        move.l  ptr_vbl_cnt(pc), a0
        move.l  (a0), last_frame_vbl

        move.w  (a7)+, sr

        ; If STE DMA present, try to load AM_MUS.BIN + AM_SFX.BIN into Malloc RAM
        clr.b   am_dma_ready
        clr.l   bg_cache_ptr
        clr.b   bg_valid
        tst.b   has_dma
        beq.w   .try_bg_only

        ; Allocate 268,288 B (AM_MUS 130048 + AM_SFX 99584 + 4KB vol_tbl + 2KB dma_ring + 32256 bg_cache)
        move.l  #268288, -(a7)
        move.w  #$48, -(a7)             ; GEMDOS Malloc
        trap    #1
        addq.l  #6, a7
        tst.l   d0
        ble.s   .try_bg_only            ; low RAM (e.g. 512KB or heavy HD driver): still try 32KB bg_cache!

        move.l  d0, a5                  ; a5 = allocated audio+bg arena
        move.l  a5, am_mus_buf          ; +0: AM_MUS.BIN (129920 B)
        move.l  a5, a4
        adda.l  #130048, a4             ; even-aligned
        move.l  a4, am_sfx_buf          ; +130048: AM_SFX.BIN (99460 B)
        move.l  a4, a3
        adda.l  #99584, a3
        move.l  a3, vol_tbl_ptr         ; 4096 B volume lookup table
        lea     4096(a3), a2
        move.l  a2, dma_ring_ptr        ; 2000 B (8 x 250B) circular stereo DMA ring
        lea     2048(a2), a2
        move.l  a2, bg_cache_ptr        ; 32256 B (21 tiles = 168B/line x 192 lines)
        bra.s   .load_am_audio

.try_bg_only:
        tst.b   has_blitter
        bne.s   .alloc_bg_only
        tst.b   has_dma
        beq.w   .init_done
.alloc_bg_only:
        move.l  #32256, -(a7)
        move.w  #$48, -(a7)
        trap    #1
        addq.l  #6, a7
        tst.l   d0
        ble.w   .init_done
        move.l  d0, bg_cache_ptr
        bra.w   .init_done

.load_am_audio:

        ; Load AM_MUS.BIN (129920 B)
        lea     fn_am_mus(pc), a0
        move.l  am_mus_buf(pc), a1
        move.l  #129920, d0
        bsr.w   load_file
        tst.l   d0
        ble.w   .init_done

        ; Load AM_SFX.BIN (99460 B)
        lea     fn_am_sfx(pc), a0
        move.l  am_sfx_buf(pc), a1
        move.l  #99460, d0
        bsr.w   load_file
        tst.l   d0
        ble.w   .init_done

        ; Build 16-level x 256-byte signed volume table (max output +/-63 so 2ch never clip!)
        ; vol_tbl[lvl * 256 + (u8)samp] = ((s8)samp * lvl) >> 5
        ; lvl = 0..15 -> max = (127 * 15) >> 5 = 59 (safe headroom for 2 channels per ear!)
        move.l  vol_tbl_ptr(pc), a0
        moveq   #0, d1                  ; lvl = 0..15
.vt_lvl:
        moveq   #0, d2                  ; sample byte = 0..255
.vt_samp:
        move.b  d2, d0
        ext.w   d0                      ; signed -128..+127
        muls.w  d1, d0
        asr.w   #5, d0                  ; / 32 -> -60..+59
        move.b  d0, (a0)+
        addq.w  #1, d2
        cmp.w   #256, d2
        blt.s   .vt_samp
        addq.w  #1, d1
        cmp.w   #16, d1
        blt.s   .vt_lvl

        ; Clear 2000 B DMA ring buffer (500 longs) and virtual Paula channels
        move.l  dma_ring_ptr(pc), a0
        move.w  #499, d0
.clr_dma:
        clr.l   (a0)+
        dbra    d0, .clr_dma
        bsr.w   vpaula_stop_all

        ; Start STE DMA stereo 12,517 Hz continuous loop over 2000-byte ring buffer
        ; (Hardware cursor-tracked in VBL: works identically at 50 Hz, 60 Hz, and 71 Hz!)
        clr.b   DMA_CTRL.w
        move.b  #$01, DMA_MODE.w        ; $01 = 12,517 Hz, stereo signed 8-bit
        move.l  dma_ring_ptr(pc), d0
        bsr.w   set_dma_ring
        move.b  #$03, DMA_CTRL.w        ; play + loop continuously
        move.w  #4, dma_wr_slot         ; start writing 4 slots (40ms) ahead of DMA cursor
        clr.b   am_mode
        st.b    am_dma_ready

.init_done:
        movem.l (a7)+, d0-d7/a0-a6
        rts

; Helper: load_file(a0=filename, a1=buf, d0=max_len) -> d0=bytes_read (or <=0)
load_file:
        movem.l d1-d2/a0-a2, -(a7)
        move.l  d0, d2
        move.l  a1, a2
        clr.w   -(a7)                   ; read-only
        move.l  a0, -(a7)
        move.w  #$3d, -(a7)             ; Fopen
        trap    #1
        addq.l  #8, a7
        tst.l   d0
        bmi.s   .lf_err
        move.w  d0, d1                  ; handle
        move.l  a2, -(a7)
        move.l  d2, -(a7)
        move.w  d1, -(a7)
        move.w  #$3f, -(a7)             ; Fread
        trap    #1
        lea     12(a7), a7
        move.l  d0, d2
        move.w  d1, -(a7)
        move.w  #$3e, -(a7)             ; Fclose
        trap    #1
        addq.l  #4, a7
        move.l  d2, d0
.lf_err:
        movem.l (a7)+, d1-d2/a0-a2
        rts

; Helper: set_dma_ring(d0 = ring_start, length = 2000 bytes)
set_dma_ring:
        move.l  d0, d1
        addi.l  #DMA_RING_BYTES, d1
        move.b  d0, DMA_START_LO.w
        lsr.l   #8, d0
        move.b  d0, DMA_START_MID.w
        lsr.l   #8, d0
        move.b  d0, DMA_START_HI.w
        move.b  d1, DMA_END_LO.w
        lsr.l   #8, d1
        move.b  d1, DMA_END_MID.w
        lsr.l   #8, d1
        move.b  d1, DMA_END_HI.w
        rts

; ============================================================================
; 2. patch_vbl_pace — fixed 25.0 Hz (2 VBLs/frame) gameplay pacer
; ============================================================================
patch_vbl_pace:
        movem.l d0-d1/a0-a1, -(a7)
        move.l  ptr_vbl_cnt(pc), a0
        move.l  ptr_vbl_flag(pc), a1
        move.l  last_frame_vbl(pc), d1
.wait_2vbl:
        move.l  (a0), d0
        sub.l   d1, d0
        cmp.l   #2, d0
        blt.s   .wait_2vbl
        tst.w   (a1)
        beq.s   .wait_2vbl
        cmp.l   #4, d0
        bgt.s   .snap
        addq.l  #2, d1
        move.l  d1, last_frame_vbl
        bra.s   .done
.snap:
        move.l  (a0), last_frame_vbl
.done:
        movem.l (a7)+, d0-d1/a0-a1
        rts

; ============================================================================
; 3. patch_draw_tiles — STE Blitter 1-pixel smooth horizontal + vertical tilemap
;    Renders 21-tile-wide (336x192, stride 168B) bg_cache when coarse_x/y/tiles
;    change, then STE-Blitter shifts bg_cache -> backbuffer (stride 160B) by fine_x!
; ============================================================================
patch_draw_tiles:
        tst.l   bg_cache_ptr
        beq.s   .cpu_tiles              ; no bg_cache RAM: fall back to original CPU tilemap renderer!
        tst.b   has_blitter
        bne.s   .blt_tiles
        tst.b   has_dma
        bne.w   .tt_tiles               ; TT (32 MHz, DMA, no Blitter): CPU smooth 1px scroll!
.cpu_tiles:
        andi.w  #$f, d6
        beq.s   .cpu_eq
        move.l  ptr_tiles_cpu_ne(pc), a0
        jmp     (a0)
.cpu_eq:
        move.l  ptr_tiles_cpu_eq(pc), a0
        jmp     (a0)

.blt_tiles:
        andi.w  #$f, d6
        move.l  a6, bg_cur_a6
        move.l  a5, bg_cur_a5

        ; Check if 21-tile bg_cache is valid and matches (a6, d6, d1, 21x13 tiles)
        tst.b   bg_valid
        beq.s   .rebuild_cache
        cmp.l   bg_last_a6(pc), a6
        bne.s   .rebuild_cache
        cmp.w   bg_last_d6(pc), d6
        bne.s   .rebuild_cache
        cmp.l   bg_last_d1(pc), d1
        bne.s   .rebuild_cache

        ; Verify all 13 visible rows x 21 bytes match bg_map_copy (byte-safe for odd coarse_x!)
        move.l  a6, a0
        lea     bg_map_copy(pc), a1
        moveq   #12, d3
.cmp_row:
        rept    21
        cmpm.b  (a0)+, (a1)+
        bne.s   .rebuild_cache
        endr
        lea     $6b(a0), a0             ; 128 - 21 = 107 ($6b)
        dbra    d3, .cmp_row
        bra.w   .blit_from_cache

.rebuild_cache:
        ; Snapshot 21x13 tile IDs into bg_map_copy (byte-safe for odd coarse_x!)
        move.l  a6, a0
        lea     bg_map_copy(pc), a1
        moveq   #12, d3
.snap_row:
        rept    21
        move.b  (a0)+, (a1)+
        endr
        lea     $6b(a0), a0
        dbra    d3, .snap_row

        move.l  a6, bg_last_a6
        move.w  d6, bg_last_d6
        move.l  d1, bg_last_d1
        st.b    bg_valid

        ; Render 21 tiles wide x 192 lines into bg_cache_ptr (stride 168 B/line!)
        move.l  bg_cache_ptr(pc), a5
        lea     BLT_BASE.w, a4
        move.w  #2, BLT_SRC_XINC(a4)
        move.w  #2, BLT_SRC_YINC(a4)
        move.l  #$ffffffff, BLT_ENDMASK1(a4)
        move.w  #$ffff, BLT_ENDMASK3(a4)
        move.w  #2, BLT_DST_XINC(a4)
        move.w  #162, BLT_DST_YINC(a4)  ; 168 - 3*2 = 162!
        move.w  #4, BLT_XCOUNT(a4)
        move.w  #$0203, BLT_HOP(a4)
        clr.b   BLT_SKEW(a4)
        moveq   #$ffffffc0, d7

        tst.w   d6
        beq.s   .full_12_rows

        move.w  d6, d0
        lsl.w   #3, d0
        ext.l   d0
        move.l  d1, d2
        add.l   d0, d2

        moveq   #16, d5
        sub.w   d6, d5
        moveq   #20, d4                 ; 21 tiles across!
.top_col:
        moveq   #0, d0
        move.b  (a6)+, d0
        lsl.w   #7, d0
        add.l   d2, d0
        move.l  d0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)
        addq.l  #8, a5
        dbra    d4, .top_col

        move.w  d5, d0
        subq.w  #1, d0
        mulu.w  #168, d0                ; stride 168!
        adda.w  d0, a5
        lea     $6b(a6), a6             ; 128 - 21 = $6b

        moveq   #10, d3
        bra.s   .mid_rows

.full_12_rows:
        moveq   #11, d3
.mid_rows:
        moveq   #16, d5
.row_loop:
        moveq   #20, d4                 ; 21 tiles across!
.col_loop:
        moveq   #0, d0
        move.b  (a6)+, d0
        lsl.w   #7, d0
        add.l   d1, d0
        move.l  d0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)
        addq.l  #8, a5
        dbra    d4, .col_loop

        lea     2520(a5), a5            ; +15*168 (total +16*168)
        lea     $6b(a6), a6
        dbra    d3, .row_loop

        tst.w   d6
        beq.s   .blit_from_cache
        moveq   #20, d4                 ; 21 tiles across!
.bot_col:
        moveq   #0, d0
        move.b  (a6)+, d0
        lsl.w   #7, d0
        add.l   d1, d0
        move.l  d0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d6, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)
        addq.l  #8, a5
        dbra    d4, .bot_col

.blit_from_cache:
        ; Copy bg_cache_ptr (stride 168) -> bg_cur_a5 (stride 160), shifted left by fine_x!
        lea     BLT_BASE.w, a4
        move.l  #$ffffffff, BLT_ENDMASK1(a4)
        move.w  #$ffff, BLT_ENDMASK3(a4)
        move.w  #$0203, BLT_HOP(a4)
        moveq   #$ffffffc0, d7

        move.l  ptr_scroll_x(pc), a0
        move.w  (a0), d0
        andi.w  #$f, d0                 ; d0 = fine_x (0..15)
        bne.s   .blit_shifted

        ; fine_x == 0: 32 chunks x 6 lines, all 4 planes together (max ~0.48ms HOG burst for IKBD safety)
        move.w  #2, BLT_SRC_XINC(a4)
        move.w  #10, BLT_SRC_YINC(a4)   ; 168 - 79*2 = 10
        move.w  #2, BLT_DST_XINC(a4)
        move.w  #2, BLT_DST_YINC(a4)    ; 160 - 79*2 = 2
        move.w  #80, BLT_XCOUNT(a4)
        clr.b   BLT_SKEW(a4)
        move.l  bg_cache_ptr(pc), BLT_SRC_ADDR(a4)
        move.l  bg_cur_a5(pc), BLT_DST_ADDR(a4)
        moveq   #31, d3
.copy_unshifted:
        move.w  #6, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)
        dbra    d3, .copy_unshifted
        bra.s   .tiles_done

.blit_shifted:
        ; fine_x = 1..15: 4 bitplane passes x 12 chunks x 16 lines (max ~0.33ms HOG burst -> zero ACIA overruns!)
        moveq   #16, d1
        sub.w   d0, d1
        ori.b   #$80, d1                ; FXSR | (16 - fine_x)
        move.b  d1, BLT_SKEW(a4)
        move.w  #8, BLT_SRC_XINC(a4)
        move.w  #8, BLT_SRC_YINC(a4)    ; with FXSR=1 & XCOUNT=20: reads 21 words (+160), +8 = 168!
        move.w  #8, BLT_DST_XINC(a4)
        move.w  #8, BLT_DST_YINC(a4)    ; writes 20 words (+152), +8 = 160!
        move.w  #20, BLT_XCOUNT(a4)

        move.l  bg_cache_ptr(pc), a0
        move.l  bg_cur_a5(pc), a1
        moveq   #3, d2                  ; 4 bitplanes
.plane_lp:
        move.l  a0, BLT_SRC_ADDR(a4)
        move.l  a1, BLT_DST_ADDR(a4)
        moveq   #11, d3                 ; 12 chunks x 16 lines = 192 lines
.chunk_lp:
        move.w  #16, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)
        dbra    d3, .chunk_lp
        addq.l  #2, a0
        addq.l  #2, a1
        dbra    d2, .plane_lp

.tiles_done:
        movem.l (a7)+, d1-d7/a0-a6
        rts

; --- TT (32 MHz 68030, no Blitter) CPU 1-pixel smooth tilemap ---
; Uses the exact same 21-tile bg_cache (168 B/line x 192 lines), then shifts left by fine_x!
.tt_tiles:
        andi.w  #$f, d6
        move.l  a6, bg_cur_a6
        move.l  a5, bg_cur_a5
        tst.b   bg_valid
        beq.s   .tt_rebuild
        cmp.l   bg_last_a6(pc), a6
        bne.s   .tt_rebuild
        cmp.w   bg_last_d6(pc), d6
        bne.s   .tt_rebuild
        cmp.l   bg_last_d1(pc), d1
        bne.s   .tt_rebuild

        move.l  a6, a0
        lea     bg_map_copy(pc), a1
        moveq   #12, d3
.tt_cmp_row:
        rept    21
        cmpm.b  (a0)+, (a1)+
        bne.s   .tt_rebuild
        endr
        lea     $6b(a0), a0
        dbra    d3, .tt_cmp_row
        bra.w   .tt_copy_from_cache

.tt_rebuild:
        move.l  a6, a0
        lea     bg_map_copy(pc), a1
        moveq   #12, d3
.tt_snap_row:
        rept    21
        move.b  (a0)+, (a1)+
        endr
        lea     $6b(a0), a0
        dbra    d3, .tt_snap_row

        move.l  a6, bg_last_a6
        move.w  d6, bg_last_d6
        move.l  d1, bg_last_d1
        st.b    bg_valid

        ; CPU render 21 tiles wide x 192 lines into bg_cache_ptr (stride 168 B/line)
        move.l  bg_cache_ptr(pc), a5
        tst.w   d6
        beq.s   .tt_full_12

        ; Top partial row: height = 16 - d6, src offset = d6*8
        move.w  d6, d0
        lsl.w   #3, d0
        ext.l   d0
        move.l  d1, d2
        add.l   d0, d2
        moveq   #16, d5
        sub.w   d6, d5                  ; h_top (1..15)
        bsr.s   .tt_draw_tile_row
        move.w  d5, d0
        mulu.w  #168, d0
        adda.w  d0, a5
        lea     $6b(a6), a6

        moveq   #10, d3                 ; 11 middle rows
        bra.s   .tt_mid_rows

.tt_full_12:
        moveq   #11, d3                 ; 12 middle rows
.tt_mid_rows:
        move.l  d1, d2
        moveq   #16, d5
.tt_mid_lp:
        bsr.s   .tt_draw_tile_row
        lea     2688(a5), a5            ; +16*168
        lea     $6b(a6), a6
        dbra    d3, .tt_mid_lp

        tst.w   d6
        beq.s   .tt_copy_from_cache
        move.l  d1, d2
        move.w  d6, d5
        bsr.s   .tt_draw_tile_row
        bra.s   .tt_copy_from_cache

; Helper: draw 1 row of 21 tiles (height d5, src base d2) into a5 (stride 168), advancing a6 by +21
.tt_draw_tile_row:
        movem.l d3-d4/a5, -(a7)
        moveq   #20, d4                 ; 21 tiles
.tt_col_lp:
        moveq   #0, d0
        move.b  (a6)+, d0
        lsl.w   #7, d0
        add.l   d2, d0
        move.l  d0, a0
        move.l  a5, a1
        move.w  d5, d3
        subq.w  #1, d3
.tt_ln_lp:
        move.l  (a0)+, (a1)+
        move.l  (a0)+, (a1)+
        lea     160(a1), a1             ; +168 total
        dbra    d3, .tt_ln_lp
        addq.l  #8, a5
        dbra    d4, .tt_col_lp
        movem.l (a7)+, d3-d4/a5
        rts

.tt_copy_from_cache:
        move.l  bg_cache_ptr(pc), a0
        move.l  bg_cur_a5(pc), a1
        move.l  ptr_scroll_x(pc), a2
        move.w  (a2), d7
        andi.w  #$f, d7                 ; d7 = fine_x (0..15)
        bne.s   .tt_copy_shifted

        ; fine_x == 0: 192 lines x 40 longs (160B), +8 skip on src
        move.w  #191, d3
.tt_c0_ln:
        moveq   #9, d4                  ; 10 x 16B = 160B
.tt_c0_col:
        move.l  (a0)+, (a1)+
        move.l  (a0)+, (a1)+
        move.l  (a0)+, (a1)+
        move.l  (a0)+, (a1)+
        dbra    d4, .tt_c0_col
        addq.l  #8, a0
        dbra    d3, .tt_c0_ln
        bra.w   .tiles_done

.tt_copy_shifted:
        ; fine_x = 1..15: 192 lines x 20 tile-cols x 4 planes, left-shifted by d7!
        move.w  #191, d3
.tt_cs_ln:
        moveq   #19, d4                 ; 20 x 8B = 160B
.tt_cs_col:
        rept    4
        move.w  (a0), d0
        swap    d0
        move.w  8(a0), d0
        lsl.l   d7, d0
        swap    d0
        move.w  d0, (a1)+
        addq.l  #2, a0
        endr
        dbra    d4, .tt_cs_col
        addq.l  #8, a0                  ; skip 21st tile (168B stride)
        dbra    d3, .tt_cs_ln
        bra.w   .tiles_done

; ============================================================================
; 4. patch_spr32 — STE Blitter 32x32 unclipped masked sprite renderer
; ============================================================================
patch_spr32:
        tst.b   has_blitter
        bne.s   .blt_spr32
        moveq   #$78, d1
        neg.b   d1
        subq.w  #1, d2
        move.l  ptr_spr32_cpu(pc), a0
        jmp     (a0)

.blt_spr32:
        movem.l a4-a5, -(a7)
        lea     BLT_BASE.w, a4
        move.w  #10, BLT_SRC_XINC(a4)
        move.w  #10, BLT_SRC_YINC(a4)
        move.w  #8, BLT_DST_XINC(a4)
        move.b  #2, BLT_HOP(a4)

        tst.w   d0
        beq.s   .shift_zero

        move.w  #144, BLT_DST_YINC(a4)
        move.w  #3, BLT_XCOUNT(a4)
        moveq   #-1, d3
        lsr.w   d0, d3
        move.w  d3, BLT_ENDMASK1(a4)
        move.w  #$ffff, BLT_ENDMASK2(a4)
        not.w   d3
        move.w  d3, BLT_ENDMASK3(a4)
        ori.b   #$40, d0
        move.b  d0, BLT_SKEW(a4)
        bra.s   .run_loop

.shift_zero:
        move.w  #152, BLT_DST_YINC(a4)
        move.w  #2, BLT_XCOUNT(a4)
        move.l  #$ffffffff, BLT_ENDMASK1(a4)
        move.w  #$ffff, BLT_ENDMASK3(a4)
        clr.b   BLT_SKEW(a4)

.run_loop:
        tst.w   d2
        ble.w   .spr_done
.skip_zero:
        moveq   #0, d4
        move.w  (a2)+, d4
        bne.s   .got_run
        lea     160(a1), a1
        subq.w  #1, d2
        bgt.s   .skip_zero
        bra.w   .spr_done

.got_run:
        lea     (a3, d4.l), a0
        move.w  d4, d6
        moveq   #1, d5
        subq.w  #1, d2
        beq.s   .do_blit_run
.count_run:
        addi.w  #20, d6
        cmp.w   (a2), d6
        bne.s   .do_blit_run
        addq.l  #2, a2
        addq.w  #1, d5
        subq.w  #1, d2
        bne.s   .count_run

.do_blit_run:
        moveq   #$ffffffc0, d7
        move.l  a1, a5

        move.b  #1, BLT_OP(a4)
        move.l  a0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        move.l  a0, BLT_SRC_ADDR(a4)
        addq.l  #2, a5
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        move.l  a0, BLT_SRC_ADDR(a4)
        addq.l  #2, a5
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        move.l  a0, BLT_SRC_ADDR(a4)
        addq.l  #2, a5
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        move.b  #7, BLT_OP(a4)
        move.l  a1, a5
        addq.l  #2, a0

        move.l  a0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        addq.l  #2, a0
        addq.l  #2, a5
        move.l  a0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        addq.l  #2, a0
        addq.l  #2, a5
        move.l  a0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        addq.l  #2, a0
        addq.l  #2, a5
        move.l  a0, BLT_SRC_ADDR(a4)
        move.l  a5, BLT_DST_ADDR(a4)
        move.w  d5, BLT_YCOUNT(a4)
        move.b  d7, BLT_LINE_NUM(a4)

        mulu.w  #160, d5
        adda.w  d5, a1
        bra.w   .run_loop

.spr_done:
        movem.l (a7)+, a4-a5
        rts

; ============================================================================
; 5. patch_ym_safe — Falcon-safe YM2149 digi-SFX write
; ============================================================================
patch_ym_safe:
        swap    d1
        movep.w d1, -$720f(a0)
        swap    d1
        movep.w d1, -$720f(a0)
        movep.w d0, -$720f(a0)
        rts

; ============================================================================
; 6. patch_cam_x — Smooth 1-pixel horizontal camera tracking Quiffy!
;    Replaces jerky 128-pixel chunk scrolling at RAM $013606 (text+$1090).
;    Entry: a6 = map base ($1e7b8). Exit: jumps to RAM $0136aa (scroll_y).
; ============================================================================
patch_cam_x:
        tst.b   has_blitter
        bne.s   .cam_x_smooth
        tst.b   has_dma
        beq.s   .cam_x_cpu              ; plain ST only; STE/MegaSTE/TT/Falcon all smooth-scroll!
.cam_x_smooth:
        tst.l   bg_cache_ptr
        beq.s   .cam_x_cpu

        move.l  ptr_player_x(pc), a0
        move.w  (a0), d0                ; player_x
        subi.w  #152, d0                ; center Quiffy (32px wide -> 160-8=152)
        bpl.s   .cx_ge0
        moveq   #0, d0
.cx_ge0:
        move.l  ptr_max_scroll_x(pc), a0
        cmp.w   (a0), d0
        ble.s   .cx_ok
        move.w  (a0), d0
.cx_ok:
        move.l  ptr_scroll_x(pc), a0
        move.w  d0, (a0)
        lsr.w   #4, d0
        adda.w  d0, a6
        move.l  ptr_cam_y_cont(pc), a0
        jmp     (a0)

.cam_x_cpu:
        ; Plain ST / TT (no Blitter) fallback: run original chunk-scroll camera
        ; ptr_cam_x_cpu = $1360c; $135fa = -18(a0); $1362a = $1e(a0)
        move.l  ptr_cam_x_cpu(pc), a0
        move.w  -18(a0), d0             ; original `move.w $135fa(pc), d0`
        beq.s   .cam_x_zero
        jmp     (a0)                    ; $1360c (bmi.b $1361a)
.cam_x_zero:
        jmp     $1e(a0)                 ; $1362a (original `beq.b $1362a`)

; ============================================================================
; 6b. patch_water_scroll — 1-pixel smooth water overlay matching fine_x!
;     Replaces entry of sub_013988 (text+$1412 = RAM $013988).
;     Uses native ST W_BLOCKS.BLK (2 frames x 42 tiles x 32B — no "Who's The Twat"!)
; ============================================================================
patch_water_scroll:
        movem.l d1-d7/a0-a6, -(a7)
        move.l  ptr_water_map(pc), a0
        move.l  (a0), a6                ; a6 = water map base ($1e75c)
        move.l  ptr_scroll_x(pc), a0
        move.w  (a0), d7
        andi.w  #$f, d7                 ; d7 = fine_x (0..15)
        bne.s   .water_shifted
        ; fine_x == 0: jump straight to original fast unshifted water renderer ($13992)
        move.l  ptr_water_cpu(pc), a0
        jmp     (a0)

.water_shifted:
        move.l  ptr_wblocks_ptr(pc), a0
        move.l  (a0), a4                ; a4 = W_BLOCKS.BLK base ($1e7de)
        move.l  ptr_water_tog(pc), a0
        tst.w   (a0)
        bne.s   .wt_f0
        lea     $540(a4), a4
.wt_f0:
        move.l  ptr_scroll_x(pc), a0
        move.w  (a0), d0
        lsr.w   #4, d0
        adda.w  d0, a6                  ; + coarse_x

        move.l  ptr_scroll_y(pc), a0
        move.w  (a0), d0
        move.w  d0, d6                  ; d6 = scroll_y
        andi.w  #$fff0, d0
        lsl.w   #3, d0
        adda.w  d0, a6                  ; + coarse_y * 128

        move.l  ptr_backbuf(pc), a0
        move.l  (a0), a1
        addq.l  #4, a1                  ; a1 = backbuf + 4 (planes 2 & 3!)

        andi.w  #$f, d6                 ; d6 = fine_y (0..15)
        moveq   #16, d5
        sub.w   d6, d5                  ; d5 = h_top = 16 - fine_y
        move.w  d6, d2
        add.w   d2, d2                  ; d2 = top tile byte offset = fine_y * 2
        ; Row 0 (top partial row, height d5, tile src + d2)
        bsr.s   .draw_w_row
        move.w  d5, d0
        mulu.w  #160, d0
        adda.w  d0, a1
        lea     $6b(a6), a6             ; 128 - 21 = $6b

        ; Middle 11 full rows (height 16, tile src + 0)
        moveq   #0, d2
        moveq   #16, d5
        moveq   #10, d3                 ; 11 rows
.w_mid_lp:
        bsr.s   .draw_w_row
        lea     2560(a1), a1            ; +16*160
        lea     $6b(a6), a6
        dbra    d3, .w_mid_lp

        ; Bottom partial row (if fine_y != 0, height = fine_y)
        tst.w   d6
        beq.s   .w_done
        move.w  d6, d5
        bsr.s   .draw_w_row

.w_done:
        movem.l (a7)+, d1-d7/a0-a6
        rts

; Draw one row of 21 water tiles shifted left by d7 (1..15) pixels!
; Inputs: a6=water map row, a4=W_BLOCKS frame, a1=screen row + 4, d5=height (1..16), d2=src_y_off, d7=fine_x
.draw_w_row:
        movem.l d3-d6/a1, -(a7)
        moveq   #0, d4                  ; col = 0..20
.w_col_lp:
        moveq   #0, d0
        move.b  (a6)+, d0
        beq.s   .w_next_col
        lsl.w   #5, d0                  ; * 32 bytes per 1-plane water tile
        lea     (a4, d0.w), a0
        adda.w  d2, a0                  ; + top-clip byte offset
        move.l  a1, a5                  ; screen ptr for col (planes 2 & 3)
        move.w  d5, d1
        subq.w  #1, d1                  ; line dbra count

        ; Check if col==0 (clip left), col==20 (clip right), or interior (1..19)
        tst.w   d4
        beq.s   .w_col0
        cmp.w   #20, d4
        beq.s   .w_col20

        ; Interior column (1..19): write low word to (a5), high word to -8(a5)
.w_int_ln:
        moveq   #0, d0
        move.w  (a0)+, d0
        lsl.l   d7, d0
        or.w    d0, (a5)
        or.w    d0, 2(a5)
        swap    d0
        or.w    d0, -8(a5)
        or.w    d0, -6(a5)
        lea     160(a5), a5
        dbra    d1, .w_int_ln
        bra.s   .w_next_col

.w_col0:
        ; Column 0: only write low word to (a5) (left overflow clipped)
.w_c0_ln:
        move.w  (a0)+, d0
        lsl.w   d7, d0
        or.w    d0, (a5)
        or.w    d0, 2(a5)
        lea     160(a5), a5
        dbra    d1, .w_c0_ln
        bra.s   .w_next_col

.w_col20:
        ; Column 20: only write high word to -8(a5) (right overflow clipped)
.w_c20_ln:
        moveq   #0, d0
        move.w  (a0)+, d0
        lsl.l   d7, d0
        swap    d0
        or.w    d0, -8(a5)
        or.w    d0, -6(a5)
        lea     160(a5), a5
        dbra    d1, .w_c20_ln

.w_next_col:
        addq.l  #8, a1
        addq.w  #1, d4
        cmp.w   #21, d4
        blt.s   .w_col_lp
        movem.l (a7)+, d3-d6/a1
        rts

; ============================================================================
; 7. PHASE 3 — FULL AMIGA AUDIO ON STE DMA (12,517 Hz Stereo)
; ============================================================================

; Amiga blob relative offsets (from ptr_am_blob):
;   +$0000: am_play_sfx_id(id.w on stack)
;   +$0148: am_ws ($16720)
;   +$04f8: am_inst_ptr ($16ad0) -> points to INSTR.DA+4 or FLDFX.IN+4
;   +$0700: am_play_sfx(id.w, flags.w on stack)
;   +$087e: am_init_song(song_idx.w, song_ptr.l on stack)
;   +$093e: am_play_music(id.w, flags.w on stack)
;   +$0a66: am_tick_core (expects a6 = am_ws, saves d0-d7/a0-a5, returns via rts)

; --- Start Amiga Title Music (TRACK.DA + INSTR.DA) ---
start_amiga_music:
        tst.b   am_dma_ready
        beq.s   .sam_ret
        movem.l d0-d2/a0-a2, -(a7)
        move.w  sr, -(a7)
        ori.w   #$0700, sr              ; atomic switch vs VBL

        clr.b   am_mode
        bsr.w   vpaula_stop_all

        move.l  ptr_am_blob(pc), a2
        ; Set am_inst_ptr ($16ad0 = blob+$04f8) = am_mus_buf + 9344 + 4
        move.l  am_mus_buf(pc), d0
        addi.l  #9348, d0
        move.l  d0, $04f8(a2)

        ; Call am_init_song(0, am_mus_buf)
        move.l  am_mus_buf(pc), -(a7)
        clr.w   -(a7)
        jsr     $087e(a2)
        addq.l  #6, a7

        ; Call am_play_music(0, $00a0) -> start + loop!
        move.w  #$00a0, -(a7)
        clr.w   -(a7)
        jsr     $093e(a2)
        addq.l  #4, a7

        move.b  #1, am_mode             ; 1 = music active
        move.w  (a7)+, sr
        movem.l (a7)+, d0-d2/a0-a2
.sam_ret:
        rts

; --- Switch to Amiga In-Game SFX (FLDFX.DU + FLDFX.IN) ---
start_amiga_sfx:
        tst.b   am_dma_ready
        beq.s   .sas_ret
        movem.l d0-d2/a0-a2, -(a7)
        move.w  sr, -(a7)
        ori.w   #$0700, sr

        clr.b   am_mode
        bsr.w   vpaula_stop_all

        move.l  ptr_am_blob(pc), a2
        ; Set am_inst_ptr ($16ad0 = blob+$04f8) = am_sfx_buf + 2112 + 4
        move.l  am_sfx_buf(pc), d0
        addi.l  #2116, d0
        move.l  d0, $04f8(a2)

        ; Call am_init_song(0, am_sfx_buf)
        move.l  am_sfx_buf(pc), -(a7)
        clr.w   -(a7)
        jsr     $087e(a2)
        addq.l  #6, a7

        ; Enable sequencer tick flag $1a(am_ws) = $ff
        st.b    $0148+$1a(a2)
        move.b  #2, am_mode             ; 2 = SFX active
        move.w  (a7)+, sr
        movem.l (a7)+, d0-d2/a0-a2
.sas_ret:
        rts

; --- Hook: Title Screen (replaces jsr $14d08) ---
patch_title_hook:
        bsr.w   start_amiga_music
        bsr.w   draw_credit_banner
        move.l  ptr_orig_title(pc), a0
        jsr     (a0)                    ; returns chosen level in d0.w
        ; Pop up native-font "LOADING LEVEL / PLEASE WAIT" box while level loads
        movem.l d0-d4/a0-a2, -(a7)
        lea     loading_box_str(pc), a0
        move.l  ptr_frontbuf(pc), a1
        move.l  (a1), a1
        moveq   #$50, d2                ; y = 80 (matches PLAY LEVEL / PASSWORD box)
        moveq   #$12, d3                ; 18 bytes per line
        moveq   #$0a, d4                ; x = 10
        moveq   #$03, d1                ; 4 lines (dbra)
        move.l  ptr_orig_title(pc), a2
        jsr     $130(a2)                ; Flood's native box renderer (text+$28c2)
        movem.l (a7)+, d0-d4/a0-a2
        rts

loading_box_str:
        dc.b    '!"""""""""""""""#',0
        dc.b    '$ LOADING LEVEL %',0
        dc.b    '$  PLEASE WAIT  %',0
        dc.b    '&)))))))))))))))(',0
        even

; --- Draw small "enhanced by dad_prg v1.1" at top-left (x=4, y=4) of Title Screen ($26956) ---
; Uses compact 5x5 pixel bitmap font with 1px black drop-shadow (color 0) + color 15 text.
draw_credit_banner:
        movem.l d0-d7/a0-a4, -(a7)
        move.l  ptr_frontbuf(pc), a0
        move.l  (a0), a3                ; a3 = visible title screen buffer ($26956)
        lea     credit_str(pc), a2
        moveq   #4, d4                  ; x = 4 px
.cb_char:
        moveq   #0, d0
        move.b  (a2)+, d0
        beq.s   .cb_done
        ; Look up glyph index in credit_chars table
        lea     credit_chars(pc), a0
        moveq   #0, d1
.cb_find:
        move.b  (a0)+, d2
        beq.s   .cb_space
        cmp.b   d2, d0
        beq.s   .cb_found
        addq.w  #1, d1
        bra.s   .cb_find
.cb_found:
        ; Glyph is 5 rows x 1 byte (top 5 bits = 5 pixels) at credit_glyphs + d1*5
        move.w  d1, d2
        add.w   d1, d1
        add.w   d1, d1
        add.w   d2, d1                  ; d1 *= 5
        lea     credit_glyphs(pc), a1
        adda.w  d1, a1

        moveq   #0, d5                  ; row = 0..4
.cb_row:
        move.b  (a1)+, d6               ; 5-bit row mask in bits 7..3
        moveq   #0, d7                  ; col = 0..4
.cb_col:
        btst    #7, d6
        beq.s   .cb_next_px
        ; Draw black shadow at (d4+d7+1, 4+d5+1) then color 15 at (d4+d7, 4+d5)
        move.w  d4, d0
        add.w   d7, d0
        addq.w  #1, d0                  ; sx = x + col + 1
        move.w  d5, d1
        addq.w  #5, d1                  ; sy = 4 + row + 1
        bsr.s   .plot_black
        move.w  d4, d0
        add.w   d7, d0                  ; px = x + col
        move.w  d5, d1
        addq.w  #4, d1                  ; py = 4 + row
        bsr.s   .plot_white
.cb_next_px:
        add.b   d6, d6
        addq.w  #1, d7
        cmp.w   #5, d7
        blt.s   .cb_col
        addq.w  #1, d5
        cmp.w   #5, d5
        blt.s   .cb_row
.cb_space:
        addq.w  #6, d4                  ; 5px glyph + 1px gap = 6px advance
        bra.s   .cb_char
.cb_done:
        movem.l (a7)+, d0-d7/a0-a4
        rts

; Plot color 0 (black) at (d0=x, d1=y) on 320x200x4bpp screen a3
.plot_black:
        mulu.w  #160, d1
        move.w  d0, d2
        lsr.w   #4, d2
        lsl.w   #3, d2
        add.w   d2, d1
        lea     (a3, d1.w), a4
        andi.w  #15, d0
        moveq   #15, d2
        sub.w   d0, d2
        moveq   #0, d3
        bset    d2, d3
        not.w   d3
        and.w   d3, (a4)+
        and.w   d3, (a4)+
        and.w   d3, (a4)+
        and.w   d3, (a4)
        rts

; Plot color 15 (all 4 planes set = bright white/silver) at (d0=x, d1=y) on a3
.plot_white:
        mulu.w  #160, d1
        move.w  d0, d2
        lsr.w   #4, d2
        lsl.w   #3, d2
        add.w   d2, d1
        lea     (a3, d1.w), a4
        andi.w  #15, d0
        moveq   #15, d2
        sub.w   d0, d2
        moveq   #0, d3
        bset    d2, d3
        or.w    d3, (a4)+
        or.w    d3, (a4)+
        or.w    d3, (a4)+
        or.w    d3, (a4)
        rts

credit_str:     dc.b    "enhanced by dad_prg v1.1",0
credit_chars:   dc.b    "enhacdbypgrv1.0_",0
        even
; 5x5 bitmap glyphs (MSB = leftmost pixel, bits 7..3)
credit_glyphs:
        dc.b    $70,$88,$f8,$80,$78     ; e
        dc.b    $00,$f0,$88,$88,$88     ; n
        dc.b    $80,$f0,$88,$88,$88     ; h
        dc.b    $00,$78,$88,$88,$78     ; a
        dc.b    $00,$78,$80,$80,$78     ; c
        dc.b    $08,$78,$88,$88,$78     ; d
        dc.b    $80,$f0,$88,$88,$f0     ; b
        dc.b    $88,$88,$78,$08,$70     ; y
        dc.b    $00,$f0,$88,$f0,$80     ; p
        dc.b    $78,$88,$78,$08,$70     ; g
        dc.b    $00,$70,$80,$80,$80     ; r
        dc.b    $00,$88,$88,$50,$20     ; v
        dc.b    $20,$60,$20,$20,$70     ; 1
        dc.b    $00,$00,$00,$00,$20     ; .
        dc.b    $70,$88,$88,$88,$70     ; 0
        dc.b    $00,$00,$00,$00,$f8     ; _
        even

; --- Hook: Gameplay Loop (replaces jsr $12dec) ---
patch_game_hook:
        bsr.w   start_amiga_sfx
        move.l  ptr_orig_game(pc), a0
        jsr     (a0)
        bsr.w   start_amiga_music       ; resume Amiga music for Ending/High-Score!
        rts

; --- Hook: In-Game SFX trigger (replaces entry of sub_01b7be) ---
; Input: d0.w = 1-based ST sound ID
patch_sfx_hook:
        tst.b   am_dma_ready
        bne.s   .do_am_sfx
        ; Plain ST fallback: execute original 6 bytes of sub_01b7be and jump to +6
        movem.l d0-d7/a0-a6, -(a7)
        move.w  #$80, -(a7)
        move.l  ptr_orig_sfx_cont(pc), a0
        jmp     (a0)

.do_am_sfx:
        cmp.b   #2, am_mode
        bne.s   .sfx_ret
        ; Guard: Amiga routing table only covers 1-based SFX IDs 1..61
        tst.w   d0
        ble.s   .sfx_ret
        cmp.w   #62, d0
        bge.s   .sfx_ret
        movem.l d0-d2/a0-a2, -(a7)
        move.w  sr, -(a7)
        ori.w   #$0700, sr
        ; Call Amiga am_play_sfx_id(d0.w) at blob+$0000
        move.w  d0, -(a7)
        move.l  ptr_am_blob(pc), a2
        jsr     (a2)
        addq.l  #2, a7
        move.w  (a7)+, sr
        movem.l (a7)+, d0-d2/a0-a2
.sfx_ret:
        rts

; --- Hook: Clean exit (replaces jsr $1b598) ---
patch_exit_hook:
        ; Disable IKBD joystick reporting ($1a) and re-enable relative mouse ($08) for TOS Desktop
.ikbd_wait_j:
        btst.b  #1, $fffffc00.w
        beq.s   .ikbd_wait_j
        move.b  #$1a, $fffffc02.w
.ikbd_wait_e:
        btst.b  #1, $fffffc00.w
        beq.s   .ikbd_wait_e
        move.b  #$08, $fffffc02.w

        tst.b   am_dma_ready
        beq.s   .no_dma_stop
        clr.b   DMA_CTRL.w
        clr.b   am_dma_ready
.no_dma_stop:
        move.w  orig_rez(pc), d0
        beq.s   .no_rez_restore
        move.w  d0, -(a7)
        move.l  #-1, -(a7)
        move.l  #-1, -(a7)
        move.w  #5, -(a7)
        trap    #14
        lea     12(a7), a7
.no_rez_restore:
        move.l  ptr_orig_exit(pc), a0
        jmp     (a0)

; --- Virtual Paula: update channel d7 (called from Amiga blob +$0aa2) ---
; Inputs: d7.w = channel (0..3), a6 = am_ws ($16720)
;   $0(a6) = volume (0..64), $2(a6) = period, $18(a6) = new instr ($ff = none)
; Must preserve all regs (called inside movem/movem block in blob).
vpaula_update:
        movem.l d0-d3/a0-a2, -(a7)
        move.w  d7, d0
        lsl.w   #5, d0                  ; * 32 (VCH_SIZE)
        lea     vch_table(pc), a1
        adda.w  d0, a1

        ; Volume (clamp 0..64)
        move.w  $0(a6), d0
        cmp.w   #64, d0
        ble.s   .vol_ok
        moveq   #64, d0
.vol_ok:
        tst.w   d0
        bpl.s   .vol_pos
        moveq   #0, d0
.vol_pos:
        move.w  d0, VCH_VOL(a1)

        ; Period -> 16.16 step @ 12,517 Hz: (4,642,439 / period) << 2
        move.w  $2(a6), d1
        cmp.w   #71, d1
        blt.s   .no_per
        move.l  #4642439, d0
        divu.w  d1, d0
        and.l   #$ffff, d0
        lsl.l   #2, d0
        swap    d0
        move.w  d0, VCH_STEP_INT(a1)
        swap    d0
        move.w  d0, VCH_STEP_FRAC(a1)
.no_per:
        ; Check for new instrument trigger ($18(a6) != $ff)
        moveq   #0, d0
        move.b  $18(a6), d0
        cmp.b   #$ff, d0
        beq.s   .vp_done
        move.b  #$ff, $18(a6)

        lsl.w   #4, d0                  ; * 16 bytes per sample descriptor
        move.l  ptr_am_blob(pc), a2
        move.l  $04f8(a2), a0           ; a0 = am_inst_ptr (INSTR.DA+4 or FLDFX.IN+4)
        move.l  (a0, d0.w), d1
        add.l   a0, d1
        move.l  d1, VCH_SAMP_PTR(a1)
        moveq   #0, d2
        move.w  $c(a0, d0.w), d2        ; len in words
        add.l   d2, d2                  ; len in bytes
        move.l  d2, VCH_SAMP_LEN(a1)

        move.l  $4(a0, d0.w), d1
        add.l   a0, d1
        move.l  d1, VCH_LOOP_PTR(a1)
        moveq   #0, d3
        move.w  $e(a0, d0.w), d3        ; loop len in words
        add.l   d3, d3                  ; loop len in bytes
        move.l  d3, VCH_LOOP_LEN(a1)

        clr.w   VCH_POS_INT(a1)
        clr.w   VCH_POS_FRAC(a1)
        cmp.l   #4, d2
        sle.b   d0
        not.b   d0
        move.b  d0, VCH_ACTIVE(a1)
.vp_done:
        movem.l (a7)+, d0-d3/a0-a2
        rts

; --- Virtual Paula: stop channel d7 (0..3) ---
vpaula_stop_ch:
        movem.l d0/a1, -(a7)
        move.w  d7, d0
        lsl.w   #5, d0
        lea     vch_table(pc), a1
        adda.w  d0, a1
        clr.w   VCH_VOL(a1)
        clr.b   VCH_ACTIVE(a1)
        movem.l (a7)+, d0/a1
        rts

; --- Virtual Paula: stop all 4 channels ---
vpaula_stop_all:
        movem.l d0/a1, -(a7)
        lea     vch_table(pc), a1
        moveq   #3, d0
.vsa_lp:
        clr.w   VCH_VOL(a1)
        clr.b   VCH_ACTIVE(a1)
        lea     VCH_SIZE(a1), a1
        dbra    d0, .vsa_lp
        movem.l (a7)+, d0/a1
        rts

; --- Hook: VBL Audio Tick + Cursor-Tracked 12,517 Hz Stereo DMA Ring Mixer ---
; Replaces jsr $1b4fa in VBL IRQ ($0126a4).
; Tracks live STE DMA hardware playback cursor ($ff8909/$0b/$0d) over a 2000-byte
; (8 x 250B) ring buffer, so audio NEVER glitches or drifts at 50 Hz, 60 Hz, or 71 Hz!
patch_vbl_audio:
        tst.b   am_dma_ready
        bne.s   .run_dma_vbl
        move.l  ptr_orig_vbl_mus(pc), a0
        jmp     (a0)

.run_dma_vbl:
        ; Atomically read 24-bit live STE DMA playback cursor (guard HI/MID/LO carry)
.rd_cnt:
        moveq   #0, d0
        move.b  DMA_CNT_HI.w, d0
        move.b  DMA_CNT_MID.w, d1
        move.b  DMA_CNT_LO.w, d2
        cmp.b   DMA_CNT_MID.w, d1
        bne.s   .rd_cnt
        cmp.b   DMA_CNT_HI.w, d0
        bne.s   .rd_cnt
        lsl.l   #8, d0
        move.b  d1, d0
        lsl.l   #8, d0
        move.b  d2, d0

        move.l  dma_ring_ptr(pc), a5
        sub.l   a5, d0                  ; d0 = rd_off (0..1999)
        bmi.s   .rd_clamp0
        cmp.l   #DMA_RING_BYTES, d0
        blt.s   .rd_ok
.rd_clamp0:
        moveq   #0, d0
.rd_ok:
        ; Compute how many 250-byte slots are free behind rd_off (keep 1-slot safety margin)
        move.w  dma_wr_slot(pc), d1
        mulu.w  #250, d1                ; d1 = wr_off (0..1750)
        sub.w   d1, d0                  ; d0 = rd_off - wr_off
        bpl.s   .diff_pos
        addi.w  #DMA_RING_BYTES, d0
.diff_pos:
        ; Fill up to 3 slots (max 750 B) per VBL while d0 >= 250
        moveq   #2, d6                  ; max 3 slots per VBL (dbra)
.slot_lp:
        cmp.w   #250, d0
        blt.s   .vbl_done
        subi.w  #250, d0
        move.w  d0, -(a7)
        move.w  d6, -(a7)

        move.w  dma_wr_slot(pc), d1
        mulu.w  #250, d1
        lea     (a5, d1.w), a4          ; a4 = current 250-byte slot

        tst.b   am_mode
        bne.s   .mix_slot
        ; Silent: clear 250 bytes (62 longs + 1 word)
        move.l  a4, a0
        moveq   #61, d2
.clr_sl:
        clr.l   (a0)+
        dbra    d2, .clr_sl
        clr.w   (a0)
        bra.s   .adv_slot

.mix_slot:
        move.l  a4, -(a7)
        move.l  a5, -(a7)
        bsr.s   run_am_tick
        move.l  4(a7), a4
        bsr.s   mix_125_stereo
        move.l  (a7)+, a5
        addq.l  #4, a7

.adv_slot:
        move.w  dma_wr_slot(pc), d1
        addq.w  #1, d1
        andi.w  #7, d1
        move.w  d1, dma_wr_slot

        move.w  (a7)+, d6
        move.w  (a7)+, d0
        dbra    d6, .slot_lp

.vbl_done:
        rts

; Run 1 tick of Amiga sequencer if $1a(am_ws) != 0
run_am_tick:
        move.l  ptr_am_blob(pc), a0
        lea     $0148(a0), a6           ; a6 = am_ws ($16720)
        tst.b   $1a(a6)
        beq.s   .rat_ret
        sf.b    $1a(a6)
        jsr     $0a66(a0)               ; am_tick_core (saves d0-d7/a0-a5, sets $1a=$ff)
.rat_ret:
        rts

; Mix 125 stereo samples (250 bytes) into a4:
;   Left  (even bytes: a4+0, +2, ...): Ch 0 (replace) + Ch 3 (add)
;   Right (odd  bytes: a4+1, +3, ...): Ch 1 (replace) + Ch 2 (add)
mix_125_stereo:
        ; Left ear: Ch 0 (replace) + Ch 3 (add)
        lea     vch_table(pc), a1       ; Ch 0
        move.l  a4, a3
        bsr.s   mix_ch_replace
        lea     vch_table+3*VCH_SIZE(pc), a1 ; Ch 3
        move.l  a4, a3
        bsr.w   mix_ch_add

        ; Right ear: Ch 1 (replace) + Ch 2 (add)
        lea     vch_table+1*VCH_SIZE(pc), a1 ; Ch 1
        lea     1(a4), a3
        bsr.s   mix_ch_replace
        lea     vch_table+2*VCH_SIZE(pc), a1 ; Ch 2
        lea     1(a4), a3
        bsr.w   mix_ch_add
        rts

; Mix 125 samples from channel a1 into stride-2 buffer a3 (REPLACE)
mix_ch_replace:
        tst.b   VCH_ACTIVE(a1)
        beq.w   .mcr_zero
        move.w  VCH_VOL(a1), d0
        lsr.w   #2, d0                  ; 0..16 -> clamp 0..15
        beq.w   .mcr_zero
        cmp.w   #15, d0
        ble.s   .mcr_vok
        moveq   #15, d0
.mcr_vok:
        lsl.w   #8, d0                  ; * 256
        move.l  vol_tbl_ptr(pc), a2
        adda.w  d0, a2                  ; a2 = vol_tbl[lvl]

        move.l  VCH_SAMP_PTR(a1), a0
        move.w  VCH_POS_FRAC(a1), d0
        move.w  VCH_STEP_FRAC(a1), d1
        move.w  VCH_POS_INT(a1), d2
        move.w  VCH_STEP_INT(a1), d3
        move.l  VCH_SAMP_LEN(a1), d5    ; d5.w = samp_len (< 32KB)
        moveq   #0, d4

        ; Fast path check: if pos_int + 125*(step_int+1) < samp_len, NO bounds check!
        move.w  d3, d6
        addq.w  #1, d6
        mulu.w  #125, d6
        add.w   d2, d6
        bcs.s   .mcr_slow               ; unsigned overflow -> slow
        cmp.w   d5, d6
        bhs.s   .mcr_slow

        ; --- FAST UNROLLED LOOP (5x unrolled x 25 = 125 samples, ZERO bounds checks!) ---
        moveq   #24, d7
.mcr_fast:
        rept    5
        move.b  (a0, d2.w), d4
        move.b  (a2, d4.w), (a3)
        addq.l  #2, a3
        add.w   d1, d0
        addx.w  d3, d2
        endr
        dbra    d7, .mcr_fast

        move.w  d0, VCH_POS_FRAC(a1)
        move.w  d2, VCH_POS_INT(a1)
        rts

.mcr_zero:
        moveq   #24, d7
.mcr_zlp:
        rept    5
        clr.b   (a3)
        addq.l  #2, a3
        endr
        dbra    d7, .mcr_zlp
        rts

.mcr_slow:
        moveq   #124, d7
.mcr_slp:
        cmp.w   d5, d2
        blo.s   .mcr_ok
        ; Handle loop or stop
        move.l  VCH_LOOP_LEN(a1), d6
        cmp.l   #4, d6
        ble.s   .mcr_stop
        sub.w   d5, d2
        move.l  VCH_LOOP_PTR(a1), a0
        move.l  a0, VCH_SAMP_PTR(a1)
        move.l  d6, d5
        move.l  d6, VCH_SAMP_LEN(a1)
        cmp.w   d5, d2
        blo.s   .mcr_ok
        moveq   #0, d2
.mcr_ok:
        move.b  (a0, d2.w), d4
        move.b  (a2, d4.w), (a3)
        addq.l  #2, a3
        add.w   d1, d0
        addx.w  d3, d2
        dbra    d7, .mcr_slp
        move.w  d0, VCH_POS_FRAC(a1)
        move.w  d2, VCH_POS_INT(a1)
        rts

.mcr_stop:
        clr.b   VCH_ACTIVE(a1)
.mcr_rem:
        clr.b   (a3)
        addq.l  #2, a3
        dbra    d7, .mcr_rem
        rts

; Mix 125 samples from channel a1 into stride-2 buffer a3 (ADD)
mix_ch_add:
        tst.b   VCH_ACTIVE(a1)
        beq.w   .mca_ret
        move.w  VCH_VOL(a1), d0
        lsr.w   #2, d0
        beq.w   .mca_ret
        cmp.w   #15, d0
        ble.s   .mca_vok
        moveq   #15, d0
.mca_vok:
        lsl.w   #8, d0
        move.l  vol_tbl_ptr(pc), a2
        adda.w  d0, a2

        move.l  VCH_SAMP_PTR(a1), a0
        move.w  VCH_POS_FRAC(a1), d0
        move.w  VCH_STEP_FRAC(a1), d1
        move.w  VCH_POS_INT(a1), d2
        move.w  VCH_STEP_INT(a1), d3
        move.l  VCH_SAMP_LEN(a1), d5
        moveq   #0, d4

        move.w  d3, d6
        addq.w  #1, d6
        mulu.w  #125, d6
        add.w   d2, d6
        bcs.s   .mca_slow
        cmp.w   d5, d6
        bhs.s   .mca_slow

        ; --- FAST UNROLLED LOOP (5x unrolled x 25 = 125 samples) ---
        moveq   #24, d7
.mca_fast:
        rept    5
        move.b  (a0, d2.w), d4
        move.b  (a2, d4.w), d6
        add.b   d6, (a3)
        addq.l  #2, a3
        add.w   d1, d0
        addx.w  d3, d2
        endr
        dbra    d7, .mca_fast

        move.w  d0, VCH_POS_FRAC(a1)
        move.w  d2, VCH_POS_INT(a1)
.mca_ret:
        rts

.mca_slow:
        moveq   #124, d7
.mca_slp:
        cmp.w   d5, d2
        blo.s   .mca_ok
        move.l  VCH_LOOP_LEN(a1), d6
        cmp.l   #4, d6
        ble.s   .mca_stop
        sub.w   d5, d2
        move.l  VCH_LOOP_PTR(a1), a0
        move.l  a0, VCH_SAMP_PTR(a1)
        move.l  d6, d5
        move.l  d6, VCH_SAMP_LEN(a1)
        cmp.w   d5, d2
        blo.s   .mca_ok
        moveq   #0, d2
.mca_ok:
        move.b  (a0, d2.w), d4
        move.b  (a2, d4.w), d6
        add.b   d6, (a3)
        addq.l  #2, a3
        add.w   d1, d0
        addx.w  d3, d2
        dbra    d7, .mca_slp
        move.w  d0, VCH_POS_FRAC(a1)
        move.w  d2, VCH_POS_INT(a1)
        rts

.mca_stop:
        clr.b   VCH_ACTIVE(a1)
        rts

; ============================================================================
; 8. Zero-Lag IKBD Event-Mode ISR (replaces $0127f0)
;    Works with IKBD $14 (Joystick Event Reporting) so Joy 1 changes ($ff, byte)
;    update $26a68 immediately (~2.5ms) with zero 1-frame ($16) polling lag.
;    Drains ACIA in a loop, resyncs on OVRN, and drains MIDI ACIA if needed.
; ============================================================================
patch_ikbd_isr:
        movem.l d0-d2/a0-a1, -(a7)
        lea     $fffffc00.w, a1
.ikbd_loop:
        move.b  (a1), d2                ; ACIA status
        btst    #0, d2                  ; RDRF (byte ready)?
        beq.w   .ikbd_done
        move.b  2(a1), d0               ; read ACIA data (also clears OVRN)
        btst    #5, d2                  ; OVRN?
        beq.s   .no_ovrn
        clr.b   ikbd_state              ; resync packet state on overrun
.no_ovrn:
        move.b  ikbd_state(pc), d1
        beq.s   .state_idle
        cmp.b   #1, d1
        beq.s   .state_joy1
        cmp.b   #2, d1
        beq.s   .state_skip1
        cmp.b   #3, d1
        beq.s   .state_fd_joy0
        subq.b  #1, d1
        cmp.b   #3, d1
        bgt.s   .save_st
        moveq   #0, d1
.save_st:
        move.b  d1, ikbd_state
        bra.s   .ikbd_loop

.state_joy1:
        move.l  ptr_joy_byte(pc), a0
        move.b  d0, (a0)                ; live Joy 1 state -> $26a68
        clr.b   ikbd_state
        bra.s   .ikbd_loop

.state_skip1:
        clr.b   ikbd_state              ; discard Joy 0 byte
        bra.s   .ikbd_loop

.state_fd_joy0:
        move.b  #1, ikbd_state          ; $fd reply: discard Joy 0, next byte is Joy 1
        bra.s   .ikbd_loop

.state_idle:
        cmp.b   #$f6, d0
        blo.s   .is_key
        cmp.b   #$ff, d0
        beq.s   .hdr_ff                 ; Joy 1 event (1 byte)
        cmp.b   #$fe, d0
        beq.s   .hdr_fe                 ; Joy 0 event (1 byte)
        cmp.b   #$fd, d0
        beq.s   .hdr_fd                 ; Joy interrogate reply (joy0, joy1)
        cmp.b   #$fc, d0
        beq.s   .hdr_fc                 ; Clock (6 bytes)
        cmp.b   #$f7, d0
        beq.s   .hdr_f7                 ; Abs mouse (5 bytes)
        cmp.b   #$f6, d0
        beq.s   .hdr_f6                 ; Status (7 bytes)
        move.b  #5, ikbd_state          ; $f8..$fb rel mouse (2 bytes)
        bra.w   .ikbd_loop
.hdr_ff:
        move.b  #1, ikbd_state
        bra.w   .ikbd_loop
.hdr_fe:
        move.b  #2, ikbd_state
        bra.w   .ikbd_loop
.hdr_fd:
        move.b  #3, ikbd_state
        bra.w   .ikbd_loop
.hdr_fc:
        move.b  #9, ikbd_state
        bra.w   .ikbd_loop
.hdr_f7:
        move.b  #8, ikbd_state
        bra.w   .ikbd_loop
.hdr_f6:
        move.b  #10, ikbd_state
        bra.w   .ikbd_loop

.is_key:
        move.l  ptr_orig_kbd_key(pc), a0
        jsr     (a0)                    ; Flood's keyboard scancode handler ($012844)
        bra.w   .ikbd_loop

.ikbd_done:
        btst    #0, $fffffc04.w         ; drain MIDI ACIA if RDRF set (shared MFP GPIP4)
        beq.s   .no_midi
        tst.b   $fffffc06.w
.no_midi:
        bclr.b  #6, $fffffa11.w         ; clear MFP ISRB bit 6
        movem.l (a7)+, d0-d2/a0-a1
        rte

; ============================================================================
; 9. Staircase Walk-Animation Anti-Aliasing Fix (replaces text+$ae4e = $01d3c4)
;    In original Flood, anim_frame ($1e7ae) keeps ticking modulo 4 every 2 frames
;    (8-frame period) even while falling in dry mid-air when Quiffy's sprite is
;    frozen. Walking down 1-tile-drop, 2-tile-wide stairs also has an exact 8-frame
;    period (6 frames falling + 2 frames on step), aliasing anim_frame back to the
;    same value on every step so Quiffy slides down frozen in one frame!
;    Fix: pause anim_frame while in dry mid-air (surf.b == 0 && water_depth == 0).
; ============================================================================
patch_anim_step:
        move.l  ptr_surf_bits(pc), a0
        tst.b   1(a0)                   ; ($1e7be).b != 0 (touching surface)?
        bne.s   .do_anim_step
        move.l  d0, -(a7)
        move.l  ptr_water_depth(pc), a0
        jsr     (a0)                    ; sub_01a192(d1=px, d2=py) -> d0
        tst.l   d0
        beq.s   .dry_air
        move.l  (a7)+, d0
.do_anim_step:
        move.l  ptr_water_tog(pc), a0
        add.w   (a0), d5
        rts
.dry_air:
        move.l  (a7)+, d0
        rts

; ============================================================================
; Patch Data & State
; ============================================================================
        even
fn_am_mus:      dc.b    "AM_MUS.BIN",0
fn_am_sfx:      dc.b    "AM_SFX.BIN",0
        even
last_frame_vbl: dc.l    0
am_mus_buf:     dc.l    0
am_sfx_buf:     dc.l    0
vol_tbl_ptr:    dc.l    0
dma_ring_ptr:   dc.l    0
bg_cache_ptr:   dc.l    0
bg_cur_a6:      dc.l    0
bg_cur_a5:      dc.l    0
bg_last_a6:     dc.l    0
bg_last_d1:     dc.l    0
bg_last_d6:     dc.w    0
orig_rez:       dc.w    0
dma_wr_slot:    dc.w    0
bg_valid:       dc.b    0
ikbd_state:     dc.b    0
        even
bg_map_copy:    dcb.b   280, 0
vch_table:      dcb.b   4*VCH_SIZE, 0
has_blitter:    dc.b    0
has_dma:        dc.b    0
am_dma_ready:   dc.b    0
am_mode:        dc.b    0               ; 0=silent, 1=music, 2=sfx
        even
