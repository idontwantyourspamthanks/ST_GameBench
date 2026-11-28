; STE Tier 2 Hardware Scrolling + 143-Tile Blitter Diff + Dirty-Rect Restore + Ticker Split
; Memory map in free 1 MB STE RAM ($084000-$0abfff = 160 KB):
;   $084000-$085fff ( 8 KB): GODSPAT.BIN (code + state + dirty stacks)
;   $086000-$08f9ff (39 KB): BUF0 (176 B/line * 224 lines = $9a00)
;   $090000-$0999ff (39 KB): BUF1 (176 B/line * 224 lines = $9a00)
;   $09a000-$09bfff ( 8 KB): DRAWN_MAP0 (128 * 64 tile IDs for BUF0)
;   $09c000-$09dfff ( 8 KB): DRAWN_MAP1 (128 * 64 tile IDs for BUF1)
;   $09e000-$0a0fff (12 KB): SAVE_BUF0 (dirty-rect background save pool for BUF0)
;   $0a1000-$0a3fff (12 KB): SAVE_BUF1 (dirty-rect background save pool for BUF1)
;   $0a4000-$0abfff (32 KB): Sprite mask LUT + pool (defined in ste_sprites.s)

HW_STRIDE       equ     176             ; 352 px = 22 words/plane = 11 tiles wide
HW_LINES        equ     224             ; 16 slack top + 192 visible + 16 slack bottom
HW_BUF_SIZE     equ     HW_STRIDE*HW_LINES ; 39424 ($9a00)
HW_ZERO_OFF     equ     16*HW_STRIDE    ; 2816 ($0b00)

BUF0_BASE       equ     $086000
BUF1_BASE       equ     $090000
DMAP0_BASE      equ     $09a000
DMAP1_BASE      equ     $09c000
SBUF0_BASE      equ     $09e000
SBUF1_BASE      equ     $0a1000
SBUF_SIZE       equ     $3000           ; 12 KB per buffer

DIRTY_MAX       equ     64              ; max dirty rects per buffer (12 bytes each = 768 B)

; --- Hardware-scroll state ---
hw_scroll_want:   dc.w  0               ; 1 if current back buffer uses STE HW scroll
hw_scroll_front:  dc.w  0               ; 1 if currently displayed front buffer uses STE HW scroll
back_buf_idx:     dc.w  0               ; 0 or 1
back_disp_addr:   dc.l  BUF0_BASE+HW_ZERO_OFF
back_fine_x:      dc.w  0
front_disp_addr:  dc.l  BUF0_BASE+HW_ZERO_OFF
front_fine_x:     dc.w  0

; Per-buffer state (indexed by b*4 or b*2)
buf_bases:        dc.l  BUF0_BASE,BUF1_BASE
dmap_bases:       dc.l  DMAP0_BASE,DMAP1_BASE
sbuf_bases:       dc.l  SBUF0_BASE,SBUF1_BASE
dstack_bases:     dc.l  dirty_stack0,dirty_stack1

buf_valid:        dc.w  0,0
buf_org_wx:       dc.w  0,0
buf_org_y:        dc.w  0,0
buf_map_ptr:      dc.l  0,0
buf_tiles_ptr:    dc.l  0,0
dirty_cnt:        dc.w  0,0
save_ptr:         dc.l  SBUF0_BASE,SBUF1_BASE

; ---------------------------------------------------------------------------
; ste_save_bg: Save a screen rectangle before sprite/HUD draw (for LIFO restore)
; Inputs: a1 = dst word-aligned addr in buf[b], d6.w = x_clusters (1..10), d7.w = y_lines (1..192)
; Preserves: all registers!
; ---------------------------------------------------------------------------
ste_save_bg:
        tst.w   spr_save_enable
        beq.w   .ret
        movem.l d0-d5/a0-a3,-(a7)
        move.w  back_buf_idx(pc),d0
        move.w  d0,d1
        add.w   d1,d1                   ; b*2
        lea     dirty_cnt(pc),a0
        move.w  (a0,d1.w),d2
        cmpi.w  #DIRTY_MAX,d2
        bge.w   .skip                   ; stack full
        add.w   d1,d1                   ; b*4
        lea     save_ptr(pc),a2
        move.l  (a2,d1.w),d3            ; current save pool ptr
        ; Compute bytes needed = x_clusters * 8 * y_lines
        move.w  d6,d4
        lsl.w   #2,d4                   ; x_words = x_clusters * 4
        move.w  d4,d5
        add.w   d5,d5                   ; bytes/row = x_clusters * 8
        mulu.w  d7,d5                   ; total bytes
        move.l  d3,d0
        add.l   d5,d0
        lea     sbuf_bases(pc),a3
        move.l  (a3,d1.w),d5
        addi.l  #SBUF_SIZE,d5
        cmp.l   d5,d0
        bhi.w   .skip                   ; save pool full

        ; Advance save_ptr and record entry on dirty_stack[b]
        move.l  d0,(a2,d1.w)
        lea     dirty_cnt(pc),a0
        move.w  back_buf_idx(pc),d5
        add.w   d5,d5
        addq.w  #1,(a0,d5.w)

        lea     dstack_bases(pc),a3
        movea.l (a3,d1.w),a3
        mulu.w  #12,d2
        adda.w  d2,a3
        move.l  a1,(a3)+                ; +0: dst_addr in buf[b]
        move.l  d3,(a3)+                ; +4: save_ptr
        move.w  d4,(a3)+                ; +8: x_words
        move.w  d7,(a3)+                ; +10: y_lines

        ; Blit buf[b] -> save_buf[b] (1 single Blitter call, all 4 planes interleaved!)
        move.w  #2,BLT_SXINC.w
        move.w  #HW_STRIDE+2,d5
        move.w  d4,d0
        add.w   d0,d0
        sub.w   d0,d5                   ; SRC_Y_INC = 176 - (x_words*2) + 2
        move.w  d5,BLT_SYINC.w
        move.l  a1,BLT_SADDR.w
        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.w  #2,BLT_DXINC.w
        move.w  #2,BLT_DYINC.w
        move.l  d3,BLT_DADDR.w
        move.w  d4,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.b  #0,BLT_SKEW.w
        bsr.w   blt_go_nh
.skip:
        movem.l (a7)+,d0-d5/a0-a3
.ret:
        rts

; ---------------------------------------------------------------------------
; ste_restore_dirty: Restore all dirty rects in back buffer b (LIFO order)
; Input: d0.w = b (0 or 1). Clobbers: d1-d5,a0-a3
; ---------------------------------------------------------------------------
ste_restore_dirty:
        move.w  d0,d1
        add.w   d1,d1                   ; b*2
        lea     dirty_cnt(pc),a0
        move.w  (a0,d1.w),d2
        beq.w   .rd_reset
        clr.w   (a0,d1.w)
        add.w   d1,d1                   ; b*4
        lea     dstack_bases(pc),a3
        movea.l (a3,d1.w),a3
        move.w  d2,d3
        mulu.w  #12,d3
        adda.w  d3,a3                   ; point past last entry (LIFO!)

        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.w  #2,BLT_SXINC.w
        move.w  #2,BLT_SYINC.w
        move.w  #2,BLT_DXINC.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.b  #0,BLT_SKEW.w

        subq.w  #1,d2
.rd_lp:
        lea     -12(a3),a3
        move.l  (a3),BLT_DADDR.w        ; dst_addr in buf[b]
        move.l  4(a3),BLT_SADDR.w       ; save_ptr
        move.w  8(a3),d4                ; x_words
        move.w  10(a3),d5               ; y_lines
        move.w  #HW_STRIDE+2,d3
        sub.w   d4,d3
        sub.w   d4,d3                   ; DST_Y_INC = 176 - x_words*2 + 2
        move.w  d3,BLT_DYINC.w
        move.w  d4,BLT_XCNT.w
        move.w  d5,BLT_YCNT.w
        bsr.w   blt_go_nh
        dbra    d2,.rd_lp

.rd_reset:
        move.w  d0,d1
        lsl.w   #2,d1
        lea     sbuf_bases(pc),a2
        lea     save_ptr(pc),a3
        move.l  (a2,d1.w),(a3,d1.w)
        rts

; ---------------------------------------------------------------------------
; $18036 replacement: STE Hardware-Scroll Tilemap Diff Renderer
; ---------------------------------------------------------------------------
ste_tile_draw:
        ; Fall back to stock renderer on world transitions ($4fa >= 2) or boss rooms ($3b8 != 0)
        cmpi.w  #2,$4fa.w
        bge.s   .td_fallback
        tst.w   $3b8.w
        bne.s   .td_fallback
        bra.s   .td_ste

.td_fallback:
        clr.w   hw_scroll_want
        clr.l   spr_scr_base
        move.w  #160,spr_stride
        clr.w   spr_fine_x
        clr.w   spr_save_enable
        ; Execute displaced instruction at $18036: cmpi.w #2,$4fa.w
        cmpi.w  #2,$4fa.w
        jmp     $01803c

.td_ste:
        movem.l d0-d7/a0-a6,-(a7)

        ; Select back buffer index b = 0 if $110a.w == $078300 else 1
        moveq   #0,d0
        cmpi.l  #$078300,$110a.w
        beq.s   .got_b
        moveq   #1,d0
.got_b:
        move.w  d0,back_buf_idx

        ; 1. Restore all dirty rects from previous frame on buffer b
        bsr.w   ste_restore_dirty

        ; 2. Compute camera coords (use interpolated camera when active!)
        move.w  back_buf_idx(pc),d0
        move.w  d0,d1
        add.w   d1,d1                   ; d1 = b*2
        move.w  d1,d2
        add.w   d2,d2                   ; d2 = b*4

        tst.w   use_interp_cam
        bne.s   .use_ic
        move.w  $4d6.w,d3               ; cam_x
        move.w  $4d8.w,d4               ; cam_y
        bra.s   .got_cam
.use_ic:
        move.w  render_cam_x(pc),d3
        move.w  render_cam_y(pc),d4
.got_cam:
        move.w  d3,cur_td_x
        move.w  d4,cur_td_y
        move.w  d3,d5
        asr.w   #4,d5                   ; wx = cam_x >> 4
        andi.w  #15,d3                  ; fine_x = cam_x & 15
        move.w  d3,back_fine_x

        ; Check valid + same map_ptr + same tiles_ptr
        lea     buf_valid(pc),a0
        tst.w   (a0,d1.w)
        beq.s   .recenter
        lea     buf_map_ptr(pc),a0
        move.l  $e30.w,d6
        cmp.l   (a0,d2.w),d6
        bne.s   .recenter
        lea     buf_tiles_ptr(pc),a0
        move.l  $f1a.w,d6
        cmp.l   (a0,d2.w),d6
        bne.s   .recenter

        ; Compute disp_off = HW_ZERO_OFF + (wx - org_wx)*8 + (cam_y - org_y)*176
        lea     buf_org_wx(pc),a0
        move.w  d5,d6
        sub.w   (a0,d1.w),d6            ; delta_wx
        asl.w   #3,d6                   ; * 8 bytes
        lea     buf_org_y(pc),a0
        move.w  d4,d7
        sub.w   (a0,d1.w),d7            ; delta_y
        muls.w  #HW_STRIDE,d7           ; * 176 bytes
        ext.l   d6
        add.l   d7,d6
        addi.l  #HW_ZERO_OFF,d6         ; d6 = disp_off

        ; Bounds check: must keep [disp_off, disp_off + 200*176) inside [176, 223*176)
        cmpi.l  #HW_STRIDE,d6
        blt.s   .recenter
        cmpi.l  #(HW_LINES-200-1)*HW_STRIDE,d6
        bgt.s   .recenter
        bra.w   .off_ok

.recenter:
        lea     buf_valid(pc),a0
        move.w  #1,(a0,d1.w)
        lea     buf_org_wx(pc),a0
        move.w  d5,(a0,d1.w)            ; org_wx = wx
        lea     buf_org_y(pc),a0
        move.w  d4,(a0,d1.w)            ; org_y = cam_y
        lea     buf_map_ptr(pc),a0
        move.l  $e30.w,(a0,d2.w)
        lea     buf_tiles_ptr(pc),a0
        move.l  $f1a.w,(a0,d2.w)

        ; Clear DRAWN_MAP[b] (8192 bytes = 4096 words) to $ffff with Blitter fill!
        lea     dmap_bases(pc),a0
        move.l  (a0,d2.w),BLT_DADDR.w
        move.w  #2,BLT_DXINC.w
        move.w  #2,BLT_DYINC.w
        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.w  #4096,BLT_XCNT.w
        move.w  #1,BLT_YCNT.w
        move.b  #0,BLT_HOP.w            ; all 1s
        move.b  #15,BLT_OP.w            ; fill $ffff
        move.b  #0,BLT_SKEW.w
        bsr.w   blt_go_nh

        move.l  #HW_ZERO_OFF,d6         ; disp_off = HW_ZERO_OFF

.off_ok:
        ; Save back_disp_addr = buf_bases[b] + disp_off
        lea     buf_bases(pc),a0
        movea.l (a0,d2.w),a6            ; a6 = buf_base[b]
        lea     (a6,d6.l),a5
        move.l  a5,back_disp_addr

        ; 3. Unified 11x13 visible tile diff loop!
        ; Setup constant Blitter regs for 32x16 4-plane tile copy (XCNT=8 words)
        move.w  #2,BLT_SXINC.w
        move.w  #2,BLT_SYINC.w
        move.w  #2,BLT_DXINC.w
        move.w  #HW_STRIDE-14,BLT_DYINC.w ; 176 - 14 = 162
        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.b  #0,BLT_SKEW.w

        ; tx0 = cur_td_x >> 5, ty0 = cur_td_y >> 4
        move.w  cur_td_x(pc),d0
        asr.w   #5,d0                   ; d0 = tx0
        move.w  cur_td_y(pc),d1
        asr.w   #4,d1                   ; d1 = ty0

        ; Base map & dmap row pointers for (tx0, ty0): offset = ty0*128 + tx0
        move.w  d1,d3
        asl.w   #7,d3
        add.w   d0,d3
        movea.l $e30.w,a0
        adda.w  d3,a0                   ; a0 = &map[ty0][tx0]
        lea     dmap_bases(pc),a1
        movea.l (a1,d2.w),a1
        adda.w  d3,a1                   ; a1 = &dmap[ty0][tx0]

        ; Compute initial tile screen offset in buf[b] for (tx0, ty0):
        ; off0 = HW_ZERO_OFF + (tx0*2 - org_wx)*8 + (ty0*16 - org_y)*176
        move.w  back_buf_idx(pc),d2
        add.w   d2,d2                   ; b*2
        move.w  d0,d3
        add.w   d3,d3                   ; tx0*2
        lea     buf_org_wx(pc),a2
        sub.w   (a2,d2.w),d3            ; tx0*2 - org_wx
        asl.w   #3,d3                   ; * 8
        ext.l   d3
        move.w  d1,d4
        asl.w   #4,d4                   ; ty0*16
        lea     buf_org_y(pc),a2
        sub.w   (a2,d2.w),d4            ; ty0*16 - org_y
        muls.w  #HW_STRIDE,d4           ; * 176
        add.l   d4,d3
        addi.l  #HW_ZERO_OFF,d3         ; d3.l = byte offset of (tx0,ty0) in buf[b]

        movea.l $f1a.w,a3               ; a3 = tiles base (shift 0 = +0, stride = 1408)
        moveq   #12,d7                  ; 13 rows (0..12)

.row_lp:
        cmpi.w  #64,d1                  ; ty >= 64?
        bge.w   .tiles_done
        movem.l d0/d3/a0-a1,-(a7)
        moveq   #10,d6                  ; 11 cols (0..10)
.col_lp:
        cmpi.w  #128,d0                 ; tx >= 128?
        bge.s   .row_next
        move.b  (a0)+,d2                ; map tile ID
        cmp.b   (a1)+,d2                ; already drawn in buf[b]?
        beq.s   .col_skip
        ; Check if tile lies completely inside [0, HW_BUF_SIZE - 15*176 - 16]
        tst.l   d3
        bmi.s   .col_skip
        cmpi.l  #HW_BUF_SIZE-(16*HW_STRIDE),d3
        bgt.s   .col_skip

        move.b  d2,-1(a1)               ; mark drawn!
        ; src = tiles_base + tile_id * 1408 ((id<<7)+(id<<8)+(id<<10))
        andi.l  #$ff,d2
        asl.l   #7,d2                   ; *128
        movea.l a3,a4
        adda.l  d2,a4
        add.l   d2,d2                   ; *256
        adda.l  d2,a4
        asl.l   #2,d2                   ; *1024
        adda.l  d2,a4
        lea     (a6,d3.l),a5            ; dst = buf_base[b] + off

        move.l  a4,BLT_SADDR.w
        move.l  a5,BLT_DADDR.w
        move.w  #8,BLT_XCNT.w
        move.w  #16,BLT_YCNT.w
        bsr.w   blt_go_nh

.col_skip:
        addi.l  #16,d3                  ; next tile column (+32px = +16 bytes)
        addq.w  #1,d0
        dbra    d6,.col_lp

.row_next:
        movem.l (a7)+,d0/d3/a0-a1
        adda.w  #128,a0                 ; next map row
        adda.w  #128,a1                 ; next dmap row
        addi.l  #16*HW_STRIDE,d3        ; next tile row (+16*176 = +2816 bytes)
        addq.w  #1,d1
        dbra    d7,.row_lp

.tiles_done:
        ; 4. Enable STE HW scroll & dirty-rect sprite saving for this frame!
        move.w  #1,hw_scroll_want
        move.l  back_disp_addr(pc),spr_scr_base
        move.w  #HW_STRIDE,spr_stride
        move.w  back_fine_x(pc),spr_fine_x
        move.w  #1,spr_save_enable

        movem.l (a7)+,d0-d7/a0-a6
        rts

; ---------------------------------------------------------------------------
; $00331c hook: Run original $3cc6 (lives HUD), then blit HUD boxes from
; $110a.w (160B stride) -> back_disp_addr (176B stride) with SKEW = back_fine_x
; ---------------------------------------------------------------------------
ste_hud_hook:
        jsr     $003cc6                 ; draw lives icons to $110a.w
        tst.w   hw_scroll_want
        beq.w   .hud_ret
        movem.l d0-d7/a0-a6,-(a7)

        ; 1. Top-left Lives icons: (0, 0), width = min($3a2.w, 10) clusters, height = 16
        move.w  $3a2.w,d6
        ble.s   .no_lives
        cmpi.w  #10,d6
        ble.s   .lv_ok
        moveq   #10,d6
.lv_ok:
        moveq   #0,d0                   ; x = 0
        moveq   #0,d1                   ; y = 0
        moveq   #16,d7                  ; h = 16
        bsr.w   ste_copy_hud_rect
.no_lives:
        ; 2. Bottom-left Energy Potion Jar: (16, 160), 24px wide (1.5 clusters), height = 24
        moveq   #16,d0
        move.w  #160,d1
        moveq   #2,d6
        moveq   #24,d7
        bsr.s   ste_copy_hud_jar

        ; 3. Bottom-right Score Box: (224, 168), 5 clusters (80px), height = 15
        move.w  #224,d0
        move.w  #168,d1
        moveq   #5,d6
        moveq   #15,d7
        bsr.w   ste_copy_hud_rect

        ; 4. Optional status bar ($43e.w >= 0): (160, 152), 4 clusters, height = 24
        tst.w   $43e.w
        bmi.s   .hud_ticker
        move.w  #160,d0
        move.w  #152,d1
        moveq   #4,d6
        moveq   #24,d7
        bsr.w   ste_copy_hud_rect

.hud_ticker:
        ; 5. Bottom 8-line green ticker bar: (0, 192), 20 clusters (320px), height = 8
        ; Blitted directly into buf[b] at line 192 with SKEW = back_fine_x so Timer B
        ; never touches $ff8205/$07/$09/$65/$0f mid-screen -> 0% Shifter plane desync!
        moveq   #0,d0
        move.w  #192,d1
        moveq   #20,d6
        moveq   #8,d7
        bsr.w   ste_copy_hud_rect

.hud_done:
        movem.l (a7)+,d0-d7/a0-a6
.hud_ret:
        rts

; ---------------------------------------------------------------------------
; ste_copy_hud_jar: Copy 24px-wide Energy Potion Jar (preserving right 8px!)
; Inputs: d0.w = 16, d1.w = 160, d6.w = 2, d7.w = 24
; ---------------------------------------------------------------------------
ste_copy_hud_jar:
        movea.l $110a.w,a0
        adda.w  #160*160+8,a0
        movea.l back_disp_addr(pc),a1
        adda.w  #160*HW_STRIDE+8,a1
        move.w  back_fine_x(pc),d5
        bne.s   .jar_skewed

        ; Aligned (fine_x == 0): 2 clusters, ENDMASK1=$ffff, ENDMASK3=$ff00 (24px exact!)
        bsr.w   ste_save_bg
        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ff00,BLT_EM3.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.b  #0,BLT_SKEW.w
        move.w  #8,BLT_SXINC.w
        move.w  #160-8,BLT_SYINC.w
        move.w  #8,BLT_DXINC.w
        move.w  #HW_STRIDE-8,BLT_DYINC.w
        moveq   #3,d0
.jar_pl0:
        move.l  a0,BLT_SADDR.w
        move.l  a1,BLT_DADDR.w
        move.w  #2,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        bsr.w   blt_go_nh
        addq.l  #2,a0
        addq.l  #2,a1
        dbra    d0,.jar_pl0
        rts

.jar_skewed:
        ; Skewed 24px (fine_x = 1..15): 2 clusters if fine_x <= 8, 3 clusters if fine_x > 8
        move.l  #$ffffff00,d0
        lsr.l   d5,d0                   ; 32-bit mask shifted right by fine_x
        cmpi.w  #8,d5
        bgt.s   .jar_3c
        ; Fits in 2 clusters!
        bsr.w   ste_save_bg
        move.w  d0,BLT_EM3.w
        swap    d0
        move.w  d0,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.b  d5,BLT_SKEW.w           ; 2 src words -> 2 dst words (no NFSR)
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.w  #8,BLT_SXINC.w
        move.w  #160-8,BLT_SYINC.w
        move.w  #8,BLT_DXINC.w
        move.w  #HW_STRIDE-8,BLT_DYINC.w
        moveq   #3,d0
.jar_pl2:
        move.l  a0,BLT_SADDR.w
        move.l  a1,BLT_DADDR.w
        move.w  #2,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        bsr.w   blt_go_nh
        addq.l  #2,a0
        addq.l  #2,a1
        dbra    d0,.jar_pl2
        rts

.jar_3c:
        ; Spans 3 clusters (fine_x = 9..15): EM1 = $ffff>>d5, EM2 = $ffff, EM3 = ~($ffff>>(d5-8))
        moveq   #3,d6
        bsr.w   ste_save_bg
        moveq   #-1,d0
        lsr.w   d5,d0
        move.w  d0,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  d5,d1
        subq.w  #8,d1
        moveq   #-1,d0
        lsr.w   d1,d0
        not.w   d0
        move.w  d0,BLT_EM3.w
        move.w  d5,d0
        ori.b   #$40,d0                 ; NFSR | fine_x
        move.b  d0,BLT_SKEW.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.w  #8,BLT_SXINC.w
        move.w  #160-8,BLT_SYINC.w
        move.w  #8,BLT_DXINC.w
        move.w  #HW_STRIDE-16,BLT_DYINC.w
        moveq   #3,d0
.jar_pl3:
        move.l  a0,BLT_SADDR.w
        move.l  a1,BLT_DADDR.w
        move.w  #3,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        bsr.w   blt_go_nh
        addq.l  #2,a0
        addq.l  #2,a1
        dbra    d0,.jar_pl3
        rts

; ---------------------------------------------------------------------------
; ste_copy_hud_rect: Copy aligned HUD box from $110a.w (160B stride) to
; back_disp_addr (176B stride) shifted right by back_fine_x, with dirty-rect save!
; Inputs: d0.w = x (multiple of 16), d1.w = y, d6.w = clusters (1..10), d7.w = h
; ---------------------------------------------------------------------------
ste_copy_hud_rect:
        ; src = $110a.w + y*160 + (x>>4)*8
        movea.l $110a.w,a0
        move.w  d1,d2
        mulu.w  #160,d2
        adda.l  d2,a0
        move.w  d0,d2
        asr.w   #1,d2
        adda.w  d2,a0

        ; dst = back_disp_addr + y*176 + (x>>4)*8
        movea.l back_disp_addr(pc),a1
        move.w  d1,d3
        mulu.w  #HW_STRIDE,d3
        adda.l  d3,a1
        adda.w  d2,a1

        move.w  back_fine_x(pc),d5
        bne.s   .hud_skewed

        ; Aligned HUD copy (fine_x == 0): save + 1 single interleaved Blitter call!
        bsr.w   ste_save_bg
        move.w  d6,d4
        lsl.w   #2,d4                   ; x_words = clusters * 4
        move.w  #2,BLT_SXINC.w
        move.w  #162,d2
        sub.w   d4,d2
        sub.w   d4,d2
        move.w  d2,BLT_SYINC.w
        move.w  #2,BLT_DXINC.w
        move.w  #HW_STRIDE+2,d2
        sub.w   d4,d2
        sub.w   d4,d2
        move.w  d2,BLT_DYINC.w
        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.l  a0,BLT_SADDR.w
        move.l  a1,BLT_DADDR.w
        move.w  d4,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.b  #0,BLT_SKEW.w
        bsr.w   blt_go_nh
        rts

.hud_skewed:
        ; Skewed HUD copy (fine_x = 1..15): save (clusters+1) clusters, blit 4 planes with NFSR!
        addq.w  #1,d6                   ; dest clusters = clusters + 1
        bsr.w   ste_save_bg
        ; Blit 4 planes with OP=3, SKEW = fine_x | $40 (NFSR)
        moveq   #-1,d0
        lsr.w   d5,d0
        move.w  d0,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        not.w   d0
        move.w  d0,BLT_EM3.w
        move.w  d5,d0
        ori.b   #$40,d0
        move.b  d0,BLT_SKEW.w
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.w  #8,BLT_SXINC.w
        ; src_clusters = d6 - 1; NFSR reads (d6-1) words -> (d6-2)*8 + SYINC = 160
        move.w  d6,d2
        subq.w  #2,d2
        asl.w   #3,d2
        move.w  #160,d3
        sub.w   d2,d3
        move.w  d3,BLT_SYINC.w
        move.w  #8,BLT_DXINC.w
        move.w  d6,d2
        subq.w  #1,d2
        asl.w   #3,d2
        move.w  #HW_STRIDE,d3
        sub.w   d2,d3
        move.w  d3,BLT_DYINC.w

        moveq   #3,d0
.hud_pl:
        move.l  a0,BLT_SADDR.w
        move.l  a1,BLT_DADDR.w
        move.w  d6,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        bsr.w   blt_go_nh
        addq.l  #2,a0
        addq.l  #2,a1
        dbra    d0,.hud_pl
        rts

; ---------------------------------------------------------------------------
; $01ecba hook: Frame Flip (replaces $1ecba..$1ecd9)
; Called at SR=$2500 with d0-d1 saved on stack.
; ---------------------------------------------------------------------------
ste_flip:
        move.l  $110e.w,d0
        move.l  $110a.w,d1
        move.l  d0,$110a.w
        move.l  d1,$110e.w

        tst.w   hw_scroll_want
        beq.s   .flip_normal

        move.w  #1,hw_scroll_front
        move.l  back_disp_addr(pc),d1
        move.l  d1,front_disp_addr
        move.w  back_fine_x(pc),front_fine_x

        ; Write STE 24-bit video base in HI -> MID -> LO order!
        ; (Writing HI or MID resets LO to 0 on real STE hardware!)
        move.l  d1,d0
        swap    d0
        move.b  d0,$ffff8201.w          ; VBASE_HI
        move.l  d1,d0
        lsr.w   #8,d0
        move.b  d0,$ffff8203.w          ; VBASE_MID
        move.b  d1,$ffff820d.w          ; VBASE_LO (MUST BE LAST!)
        bra.s   .flip_reset_back

.flip_normal:
        clr.w   hw_scroll_front
        lsr.l   #8,d1
        move.b  d1,$ffff8203.w
        lsr.l   #8,d1
        move.b  d1,$ffff8201.w
        clr.b   $ffff820d.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w

.flip_reset_back:
        ; Reset per-frame back-buffer flags (re-armed by ste_tile_draw next frame if in gameplay)
        clr.w   hw_scroll_want
        clr.l   spr_scr_base
        move.w  #160,spr_stride
        clr.w   spr_fine_x
        clr.w   spr_save_enable
        rts

; ---------------------------------------------------------------------------
; $0171b4 hook: VBL top-of-frame STE Shifter programming (LINEWID + HSCROLL + VBASE)
; ---------------------------------------------------------------------------
ste_vbl_hook:
        tst.w   hw_scroll_front
        beq.s   .vbl_norm
        move.l  front_disp_addr(pc),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8201.w          ; HI
        move.l  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8203.w          ; MID
        move.b  d0,$ffff820d.w          ; LO (LAST!)
        move.w  front_fine_x(pc),d0
        move.b  d0,$ffff8265.w          ; HSCROLL (0..15)
        beq.s   .vbl_lw8
        move.b  #4,$ffff820f.w          ; LINEWID = 4 words (176 - 168)/2
        bra.s   .vbl_orig
.vbl_lw8:
        move.b  #8,$ffff820f.w          ; LINEWID = 8 words (176 - 160)/2
        bra.s   .vbl_orig
.vbl_norm:
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
.vbl_orig:
        ; Execute displaced instructions at $0171b4: tst.w $470.w; bne.s $171c0
        tst.w   $470.w
        bne.s   .vbl_skip_clr
        jmp     $0171ba
.vbl_skip_clr:
        jmp     $0171c0

; ---------------------------------------------------------------------------
; $00538c hook: Timer B at scanline 191 — set green PAL4 FIRST, then switch
; Shifter to static bottom ticker!
; ---------------------------------------------------------------------------
ste_tb191:
        move.w  $5374.w,$ffff8248.w     ; set green PAL4 IMMEDIATELY (zero red flash!)
        tst.w   hw_scroll_front
        beq.s   .tb_done
        movem.l d0-d1,-(a7)
        move.l  $110e.w,d0
        addi.l  #$7800,d0               ; static ticker at line 192 of front buffer ($110e)
        clr.b   $ffff8265.w             ; HSCROLL = 0
        clr.b   $ffff820f.w             ; LINEWID = 0 (160B stride)
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8205.w          ; VCOUNT_HI
        move.l  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8207.w          ; VCOUNT_MID
        move.b  d0,$ffff8209.w          ; VCOUNT_LO (LAST!)
        movem.l (a7)+,d0-d1
.tb_done:
        jmp     $005394

; ---------------------------------------------------------------------------
; $0030f0 hook: Exact 16.67 Hz World Tick + Locked 25.0 fps Smooth Scrolling!
; Exact monotonic 3-frame cycle (2 sim ticks per 3 rendered frames = 16.67 Hz):
;   Phase 0 (t=0.00): Run Sim (C0->C1). Draw at C0 (spr_off = 0). Save prev = C0.
;   Phase 1 (t=0.67): Run Sim (C1->C2). Draw at C0 + 2/3*(C1-C0) (spr_off = C1-render),
;                     record sprites at C1. Save prev = C1.
;   Phase 2 (t=1.33): SKIP Sim! Draw at C1 + 1/3*(C2-C1) (spr_off = C1-render),
;                     replay Phase 1 sprites + HUD, flip!
;   Next Phase 0 (t=2.00): Run Sim (C2->C3). Draw at C2.
; Monotonic example (dx=4): 0 -> 2 -> 5 -> 8 -> 10 -> 13 -> 16 (zero backwards steps!)
; ---------------------------------------------------------------------------
interp_phase:   dc.w    0
use_interp_cam: dc.w    0
sim_prev_x:     dc.w    0
sim_prev_y:     dc.w    0
render_cam_x:   dc.w    0
render_cam_y:   dc.w    0
cur_td_x:       dc.w    0
cur_td_y:       dc.w    0

ste_loop_hook:
        tst.w   hw_scroll_front
        beq.w   .lh_nosim_reset
        tst.w   $3b8.w
        bne.w   .lh_nosim_reset
        cmpi.w  #2,$4fa.w
        bge.w   .lh_nosim_reset
        tst.w   $394.w
        ble.w   .lh_nosim_reset

        move.w  interp_phase(pc),d0
        beq.s   .lh_phase0
        cmpi.w  #1,d0
        beq.s   .lh_phase1
        bra.w   .lh_phase2

.lh_phase0:
        ; --- Phase 0 (t=0.00): Run Sim, draw at exact $4d6/$4d8, save prev = $4d6/$4d8 ---
        move.w  $4d6.w,sim_prev_x
        move.w  $4d8.w,sim_prev_y
        clr.w   use_interp_cam
        clr.w   spr_off_x
        clr.w   spr_off_y
        clr.w   spr_rec_enable
        move.w  #1,interp_phase
        jsr     $0174f6
        jmp     $0030f6

.lh_phase1:
        ; --- Phase 1 (t=0.67): Run Sim, draw at prev + 2/3*(curr - prev), record sprites ---
        movem.l d0-d3,-(a7)
        move.w  $4d6.w,d1               ; curr_x = C1
        move.w  $4d8.w,d2               ; curr_y
        move.w  d1,d3
        sub.w   sim_prev_x(pc),d3       ; dx = C1 - C0
        cmpi.w  #32,d3
        bgt.s   .lh1_snap
        cmpi.w  #-32,d3
        blt.s   .lh1_snap
        move.w  d2,d0
        sub.w   sim_prev_y(pc),d0       ; dy = C1y - C0y
        cmpi.w  #32,d0
        bgt.s   .lh1_snap
        cmpi.w  #-32,d0
        blt.s   .lh1_snap

        ; render = prev + (delta * 2) / 3
        add.w   d3,d3
        ext.l   d3
        divs.w  #3,d3
        add.w   sim_prev_x(pc),d3
        add.w   d0,d0
        ext.l   d0
        divs.w  #3,d0
        add.w   sim_prev_y(pc),d0
        bra.s   .lh1_set
.lh1_snap:
        move.w  d1,d3
        move.w  d2,d0
.lh1_set:
        move.w  d3,render_cam_x
        move.w  d0,render_cam_y
        ; spr_off = C1 - render_cam (keeps sprites locked to world bricks!)
        move.w  d1,d3
        sub.w   render_cam_x(pc),d3
        move.w  d3,spr_off_x
        move.w  d2,d0
        sub.w   render_cam_y(pc),d0
        move.w  d0,spr_off_y

        ; Save prev = C1 for Phase 2!
        move.w  d1,sim_prev_x
        move.w  d2,sim_prev_y
        move.w  #1,use_interp_cam
        clr.w   spr_rec_cnt
        move.w  #1,spr_rec_enable
        move.w  #2,interp_phase
        movem.l (a7)+,d0-d3
        jsr     $0174f6
        jmp     $0030f6

.lh_phase2:
        ; --- Phase 2 (t=1.33): SKIP Sim! Draw at C1 + 1/3*(C2 - C1), replay Phase 1 sprites ---
        movem.l d0-d3,-(a7)
        move.w  $4d6.w,d1               ; C2 (updated at end of Phase 1)
        move.w  $4d8.w,d2
        move.w  d1,d3
        sub.w   sim_prev_x(pc),d3       ; dx = C2 - C1
        cmpi.w  #32,d3
        bgt.s   .lh2_snap
        cmpi.w  #-32,d3
        blt.s   .lh2_snap
        move.w  d2,d0
        sub.w   sim_prev_y(pc),d0       ; dy = C2y - C1y
        cmpi.w  #32,d0
        bgt.s   .lh2_snap
        cmpi.w  #-32,d0
        blt.s   .lh2_snap

        ; render = C1 + delta / 3
        ext.l   d3
        divs.w  #3,d3
        add.w   sim_prev_x(pc),d3
        ext.l   d0
        divs.w  #3,d0
        add.w   sim_prev_y(pc),d0
        bra.s   .lh2_set
.lh2_snap:
        move.w  d1,d3
        move.w  d2,d0
.lh2_set:
        move.w  d3,render_cam_x
        move.w  d0,render_cam_y
        ; Recorded sprites were captured at C1 (sim_prev), so spr_off = C1 - render_cam!
        move.w  sim_prev_x(pc),d3
        sub.w   render_cam_x(pc),d3
        move.w  d3,spr_off_x
        move.w  sim_prev_y(pc),d0
        sub.w   render_cam_y(pc),d0
        move.w  d0,spr_off_y

        clr.w   interp_phase
        move.w  #1,use_interp_cam
        clr.w   spr_rec_enable
        movem.l (a7)+,d0-d3

        ; 1. Draw tilemap at render_cam
        bsr.w   ste_tile_draw

        ; 2. Replay recorded sprites from Phase 1 shifted by (C1 - render_cam)
        movem.l d0-d7/a0-a6,-(a7)
        move.w  spr_rec_cnt(pc),d7
        beq.s   .lh_rep_done
        subq.w  #1,d7
        lea     spr_rec_buf(pc),a4
.lh_rep_lp:
        move.w  (a4)+,d4                ; type
        move.w  (a4)+,d0                ; sx (captured at C1)
        move.w  (a4)+,d1                ; sy
        move.w  (a4)+,d2                ; id
        movem.l d7/a4,-(a7)
        tst.w   d4
        beq.s   .rep_32m
        subq.w  #1,d4
        beq.s   .rep_16m
        jsr     ste_spr32_opaq
        bra.s   .rep_next
.rep_32m:
        jsr     ste_spr32_mask
        bra.s   .rep_next
.rep_16m:
        jsr     ste_spr16_mask
.rep_next:
        movem.l (a7)+,d7/a4
        dbra    d7,.lh_rep_lp
.lh_rep_done:
        movem.l (a7)+,d0-d7/a0-a6

        ; 3. Copy HUD boxes + ticker to back buffer
        bsr.w   ste_hud_hook

        ; 4. Flip with 2-VBL cap ($35a.w = 1 -> 25.0 fps locked!)
        move.w  $35a.w,d0
        jsr     $01ecaa
        jmp     $0030f0

.lh_nosim_reset:
        clr.w   interp_phase
        clr.w   use_interp_cam
        clr.w   spr_off_x
        clr.w   spr_off_y
        clr.w   spr_rec_enable
        move.w  $4d6.w,sim_prev_x
        move.w  $4d8.w,sim_prev_y
        jsr     $0174f6
        jmp     $0030f6

        even
dirty_stack0:
        ds.b    DIRTY_MAX*12            ; 768 bytes
dirty_stack1:
        ds.b    DIRTY_MAX*12            ; 768 bytes
