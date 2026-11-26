; =============================================================================
; Italy 1990 (Codemasters) - 11-A-Side Soccer Enhancement Module
; Target: Atari STE (8 MHz, Blitter + Hardware 1px HSCROLL)
; Assembled to $3a000 (12 KB free RAM inside 512 KB, $3a000-$3cfff)
; Wide pitch double-buffers at $80000 and $88000 (336x168 px, 168 B/line)
; =============================================================================

PATCH_BASE      equ     $3a000
PITCH_BUF0      equ     $80000          ; 168*168 ($6e40) pitch + 32*160 ($1400) HUD = $8240 B
PITCH_BUF1      equ     $89000          ; Second full buffer (256-byte aligned, $89000..$9123f)
STADIUM_BUF     equ     $92000          ; Pre-rendered 640x1216 stadium (320*1216 = $5f000 -> $f1000)
STADIUM_STRIDE  equ     320             ; 640 px = 320 bytes/line (20 tiles x 16 B)
PITCH_STRIDE    equ     168             ; 21 16px groups = 336 px = 168 bytes/line
PITCH_HEIGHT    equ     168             ; 168 scanlines (lines 0..167)
PITCH_HUD_OFF   equ     $6e40           ; 168 * 168 = $6e40 (HUD seamlessly follows line 167!)

; Game RAM addresses
G_SCR_BACK      equ     $11cf6          ; Back screen ($70000 or $78000)
G_SCR_FRONT     equ     $11cfa          ; Front screen ($78000 or $70000)
G_CAM_STRUCT    equ     $fd68           ; Camera struct (+2=camX, +4=camY, +$a=camVY)
G_BALL_STRUCT   equ     $fb98           ; Ball struct (+2=x, +4=y, +8=vx, +$a=vy, +$c=z)
G_CAM_X         equ     $ee50           ; Current camera X (0..320)
G_CAM_Y         equ     $ee4c           ; Current camera Y (0..$410)
G_TILEMAP       equ     $122e6          ; 20x38 pitch tilemap (bytes)
G_TILESET       equ     $2d770          ; 32x32 4-plane tiles ($200 bytes each)
G_PAL_PITCH     equ     $11cac          ; Pitch 16-word palette
G_PAL_HUD       equ     $11ccc          ; HUD 16-word palette
G_GOAL_CNT      equ     $edac           ; Crossbar segment counter

; STE Hardware registers
HW_VBASE_HI     equ     $ffff8201
HW_VBASE_MID    equ     $ffff8203
HW_VBASE_LO     equ     $ffff820d
HW_VCNT_HI      equ     $ffff8205
HW_VCNT_MID     equ     $ffff8207
HW_VCNT_LO      equ     $ffff8209
HW_LINEWID      equ     $ffff820f
HW_HSCROLL      equ     $ffff8265
HW_PAL0         equ     $ffff8240

; STE Blitter registers
BLT_SXINC       equ     $ffff8a20
BLT_SYINC       equ     $ffff8a22
BLT_SADDR       equ     $ffff8a24
BLT_EM1         equ     $ffff8a28
BLT_EM2         equ     $ffff8a2a
BLT_EM3         equ     $ffff8a2c
BLT_DXINC       equ     $ffff8a2e
BLT_DYINC       equ     $ffff8a30
BLT_DADDR       equ     $ffff8a32
BLT_XCNT        equ     $ffff8a36
BLT_YCNT        equ     $ffff8a38
BLT_HOP         equ     $ffff8a3a
BLT_OP          equ     $ffff8a3b
BLT_CTRL        equ     $ffff8a3c
BLT_SKEW        equ     $ffff8a3d

; Macro for full-speed STE Blitter HOG mode (#$c0)
BLT_GO          macro
                move.b  #$c0,BLT_CTRL.w
                endm

                org     PATCH_BASE

; -----------------------------------------------------------------------------
; Entry jump table at fixed offsets from PATCH_BASE ($3a000)
; -----------------------------------------------------------------------------
entry_table:
                jmp     hook_camera(pc)         ; +$00: called from $d278 (replaces jsr $d488)
                jmp     hook_pitch_render(pc)   ; +$04: called from $d2ac (replaces bsr $5fc2)
                jmp     hook_sprite_draw(pc)    ; +$08: called from $c250
                jmp     hook_goal_draw(pc)      ; +$0c: called from $c0e0
                jmp     hook_vbl_pal(pc)        ; +$10: installed at $11a72 (replaces $39dc)
                jmp     hook_flip(pc)           ; +$14: called from $d2f0 (replaces flip)
                jmp     hook_cull_setup(pc)     ; +$18: called from $bccc (sprite culling bounds)
                jmp     hook_match_exit(pc)     ; +$1c: called from $d46e (cleanly reset STE scroll on exit)
                jmp     hook_vbl_guard(pc)      ; +$20: called from $22d6 (guards non-pitch screens + X radar key)
                jmp     hook_ai_outfield(pc)    ; +$24: called from $a5fc (Kick Off 2 AI!)
                jmp     hook_cpu_joy(pc)        ; +$28: called from $ca8a (Kick Off 2 CPU ball AI!)
                jmp     hook_hud_bars(pc)       ; +$2c: called from $cd52 (dirty-checked power bars, saves 13k cyc!)
                jmp     hook_num_bubble(pc)     ; +$30: called from $8ed0 (1P-4P indicator bubble via Blitter!)
                jmp     hook_fast_wait(pc)      ; +$34: called from $230c (6x faster fade transitions!)
                jmp     hook_fire_noball(pc)    ; +$38: called from $c6e4 (Fire w/o ball -> Slide/Jump/Switch!)
                jmp     hook_player_spr(pc)     ; +$3c: called from $bd36 (clean custom slide sprite override!)
                jmp     hook_kick(pc)           ; +$40: called from $cb64 (smart ground pass, reverse chip, balanced shot!)
                jmp     hook_gk_ai(pc)          ; +$44: called from $96b0 (Kick Off 2 goalkeeper AI!)
                jmp     hook_throwin(pc)        ; +$48: called from $db2e (manual human throw-in aiming!)
                jmp     hook_goalkick(pc)       ; +$4c: called from $b004 (manual human goal-kick aiming!)

; -----------------------------------------------------------------------------
; Persistent state variables
; -----------------------------------------------------------------------------
st_front_pitch: dc.l    PITCH_BUF1              ; Front pitch buffer displayed by VBL
st_front_hud:   dc.l    $78000+$6900            ; Front HUD address ($76900 or $7e900)
st_back_fine_x: dc.w    0                       ; Fine scroll (0..15) rendered into back buf
st_front_fine_x:dc.w    0                       ; Fine scroll (0..15) latched for front buf
st_cam_x_init:  dc.w    0                       ; 0 = first frame init flag
st_radar_on:    dc.w    0                       ; 0 = Kick Off 2 radar OFF by default (toggle with 'X' key!)
st_x_prev:      dc.w    0                       ; Edge-detect for 'X' key ($2d)
st_t1_chaser:   dc.w    -1                      ; Closest outfield player ID on Team 1 (1..10)
st_t2_chaser:   dc.w    -1                      ; Closest outfield player ID on Team 2 (12..21)
st_ai_frame:    dc.w    0                       ; Frame parity for alternating even/odd AI updates
st_stadium_ok:  dc.w    0                       ; 1 = full 640x1216 stadium pre-rendered at $92000
st_in_match:    dc.w    0                       ; 1 = active match (prevents pre-match LINEWID shear!)
st_hud_p12:     dc.l    -1                      ; Cached 1P/2P power bar values
st_hud_p34:     dc.l    -1                      ; Cached 3P/4P power bar values
st_hud_dirty:   dc.w    2                       ; Redraw both double-buffers when power bars change
st_hud_clk:     dc.l    -1                      ; Cached clock ($12168.l)
st_hud_mode:    dc.w    -1                      ; Cached banner mode ($ce2a.w)
st_hud_sync:    dc.w    2                       ; Sync BOTH double-buffers (2 frames) on any HUD change!
st_hud_fx0:     dc.w    -1                      ; Last fine_x copied into PITCH_BUF0 HUD
st_hud_fx1:     dc.w    -1                      ; Last fine_x copied into PITCH_BUF1 HUD
st_tackle_tmr:  dc.w    0                       ; Active slide-tackle frames remaining (0..12)
st_tackle_id:   dc.w    -1                      ; Sliding player ID
st_tackle_vx:   dc.w    0                       ; Slide tackle velocity X
st_tackle_vy:   dc.w    0                       ; Slide tackle velocity Y
st_tackle_dir:  dc.w    0                       ; Slide tackle direction (0..7)
st_tackle_pose: dc.w    0                       ; Custom slide sprite pose (0=R,1=L,2=D,3=U)
st_tackle_orig: dc.l    0                       ; Saved original $2a(a5) sprite table ptr
st_tackle_won:  dc.w    0                       ; 1 = won ball cleanly during this slide
st_jump_tmr:    dc.w    0                       ; Active jump frames remaining
st_jump_id:     dc.w    -1                      ; Jumping player ID
st_jump_vz:     dc.w    0                       ; Vertical jump velocity (gravity -1/frame)
st_cam_vx:      dc.w    0                       ; Smoothed camera X velocity (eliminates judder!)
st_cam_vy:      dc.w    0                       ; Smoothed camera Y velocity
st_cpu_hold:    dc.w    0                       ; Frames CPU has dribbled (triggers Kick Off 2 passing!)
st_cpu_shoot:   dc.w    0                       ; 1 = CPU charging a power shot (hold Fire 6 frames)
st_setp_chg:    dc.w    0                       ; Human throw-in / goal-kick Fire hold counter

; =============================================================================
; 1. SMOOTH 1-PIXEL HORIZONTAL + VERTICAL CAMERA TRACKING (hook_camera)
;    Replaces BOTH jerky $d488 (Y accel) and $b2a8 (coarse Y step) with silky
;    velocity-damped 1-pixel tracking in X (0..320) AND Y (0..$410)!
;    Also ticks active slide tackles, jumps, and computes single chasers per team.
; =============================================================================
hook_camera:
                movem.l d0-d3/a4-a5,-(a7)
                lea     G_CAM_STRUCT.l,a5
                lea     G_BALL_STRUCT.l,a4

                ; --- X target = clamp(ball.x + ball.vx/4 - 160, 0, 320) ---
                move.w  2(a4),d0                ; ball.x
                move.w  8(a4),d1                ; ball.vx (gentle 1/4 lead -> zero whiplash!)
                asr.w   #2,d1
                add.w   d1,d0
                subi.w  #160,d0
                bpl.s   .chk_xmax
                moveq   #0,d0
                bra.s   .x_clamped
.chk_xmax:
                cmpi.w  #320,d0
                ble.s   .x_clamped
                move.w  #320,d0
.x_clamped:
                ; --- Y target = clamp(ball.y + ball.vy/4 - 84, 0, $410) ---
                move.w  4(a4),d3                ; ball.y
                move.w  10(a4),d1               ; ball.vy (gentle 1/4 lead -> zero whiplash!)
                asr.w   #2,d1
                add.w   d1,d3
                subi.w  #84,d3
                bpl.s   .chk_ymax
                moveq   #0,d3
                bra.s   .y_clamped
.chk_ymax:
                cmpi.w  #$410,d3
                ble.s   .y_clamped
                move.w  #$410,d3
.y_clamped:
                ; First frame? Snap both X and Y immediately!
                tst.w   st_cam_x_init
                bne.s   .smooth_xy
                move.w  #1,st_cam_x_init
                move.w  d0,2(a5)
                move.w  d3,4(a5)
                clr.w   10(a5)
                clr.w   st_cam_vx
                clr.w   st_cam_vy
                bra.w   .cam_done

.smooth_xy:
                ; Velocity-damped X step: desired = clamp(diff >> 3, -8..+8), accel clamped to +-2/frame!
                move.w  2(a5),d1
                sub.w   d1,d0                   ; d0 = diffX
                move.w  d0,d2
                asr.w   #3,d2
                bne.s   .xhave
                tst.w   d0
                beq.s   .xvel
                moveq   #1,d2
                tst.w   d0
                bpl.s   .xvel
                moveq   #-1,d2
                bra.s   .xvel
.xhave:         cmpi.w  #11,d2
                ble.s   .xneg
                moveq   #11,d2
                bra.s   .xvel
.xneg:          cmpi.w  #-11,d2
                bge.s   .xvel
                moveq   #-11,d2
.xvel:          ; Smooth st_cam_vx toward d2 by max +-2 px/frame
                move.w  st_cam_vx(pc),d0
                sub.w   d0,d2                   ; delta_v = desired - cur_v
                cmpi.w  #2,d2
                ble.s   .xac_lo
                moveq   #2,d2
                bra.s   .xac_ok
.xac_lo:        cmpi.w  #-2,d2
                bge.s   .xac_ok
                moveq   #-2,d2
.xac_ok:        add.w   d2,d0
                move.w  d0,st_cam_vx
                add.w   d0,d1
                bpl.s   .xhi
                moveq   #0,d1
                clr.w   st_cam_vx
                bra.s   .xsto
.xhi:           cmpi.w  #320,d1
                ble.s   .xsto
                move.w  #320,d1
                clr.w   st_cam_vx
.xsto:          move.w  d1,2(a5)

.do_y:
                ; Velocity-damped Y step: desired = clamp(diff >> 3, -8..+8), accel clamped to +-2/frame!
                move.w  4(a5),d1
                sub.w   d1,d3                   ; d3 = diffY
                move.w  d3,d2
                asr.w   #3,d2
                bne.s   .yhave
                tst.w   d3
                beq.s   .yvel
                moveq   #1,d2
                tst.w   d3
                bpl.s   .yvel
                moveq   #-1,d2
                bra.s   .yvel
.yhave:         cmpi.w  #11,d2
                ble.s   .yneg
                moveq   #11,d2
                bra.s   .yvel
.yneg:          cmpi.w  #-11,d2
                bge.s   .yvel
                moveq   #-11,d2
.yvel:          move.w  st_cam_vy(pc),d0
                sub.w   d0,d2
                cmpi.w  #2,d2
                ble.s   .yac_lo
                moveq   #2,d2
                bra.s   .yac_ok
.yac_lo:        cmpi.w  #-2,d2
                bge.s   .yac_ok
                moveq   #-2,d2
.yac_ok:        add.w   d2,d0
                move.w  d0,st_cam_vy
                add.w   d0,d1
                bpl.s   .yhi
                moveq   #0,d1
                clr.w   st_cam_vy
                bra.s   .ysto
.yhi:           cmpi.w  #$410,d1
                ble.s   .ysto
                move.w  #$410,d1
                clr.w   st_cam_vy
.ysto:          move.w  d1,4(a5)
                clr.w   10(a5)
.cam_done:
                ; Tick active slide tackle, jump/header, & compute single chasers per team
                bsr.w   tick_slide_tackle
                bsr.w   tick_jump
                addq.w  #1,st_ai_frame
                bsr.s   compute_chasers
                movem.l (a7)+,d0-d3/a4-a5
                rts

; Find closest outfield player to ball on Team 1 (P01..P10) and Team 2 (P12..P21)
compute_chasers:
                movem.l d3-d6/a0,-(a7)
                ; Team 1: P01..P10
                lea     G_PLAYERS+$3a.l,a0
                moveq   #9,d6
                move.w  #$7fff,d4               ; best dist
                moveq   #-1,d5                  ; best id
.cc_t1:
                move.w  2(a0),d0
                sub.w   2(a4),d0
                bpl.s   .t1x
                neg.w   d0
.t1x:           move.w  4(a0),d1
                sub.w   4(a4),d1
                bpl.s   .t1y
                neg.w   d1
.t1y:           add.w   d1,d0
                cmp.w   d4,d0
                bge.s   .t1n
                move.w  d0,d4
                move.w  0(a0),d5
.t1n:           lea     $3a(a0),a0
                dbra    d6,.cc_t1
                move.w  d5,st_t1_chaser

                ; Team 2: P12..P21
                lea     G_PLAYERS+12*$3a.l,a0
                moveq   #9,d6
                move.w  #$7fff,d4
                moveq   #-1,d5
.cc_t2:
                move.w  2(a0),d0
                sub.w   2(a4),d0
                bpl.s   .t2x
                neg.w   d0
.t2x:           move.w  4(a0),d1
                sub.w   4(a4),d1
                bpl.s   .t2y
                neg.w   d1
.t2y:           add.w   d1,d0
                cmp.w   d4,d0
                bge.s   .t2n
                move.w  d0,d4
                move.w  0(a0),d5
.t2n:           lea     $3a(a0),a0
                dbra    d6,.cc_t2
                move.w  d5,st_t2_chaser
                movem.l (a7)+,d3-d6/a0
                rts

; =============================================================================
; 2. SPRITE CULLING BOUNDS FOR 320px WIDE VIEWPORT (hook_cull_setup)
;    Original $bccc:
;      d0 = ($ee50 - 1) & $fff0; d1 = d0 + $110; d2 = $ee4c; d3 = d2 + $c0
;    New:
;      d0 = $ee50 & $fff0 (coarse_x); d1 = d0 + 336 ($150); d2 = $ee4c; d3 = d2 + $c0
; =============================================================================
hook_cull_setup:
                move.w  G_CAM_X.l,d0
                andi.w  #$fff0,d0              ; coarse_x (multiple of 16)
                move.w  d0,d1
                addi.w  #336,d1                ; coarse_x + 336
                move.w  G_CAM_Y.l,d2
                move.w  d2,d3
                addi.w  #$c0,d3
                rts

; =============================================================================
; 3. 1-CALL STE BLITTER STADIUM RENDERER (hook_pitch_render)
;    First frame: pre-renders entire 20x38 tilemap (640x1216) to STADIUM_BUF ($92000).
;    Every frame: ONE SINGLE Blitter call copies 336x168 window to back_pitch_buf!
; =============================================================================
hook_pitch_render:
                movem.l d0-d4/a0-a1,-(a7)

                ; Build full 640x1216 stadium bitmap ONCE
                tst.w   st_stadium_ok
                bne.s   .stadium_ready
                bsr.w   build_stadium_bitmap
                move.w  #1,st_stadium_ok
.stadium_ready:
                ; Update back_fine_x = camX & 15, coarse_x = camX & $fff0
                moveq   #0,d0
                move.w  G_CAM_X.l,d0
                move.w  d0,d1
                andi.w  #15,d1
                move.w  d1,st_back_fine_x
                andi.w  #$fff0,d0
                lsr.w   #1,d0                   ; coarse_x_bytes = (coarse_x >> 4) * 8

                ; SADDR = STADIUM_BUF + camY * 320 + coarse_x_bytes
                move.w  G_CAM_Y.l,d1
                move.w  d1,$120fe.l             ; keep game var in sync
                mulu.w  #STADIUM_STRIDE,d1
                add.l   d0,d1
                addi.l  #STADIUM_BUF,d1         ; d1 = source address in pre-rendered stadium

                ; DADDR = back_pitch_buf ($80000 or $89000)
                move.l  #PITCH_BUF0,d2
                cmpi.l  #$78000,G_SCR_BACK.l
                bne.s   .p_b0
                move.l  #PITCH_BUF1,d2
.p_b0:
                ; 21 x 8-line HOG Blitter slices (0.67 ms per slice < 1.28 ms IKBD byte period!)
                ; Prevents IKBD ACIA overrun -> 100% crisp, zero-stuck joystick & keyboard response!
                lea     $ffff8a00.w,a0
                move.w  #2,$20(a0)              ; SXINC = 2
                move.w  #STADIUM_STRIDE-PITCH_STRIDE+2,$22(a0) ; SYINC = 154
                move.l  d1,$24(a0)              ; SADDR (auto-advances across slices!)
                move.w  #$ffff,$28(a0)          ; EM1
                move.w  #$ffff,$2a(a0)          ; EM2
                move.w  #$ffff,$2c(a0)          ; EM3
                move.w  #2,$2e(a0)              ; DXINC = 2
                move.w  #2,$30(a0)              ; DYINC = 2 (contiguous 168 B/line!)
                move.l  d2,$32(a0)              ; DADDR (auto-advances across slices!)
                move.w  #84,$36(a0)             ; XCNT = 84 words (336 px, preserved!)
                move.b  #2,$3a(a0)              ; HOP = source
                move.b  #3,$3b(a0)              ; OP = S -> D
                move.b  #0,$3d(a0)              ; SKEW = 0
                moveq   #13,d3                  ; 14 slices x 12 lines = 168 lines (1.00ms/slice, IKBD-safe!)
.p_slice:
                move.w  #12,$38(a0)             ; YCNT = 12 lines
                move.b  #$c0,$3c(a0)            ; HOG GO (IKBD IRQ fires cleanly between slices!)
                dbra    d3,.p_slice

                movem.l (a7)+,d0-d4/a0-a1
                rts

; One-time pre-render of all 20x38 tiles ($122e6 / $2d770) into STADIUM_BUF ($92000)
build_stadium_bitmap:
                movem.l d0-d7/a0-a6,-(a7)
                lea     $ffff8a00.w,a6
                move.w  #2,$20(a6)              ; SXINC = 2
                move.w  #2,$22(a6)              ; SYINC = 2
                move.w  #2,$2e(a6)              ; DXINC = 2
                move.w  #STADIUM_STRIDE-14,$30(a6) ; DYINC = 320 - 14 = 306
                move.w  #$ffff,$28(a6)
                move.w  #$ffff,$2a(a6)
                move.w  #$ffff,$2c(a6)
                move.w  #8,$36(a6)              ; XCNT = 8 words (32 px)
                move.b  #2,$3a(a6)
                move.b  #3,$3b(a6)
                move.b  #0,$3d(a6)

                lea     G_TILEMAP.l,a2
                lea     G_TILESET.l,a4
                move.l  #STADIUM_BUF,a0
                moveq   #37,d7                  ; 38 tile rows
.bs_row:
                move.l  a0,a3
                moveq   #19,d6                  ; 20 tile cols
.bs_col:
                moveq   #0,d0
                move.b  (a2)+,d0
                lsl.l   #8,d0
                add.l   d0,d0                   ; * 512 ($200)
                lea     (a4,d0.l),a1
                move.l  a1,$24(a6)
                move.l  a3,$32(a6)
                move.w  #32,$38(a6)             ; 32 lines
                move.b  #$c0,$3c(a6)
                lea     16(a3),a3               ; +32 px
                dbra    d6,.bs_col
                adda.l  #STADIUM_STRIDE*32,a0   ; next 32-line tile strip (+10,240 bytes)
                dbra    d7,.bs_row

                movem.l (a7)+,d0-d7/a0-a6
                rts

; =============================================================================
; 4. STE BLITTER MASKED SPRITE DRAWER (hook_sprite_draw, replaces $c250)
;    Inputs from $c0b6:
;      d0.w = bufX (worldX - coarse_x, signed!)
;      d1.w = screenY (signed!)
;      d2.w = height - 1 (dbra count, so rows = d2 + 1)
;      a1   = sprite data (10 bytes/row: mask.w, p0.w, p1.w, p2.w, p3.w)
; =============================================================================
hook_sprite_draw:
                movem.l d0-d7/a0-a4,-(a7)
                move.w  d2,d6
                addq.w  #1,d6                  ; d6 = total rows (1..64)

                ; Vertical clip against [0 .. PITCH_HEIGHT-1]
                tst.w   d1
                bpl.s   .y_top_ok
                ; Top clip: skip (-d1) rows
                add.w   d1,d6                  ; rows -= (-d1)
                ble.w   .sp_done
                neg.w   d1
                mulu.w  #10,d1
                adda.l  d1,a1
                moveq   #0,d1
.y_top_ok:
                move.w  #PITCH_HEIGHT,d4
                sub.w   d1,d4                  ; max visible rows from y
                ble.w   .sp_done
                cmp.w   d4,d6
                ble.s   .y_bot_ok
                move.w  d4,d6                  ; clamp bottom
.y_bot_ok:
                ; Horizontal clip against [-15 .. 335]
                cmpi.w  #-15,d0
                blt.w   .sp_done
                cmpi.w  #336,d0
                bge.w   .sp_done

                ; Destination buffer base ($80000 or $88000) + y * 168
                move.l  #PITCH_BUF0,a0
                cmpi.l  #$78000,G_SCR_BACK.l
                bne.s   .sp_b0
                move.l  #PITCH_BUF1,a0
.sp_b0:
                mulu.w  #PITCH_STRIDE,d1
                adda.l  d1,a0

                ; Compute skew = d0 & 15, word_col = d0 >> 4 (arithmetic)
                move.w  d0,d3
                andi.w  #15,d3                 ; d3 = skew (0..15)
                move.w  d0,d4
                asr.w   #4,d4                  ; d4 = word_col (-1 .. 20)

                ; Common Blitter regs
                move.w  #0,BLT_SXINC.w
                move.w  #10,BLT_SYINC.w        ; 10 bytes per sprite row
                move.w  #$ffff,BLT_EM2.w
                move.b  #2,BLT_HOP.w           ; Source only

                ; Check horizontal clipping cases:
                ; Case A: d4 < 0 (left clip: -15 <= bufX <= -1, only word 1 visible at col 0)
                tst.w   d4
                bmi.s   .clip_left
                ; Case B: d4 == 20 and skew > 0 (right clip: 321..335, only word 0 visible at col 20)
                cmpi.w  #20,d4
                blt.s   .no_hclip
                tst.w   d3
                beq.s   .unshifted              ; col 20, skew 0 -> fits in 1 word!
                ; Right clip (1 word at col 20 = +160 bytes)
                adda.w  #160,a0
                move.w  #$ffff,d5
                lsr.w   d3,d5                  ; EM1 = $ffff >> skew
                move.w  d5,BLT_EM1.w
                move.w  d5,BLT_EM3.w
                move.w  #PITCH_STRIDE,BLT_DYINC.w
                move.w  #1,d7                  ; XCNT = 1
                move.b  d3,d5                  ; skew (FXSR=0, NFSR=0)
                bra.s   .do_blit

.clip_left:
                ; Left clip: a0 stays at col 0; FXSR=1 ($80) shifts word 0 into word 1!
                move.w  #$ffff,d5
                lsr.w   d3,d5
                not.w   d5                      ; EM1 = ~($ffff >> skew) (left bits valid)
                move.w  d5,BLT_EM1.w
                move.w  d5,BLT_EM3.w
                move.w  #PITCH_STRIDE,BLT_DYINC.w
                move.w  #1,d7                  ; XCNT = 1
                move.b  d3,d5
                ori.b   #$80,d5                ; FXSR = 1
                bra.s   .do_blit

.no_hclip:
                ; Add word_col * 8 to a0
                lsl.w   #3,d4
                adda.w  d4,a0
                tst.w   d3
                bne.s   .shifted_2w

.unshifted:
                ; Exact 16px alignment (skew == 0, 1 word wide)
                cmpi.w  #20,d4
                bne.s   .unsh_ok
                adda.w  #160,a0
.unsh_ok:
                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM3.w
                move.w  #PITCH_STRIDE,BLT_DYINC.w
                move.w  #1,d7                  ; XCNT = 1
                moveq   #0,d5                  ; skew = 0
                bra.s   .do_blit

.shifted_2w:
                ; Normal 2-word shifted blit (0 <= word_col <= 19, 1 <= skew <= 15)
                move.w  #$ffff,d5
                lsr.w   d3,d5                  ; EM1 = $ffff >> skew
                move.w  d5,BLT_EM1.w
                not.w   d5                      ; EM3 = ~EM1
                move.w  d5,BLT_EM3.w
                move.w  #8,BLT_DXINC.w         ; next word of same plane is +8 bytes
                move.w  #PITCH_STRIDE-8,BLT_DYINC.w ; 160 bytes to next scanline
                move.w  #2,d7                  ; XCNT = 2
                move.b  d3,d5
                ori.b   #$40,d5                ; NFSR = 1 (read 1 word per line!)

.do_blit:
                lea     $ffff8a00.w,a3          ; Blitter base in a3 (faster register-indirect!)
                move.b  d5,$3d(a3)              ; SKEW
                move.w  d7,$36(a3)              ; XCNT (preserved across all 8 passes!)

                ; Pass 1: Mask AND (OP = 1: S AND D) across all 4 bitplanes
                move.b  #1,$3b(a3)
                move.l  a0,a2
                moveq   #3,d4
.mask_loop:
                move.l  a1,$24(a3)
                move.l  a2,$32(a3)
                move.w  d6,$38(a3)
                move.b  #$c0,$3c(a3)
                addq.l  #2,a2
                dbra    d4,.mask_loop

                ; Pass 2: 4 Bitplanes OR (OP = 7: S OR D)
                move.b  #7,$3b(a3)
                addq.l  #2,a1                   ; a1 -> plane 0
                move.l  a0,a2
                moveq   #3,d4
.plane_loop:
                move.l  a1,$24(a3)
                move.l  a2,$32(a3)
                move.w  d6,$38(a3)
                move.b  #$c0,$3c(a3)
                addq.l  #2,a1
                addq.l  #2,a2
                dbra    d4,.plane_loop

.sp_done:
                movem.l (a7)+,d0-d7/a0-a4
                rts

; =============================================================================
; 5. GOALPOST / CROSSBAR DRAWER FOR 336px PITCH BUFFER (hook_goal_draw)
;    Replaces $c0e0. Uses same 168-byte stride & clips cleanly to [0..335].
;    Inputs: d0=bufX, d1=screenY, d2=height-1, a1=type ($eda0/$eda4/$ed9c)
; =============================================================================
hook_goal_draw:
                movem.l d0-d7/a0-a4,-(a7)
                ; Horizontal bounds check
                tst.w   d0
                bmi.w   .gd_done
                cmpi.w  #320,d0
                bgt.w   .gd_done

                move.l  #PITCH_BUF0,a0
                cmpi.l  #$78000,G_SCR_BACK.l
                bne.s   .gd_b0
                move.l  #PITCH_BUF1,a0
.gd_b0:
                move.l  a0,a4                  ; top bound
                lea     PITCH_STRIDE*PITCH_HEIGHT(a0),a3 ; bottom bound ($6e40)

                move.w  d2,d6                  ; dbra row count
                muls.w  #PITCH_STRIDE,d1
                adda.l  d1,a0
                move.w  d0,d1
                lsr.w   #4,d1
                lsl.w   #3,d1
                adda.w  d1,a0

                cmpa.l  #$eda0,a1
                bne.s   .gd_chk2
                clr.w   G_GOAL_CNT.l
                move.b  #$30,d2
                move.b  #$cf,d3
.gd_l1:
                cmpa.l  a4,a0
                bcs.s   .gd_n1
                cmpa.l  a3,a0
                bcc.s   .gd_n1
                or.b    d2,(a0)
                and.b   d3,2(a0)
                and.b   d3,4(a0)
                and.b   d3,6(a0)
.gd_n1:         lea     PITCH_STRIDE(a0),a0
                dbra    d6,.gd_l1
                bra.w   .gd_done

.gd_chk2:
                cmpa.l  #$eda4,a1
                bne.s   .gd_chk3
                move.b  #$0c,d2
                move.b  #$f3,d3
.gd_l2:
                cmpa.l  a4,a0
                bcs.s   .gd_n2
                cmpa.l  a3,a0
                bcc.s   .gd_n2
                or.b    d2,1(a0)
                and.b   d3,3(a0)
                and.b   d3,5(a0)
                and.b   d3,7(a0)
.gd_n2:         lea     PITCH_STRIDE(a0),a0
                dbra    d6,.gd_l2
                bra.w   .gd_done

.gd_chk3:
                cmpa.l  #$ed9c,a1
                bne.s   .gd_done
                addq.w  #1,G_GOAL_CNT.l
.gd_l3:
                cmpa.l  a4,a0
                bcs.s   .gd_n3
                cmpa.l  a3,a0
                bcc.s   .gd_n3
                cmpi.w  #6,G_GOAL_CNT.l
                bne.s   .gd_c1
                move.w  #$fffc,(a0)
                andi.l  #$00030003,2(a0)
                andi.w  #$0003,6(a0)
                bra.s   .gd_n3
.gd_c1:
                cmpi.w  #1,G_GOAL_CNT.l
                bne.s   .gd_cmid
                move.w  #$3fff,(a0)
                andi.l  #$c000c000,2(a0)
                andi.w  #$c000,6(a0)
                bra.s   .gd_n3
.gd_cmid:
                move.w  #$ffff,(a0)
                clr.l   2(a0)
                clr.w   6(a0)
.gd_n3:         lea     PITCH_STRIDE(a0),a0
                dbra    d6,.gd_l3

.gd_done:
                movem.l (a7)+,d0-d7/a0-a4
                rts

; =============================================================================
; 6. SCREEN FLIP HOOK (hook_flip, replaces $d2f0..$d316)
;    Copies 32-line HUD ($76900/$7e900) into back_pitch_buf + $6e40 (stride 168)
;    pre-shifted RIGHT by back_fine_x pixels so STE HSCROLL cancels to 0px shift!
;    Swaps $11cf6 <-> $11cfa, writes STE VBASE immediately (latched at next VBL!).
; =============================================================================
hook_flip:
                movem.l d1-d3/a0-a1,-(a7)
                move.l  G_SCR_BACK.l,d0         ; d0 = finished back screen ($70000 or $78000)

                ; Determine finished pitch buffer ($80000 or $90000)
                move.l  #PITCH_BUF0,d1
                cmpi.l  #$78000,d0
                bne.s   .fl_b0
                move.l  #PITCH_BUF1,d1
.fl_b0:
                ; Zero-flicker smart HUD copy: detect clock ($12168) or banner ($ce2a) or powerbar changes
                ; and copy BOTH double-buffers (st_hud_sync = 2) so both buffers always match 100%!
                move.l  $12168.l,d2
                cmp.l   st_hud_clk(pc),d2
                bne.s   .hud_mark_sync
                move.w  $ce2a.l,d2
                cmp.w   st_hud_mode(pc),d2
                bne.s   .hud_mark_sync
                tst.w   st_hud_dirty
                beq.s   .hud_chk_fx
.hud_mark_sync:
                move.l  $12168.l,st_hud_clk
                move.w  $ce2a.l,st_hud_mode
                move.w  #2,st_hud_sync
.hud_chk_fx:
                lea     st_hud_fx0(pc),a0
                cmpi.l  #PITCH_BUF0,d1
                beq.s   .hfx_b0
                addq.l  #2,a0
.hfx_b0:
                move.w  st_back_fine_x(pc),d2
                cmp.w   (a0),d2
                bne.s   .hud_do_copy            ; fine_x changed for this buffer -> must re-shift!
                tst.w   st_hud_sync
                beq.w   .hud_done               ; both buffers in sync & fine_x unchanged -> skip!
                subq.w  #1,st_hud_sync
.hud_do_copy:
                move.w  d2,(a0)
                ; Blitter-copy active HUD (X=48..287 = 14 src -> 15 dst words, 26 lines 170..195)
                move.l  d0,a0
                adda.l  #$6900+320+24,a0        ; a0 = src HUD line 170, X=48 (+24 B)
                move.l  d1,a1
                adda.l  #PITCH_HUD_OFF+336+24,a1 ; a1 = dst HUD line 170, X=48 (+24 B)

                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                move.w  #$ffff,BLT_EM3.w
                move.b  #2,BLT_HOP.w
                move.b  #3,BLT_OP.w

                tst.w   d2
                bne.s   .hud_shifted

                ; fine_x == 0: 15 16px-groups = 60 words x 24 lines (2 x 12-line IKBD-safe slices)
                move.w  #2,BLT_SXINC.w
                move.w  #160-118,BLT_SYINC.w    ; 160 - 59*2 = 42
                move.w  #2,BLT_DXINC.w
                move.w  #168-118,BLT_DYINC.w    ; 168 - 59*2 = 50
                move.b  #0,BLT_SKEW.w
                move.l  a0,BLT_SADDR.w
                move.l  a1,BLT_DADDR.w
                move.w  #60,BLT_XCNT.w
                move.w  #12,BLT_YCNT.w
                BLT_GO
                move.w  #12,BLT_YCNT.w
                BLT_GO
                bra.s   .hud_done

.hud_shifted:
                ; fine_x != 0: shift 14 src -> 15 dst words per plane x 24 lines (0.36ms/plane)
                move.w  #8,BLT_SXINC.w
                move.w  #160-104,BLT_SYINC.w    ; 160 - 13*8 = 56
                move.w  #8,BLT_DXINC.w
                move.w  #168-112,BLT_DYINC.w    ; 168 - 14*8 = 56
                ori.b   #$40,d2                 ; NFSR = 1
                move.b  d2,BLT_SKEW.w
                moveq   #3,d3
.hud_plane:
                move.l  a0,BLT_SADDR.w
                move.l  a1,BLT_DADDR.w
                move.w  #15,BLT_XCNT.w
                move.w  #24,BLT_YCNT.w
                BLT_GO
                addq.l  #2,a0
                addq.l  #2,a1
                dbra    d3,.hud_plane

.hud_done:
                ; Draw ground shadow beneath jumping player if airborne!
                tst.w   st_jump_tmr
                beq.s   .no_jshad
                bsr.w   draw_jump_shadow
.no_jshad:
                ; Draw Kick Off 2-style Radar overlay into finished back pitch buffer (d1) if enabled!
                tst.w   st_radar_on
                beq.s   .no_radar
                bsr.w   draw_radar
.no_radar:
                ; Swap game screen pointers
                move.l  G_SCR_FRONT.l,G_SCR_BACK.l
                move.l  d0,G_SCR_FRONT.l

                ; Program HW_VBASE_HI/MID/LO NOW so Shifter latches it at start of next VBL!
                move.w  sr,-(a7)
                ori.w   #$0700,sr
                move.w  #1,st_in_match          ; Mark active match so VBL enables 168-B stride!
                move.l  d1,st_front_pitch
                move.b  d1,HW_VBASE_LO.w        ; $00
                lsr.l   #8,d1
                move.b  d1,HW_VBASE_MID.w       ; $00 or $90
                lsr.l   #8,d1
                move.b  d1,HW_VBASE_HI.w        ; $08
                move.w  st_back_fine_x(pc),st_front_fine_x
                move.w  (a7)+,sr
                movem.l (a7)+,d1-d3/a0-a1
                rts

; =============================================================================
; 6b. MATCH EXIT CLEANUP (hook_match_exit, replaces $d46e)
; =============================================================================
hook_match_exit:
                clr.w   st_in_match
                clr.b   HW_HSCROLL.w
                clr.b   HW_LINEWID.w
                clr.w   st_front_fine_x
                clr.w   st_back_fine_x
                clr.w   st_cam_x_init
                move.l  #$78000,d0
                move.b  #0,HW_VBASE_LO.w
                lsr.l   #8,d0
                move.b  d0,HW_VBASE_MID.w
                lsr.l   #8,d0
                move.b  d0,HW_VBASE_HI.w
                move.w  d7,d0
                rts

; =============================================================================
; 6c. VBL GUARD + 'X' KEY RADAR TOGGLE (hook_vbl_guard, replaces $22d6..$22dd)
; =============================================================================
hook_vbl_guard:
                ; Edge-detect 'X' key (ASCII 'X'=$58 -> key-down byte at $137ce+$58 = $13826!)
                tst.b   $13826.l
                beq.s   .x_up
                tst.w   st_x_prev
                bne.s   .x_done
                move.w  #1,st_x_prev
                eori.w  #1,st_radar_on
                bra.s   .x_done
.x_up:
                clr.w   st_x_prev
.x_done:
                movea.l $11a72.l,a0
                cmpa.l  #$39dc,a0
                beq.s   .vg_call
                clr.b   HW_HSCROLL.w
                clr.b   HW_LINEWID.w
.vg_call:
                jmp     (a0)

; =============================================================================
; 7. VBL PALETTE + STE HSCROLL SETUP (hook_vbl_pal, installed at $39dc)
; =============================================================================
hook_vbl_pal:
                movem.l d0-d7/a0,-(a7)
                ; Load pitch palette
                lea     G_PAL_PITCH.l,a0
                movem.l (a0),d0-d7
                lea     HW_PAL0.w,a0
                movem.l d0-d7,(a0)

                ; Program STE HSCROLL ($ff8265) & LINEWID ($ff820f) ONLY once match flip has run!
                tst.w   st_in_match
                bne.s   .vp_active
                clr.b   HW_HSCROLL.w
                clr.b   HW_LINEWID.w
                bra.s   .arm_tb
.vp_active:
                move.w  st_front_fine_x(pc),d0
                move.b  d0,HW_HSCROLL.w
                tst.w   d0
                bne.s   .lw0
                move.b  #4,HW_LINEWID.w        ; fine_x==0: 160 + 8 = 168 B/line
                bra.s   .arm_tb
.lw0:
                move.b  #0,HW_LINEWID.w        ; fine_x!=0: 168 + 0 = 168 B/line
.arm_tb:
                ; Arm Timer B at scanline 168 to swap palette ONLY (zero Shifter scroll touch!)
                clr.b   $fffffa1b.w
                move.l  #tb_hud_split,$120.w
                move.b  #168,$fffffa21.w
                move.b  #8,$fffffa1b.w

                movem.l (a7)+,d0-d7/a0
                rts

; =============================================================================
; 8. TIMER B HBL SPLIT AT SCANLINE 168 (tb_hud_split)
;    Palette swap ONLY — rock-solid 0-jitter HUD!
; =============================================================================
tb_hud_split:
                clr.b   $fffffa1b.w
                move.w  sr,-(a7)
                move.w  #$2700,sr
                movem.l d0-d7/a0,-(a7)
                lea     G_PAL_HUD.l,a0
                movem.l (a0),d0-d7
                lea     HW_PAL0.w,a0
                movem.l d0-d7,(a0)
                movem.l (a7)+,d0-d7/a0
                bclr.b  #0,$fffffa0f.w
                move.w  (a7)+,sr
                rte


; =============================================================================
; 9. KICK OFF 2-INSPIRED OUTFIELD PLAYER AI (hook_ai_outfield, replaces $a5fc)
;    Called per outfield AI player with a5 = player struct ($3a bytes).
;    - Smooth continuous 4-4-2 dynamic formation scaling with ball (X, Y)
;    - Possession-aware attacking runs & defensive tracking back
;    - Active pressing/interception when near ball or loose ball
;    - Falls back cleanly to original $a606 during set pieces ($ee08 != 0)
; =============================================================================
G_PLAYERS       equ     $f0b8           ; 22 player structs, stride $3a
G_BALL_OWNER    equ     $edfa           ; Owner player ID ($ffff = loose)
G_MATCH_STATE   equ     $ee08           ; 0 = open play, !=0 = set piece
G_HALF_DIR      equ     $12172          ; 0 = 1st half (T1 down, T2 up), !=0 = 2nd half

hook_ai_outfield:
                tst.w   $ee18.l                 ; Paused / kickoff freeze?
                bne.w   .ai_ret
                tst.w   G_MATCH_STATE.l         ; Set piece?
                beq.s   .ai_open_play
                cmpa.l  $ee0c.l,a5              ; Keep original taker logic for the set-piece taker!
                bne.s   .ai_open_play
                jmp     $a606.l
.ai_open_play:
                ; Run alternating half of AI players per frame EXCEPT active chasers (every frame!)
                move.w  0(a5),d0
                cmp.w   st_t1_chaser(pc),d0
                beq.s   .ai_run_now
                cmp.w   st_t2_chaser(pc),d0
                beq.s   .ai_run_now
                add.w   st_ai_frame(pc),d0
                btst    #0,d0
                bne.w   .ai_ret
.ai_run_now:
                movem.l d0-d7/a0-a4,-(a7)
                lea     G_BALL_STRUCT.l,a4      ; a4 = ball struct

                ; Determine team (d6: 0=Team1, 1=Team2) and role (d5: 0..9)
                move.w  0(a5),d5                ; player ID (1..10 or 12..21)
                moveq   #0,d6                   ; team 0
                cmpi.w  #11,d5
                blt.s   .is_t1
                moveq   #1,d6                   ; team 1
                subi.w  #12,d5                  ; role 0..9
                bra.s   .got_role
.is_t1:
                subq.w  #1,d5                   ; role 0..9
.got_role:
                ; Bounds safety on role
                tst.w   d5
                bmi.w   .ai_done
                cmpi.w  #9,d5
                bgt.w   .ai_done

                ; Determine attack direction d7: +1 (down toward Y=1088) or -1 (up toward Y=96)
                ; 1st half ($12172==0): T1=+1, T2=-1.  2nd half ($12172!=0): T1=-1, T2=+1.
                moveq   #1,d7
                tst.w   d6
                beq.s   .dir_t1
                neg.w   d7                      ; T2 default -1
.dir_t1:
                tst.w   G_HALF_DIR.l
                beq.s   .dir_ok
                neg.w   d7                      ; swap in 2nd half
.dir_ok:
                ; Look up 4-4-2 role entry (8 bytes: baseX.w, baseY_off.w, pullX.w, pullY.w)
                ; baseY_off is signed offset from midfield Y=592 in attack direction (+ = forward)
                move.w  d5,d0
                lsl.w   #3,d0
                lea     ko2_formation(pc),a0
                adda.w  d0,a0

                ; Compute smooth continuous targetX = baseX + ((ballX - 320) * pullX) >> 8
                move.w  2(a4),d0                ; ballX
                subi.w  #320,d0
                muls.w  4(a0),d0                ; * pullX
                asr.l   #8,d0
                add.w   0(a0),d0                ; + baseX

                ; Compute smooth continuous targetY = 592 + baseY_off*atk_dir + ((ballY - 592) * pullY) >> 8
                move.w  2(a0),d2                ; baseY_off
                tst.w   d7
                bpl.s   .yoff_ok
                neg.w   d2
.yoff_ok:
                addi.w  #592,d2
                move.w  4(a4),d1                ; ballY
                subi.w  #592,d1
                muls.w  6(a0),d1                ; * pullY
                asr.l   #8,d1
                add.w   d2,d1                   ; d1 = targetY

                ; Possession-aware Kick Off 2 tactical shift!
                move.w  G_BALL_OWNER.l,d2
                bmi.s   .ball_loose             ; $ffff = loose ball

                ; Determine owner team (d3: 0=Team1, 1=Team2)
                moveq   #0,d3
                cmpi.w  #11,d2
                blt.s   .own_t1
                moveq   #1,d3
.own_t1:
                cmp.w   d6,d3
                bne.s   .defending

                ; --- MY TEAM HAS BALL (ATTACKING RUNS!) ---
                ; Forwards (roles 8..9): +96, Wingers/Mids (4..7): +68, Defenders (0..3): +32
                moveq   #32,d2
                cmpi.w  #4,d5
                blt.s   .atk_apply
                moveq   #68,d2
                cmpi.w  #8,d5
                blt.s   .atk_apply
                moveq   #96,d2
.atk_apply:
                tst.w   d7
                bpl.s   .atk_add
                neg.w   d2
.atk_add:
                add.w   d2,d1
                bra.s   .clamp_target

.defending:
                ; --- OPPONENT HAS BALL (DROP BACK + ONLY SINGLE CLOSEST CHASER PRESSES!) ---
                move.w  0(a5),d2
                tst.w   d6
                bne.s   .def_c2
                cmp.w   st_t1_chaser(pc),d2
                beq.s   .press_ball
                bra.s   .def_drop
.def_c2:
                cmp.w   st_t2_chaser(pc),d2
                beq.s   .press_ball
.def_drop:
                ; All other defenders/mids hold shape & drop back (-60 px)
                moveq   #-60,d2
                tst.w   d7
                bpl.s   .def_add
                neg.w   d2
.def_add:
                add.w   d2,d1
                bra.s   .clamp_target

.ball_loose:
                ; --- LOOSE BALL: ONLY SINGLE CLOSEST PLAYER PER TEAM SPRINTS TO INTERCEPT! ---
                move.w  0(a5),d2
                tst.w   d6
                bne.s   .bl_c2
                cmp.w   st_t1_chaser(pc),d2
                beq.s   .press_ball
                bra.s   .clamp_target
.bl_c2:
                cmp.w   st_t2_chaser(pc),d2
                bne.s   .clamp_target

.press_ball:
                ; Never crowd the ball during set pieces ($ee08 != 0)!
                tst.w   G_MATCH_STATE.l
                bne.s   .clamp_target
                ; Intercept predicted ball position: (ballX + ballVX*2, ballY + ballVY*2)
                move.w  2(a4),d0
                move.w  8(a4),d2
                add.w   d2,d2
                add.w   d2,d0
                move.w  4(a4),d1
                move.w  10(a4),d2
                add.w   d2,d2
                add.w   d2,d1

.clamp_target:
                ; Clamp targetX to [44..596], targetY to [112..1072]
                cmpi.w  #44,d0
                bge.s   .cx_hi
                move.w  #44,d0
.cx_hi:
                cmpi.w  #596,d0
                ble.s   .cy_lo
                move.w  #596,d0
.cy_lo:
                cmpi.w  #112,d1
                bge.s   .cy_hi
                move.w  #112,d1
.cy_hi:
                cmpi.w  #1072,d1
                ble.s   .do_move
                move.w  #1072,d1

.do_move:
                ; Move player smoothly toward (d0, d1) with tight 10px deadzone via game's $a570
                moveq   #10,d4
                jsr     $a570.l
                ; If stopped, face the ball cleanly
                move.w  8(a5),d0
                or.w    10(a5),d0
                bne.s   .ai_done
                jsr     $b466.l
                move.w  d0,38(a5)               ; $26(a5) = facing
.ai_done:
                movem.l (a7)+,d0-d7/a0-a4
.ai_ret:
                rts

; Kick Off 2-style 4-4-2 Role Anchor Table (10 outfield roles x 8 bytes)
; Format: baseX (44..596), baseY_off (from 592, + = forward), pullX (/256), pullY (/256)
ko2_formation:
                dc.w    120,-260,120,160        ; 0: LB  (Left Back)
                dc.w    250,-280,100,150        ; 1: LCB (Left Center Back)
                dc.w    390,-280,100,150        ; 2: RCB (Right Center Back)
                dc.w    520,-260,120,160        ; 3: RB  (Right Back)
                dc.w    110, -40,140,200        ; 4: LM  (Left Mid / Winger)
                dc.w    255, -70,130,190        ; 5: LCM (Left Center Mid)
                dc.w    385, -70,130,190        ; 6: RCM (Right Center Mid)
                dc.w    530, -40,140,200        ; 7: RM  (Right Mid / Winger)
                dc.w    240,+180,150,180        ; 8: LST (Left Striker)
                dc.w    400,+180,150,180        ; 9: RST (Right Striker)

; =============================================================================
; 10. KICK OFF 2-INSPIRED CPU BALL-CARRIER AI (hook_cpu_joy, replaces $ca8a)
;     Returns virtual joystick byte in d0:
;       bit 0=UP, bit 1=DOWN, bit 2=LEFT, bit 3=RIGHT, bit 7=FIRE (shoot/pass)
; =============================================================================
hook_cpu_joy:
                ; Defer to original $b8c4 during kickoff ($ee18) or freeze timers ($bbd6/$bbd4)
                tst.w   $ee18.l
                bne.s   .cj_orig
                tst.w   $bbd6.l
                bne.s   .cj_orig
                ; CPU FREE KICK ($ee08 == $f and $db24 != 0) -> Kick Off 2-style driven shot/pass!
                cmpi.w  #$f,G_MATCH_STATE.l
                bne.s   .cj_not_fk
                tst.w   $db24.l
                bne.w   .cpu_freekick
                bra.s   .cj_orig
.cj_not_fk:
                tst.w   $db24.l
                bne.s   .cj_orig
                tst.w   G_MATCH_STATE.l
                bne.s   .cj_orig
                tst.w   $bbd4.l
                ble.w   .cj_open
.cj_orig:
                jmp     $b8c4.l

; Kick Off 2-style CPU Free Kick: sprint to ball, then whip shot at goal or crisp lofted pass!
.cpu_freekick:
                movem.l d1-d7/a0-a2/a4,-(a7)
                lea     G_BALL_STRUCT.l,a4
                moveq   #0,d0
                clr.w   (a3)
                ; Check distance from CPU taker to ball
                move.w  2(a4),d1
                sub.w   2(a5),d1
                bpl.s   .fk_dx
                neg.w   d1
.fk_dx:         move.w  4(a4),d2
                sub.w   4(a5),d2
                bpl.s   .fk_dy
                neg.w   d2
.fk_dy:         add.w   d2,d1
                cmpi.w  #14,d1
                ble.s   .fk_kick
                ; Not at ball yet -> run straight to ball!
                move.w  2(a4),d1
                move.w  4(a4),d2
                bsr.w   .steer_to_d1d2
                bra.w   .cj_done

.fk_kick:
                ; At the ball! Determine attack goal Y (d5) and direction (d7)
                move.w  #96,d5
                moveq   #-1,d7
                tst.w   G_HALF_DIR.l
                beq.s   .fk_gok
                move.w  #1088,d5
                moveq   #1,d7
.fk_gok:
                ; Within 280px of goal -> WHIP DRIVEN FREE KICK AT GOAL!
                move.w  4(a4),d2
                sub.w   d5,d2
                bpl.s   .fk_gd
                neg.w   d2
.fk_gd:         cmpi.w  #280,d2
                bgt.s   .fk_pass
                move.w  #320,d1                 ; aim at goal center
                move.w  d5,d2
                moveq   #13,d6                  ; loft vz = 13
                bra.s   .fk_launch

.fk_pass:
                ; Further out -> find most advanced forward CPU teammate (P12..P21)
                lea     G_PLAYERS+12*$3a.l,a0
                moveq   #9,d6
                suba.l  a1,a1
                move.w  #-1,d3                  ; best forward progress
.fk_tmloop:
                cmpa.l  a0,a5
                beq.s   .fk_tmn
                move.w  4(a0),d2
                sub.w   4(a4),d2
                tst.w   d7
                bpl.s   .fk_tmf
                neg.w   d2
.fk_tmf:        cmpi.w  #40,d2
                blt.s   .fk_tmn
                cmpi.w  #280,d2
                bgt.s   .fk_tmn
                cmp.w   d3,d2
                ble.s   .fk_tmn
                move.w  d2,d3
                move.l  a0,a1
.fk_tmn:        lea     $3a(a0),a0
                dbra    d6,.fk_tmloop
                move.l  a1,d1
                beq.s   .fk_long
                move.w  2(a1),d1
                move.w  4(a1),d2
                moveq   #10,d6                  ; crisp lofted pass vz = 10
                bra.s   .fk_launch
.fk_long:
                move.w  #320,d1
                move.w  d5,d2
                moveq   #12,d6

.fk_launch:
                ; Compute normalized velocity toward (d1, d2): scale (dx, dy) to ~48
                sub.w   2(a4),d1                ; dx
                sub.w   4(a4),d2                ; dy
                asr.w   #2,d1
                asr.w   #2,d2
                cmpi.w  #48,d1
                ble.s   .fk_vx1
                moveq   #48,d1
.fk_vx1:        cmpi.w  #-48,d1
                bge.s   .fk_vx2
                moveq   #-48,d1
.fk_vx2:        cmpi.w  #48,d2
                ble.s   .fk_vy1
                moveq   #48,d2
.fk_vy1:        cmpi.w  #-48,d2
                bge.s   .fk_vy2
                moveq   #-48,d2
.fk_vy2:        move.w  d1,8(a4)                ; ball.vx
                move.w  d2,10(a4)               ; ball.vy
                move.w  d6,12(a4)               ; ball.vz
                move.w  #2,6(a4)                ; ball.z = 2
                clr.w   $32(a4)
                ; End free-kick state cleanly & play kick SFX!
                move.w  0(a5),$ee0a.l
                move.w  #$ffff,G_BALL_OWNER.l
                clr.w   G_MATCH_STATE.l
                clr.w   $db24.l
                clr.w   $db26.l
                clr.w   $fbca.l
                move.l  #$2026,$1cb6.l
                move.w  #1,$1cae.l
                bra.w   .cj_done

.cj_open:

                movem.l d1-d7/a0-a2/a4,-(a7)
                lea     G_BALL_STRUCT.l,a4
                moveq   #0,d0                   ; joy result

                ; Check if THIS CPU player owns the ball
                move.w  0(a5),d4                ; player ID
                cmp.w   G_BALL_OWNER.l,d4
                beq.s   .cpu_has_ball

                ; --- CHASE / INTERCEPT BALL ---
                clr.w   (a3)                    ; not holding ball -> clear kick charge
                clr.w   st_cpu_hold
                clr.w   st_cpu_shoot
                move.w  #$ffff,32(a5)           ; $20(a5) = -1
                clr.w   50(a5)                  ; $32(a5) = 0
                move.w  2(a4),d1                ; targetX = ballX + ballVX
                add.w   8(a4),d1
                move.w  4(a4),d2                ; targetY = ballY + ballVY
                add.w   10(a4),d2
                bsr.w   .steer_to_d1d2
                bra.w   .cj_done

.cpu_has_ball:
                move.w  #$ffff,32(a5)
                clr.w   50(a5)
                addq.w  #1,st_cpu_hold

                ; Determine CPU attack goal Y (d5) & direction (d7):
                ; CPU is Team 2 (ID >= 12) normally: 1st half attacks UP (Y=96), 2nd half DOWN (Y=1088)
                move.w  #96,d5                  ; goalY = top goal
                moveq   #-1,d7                  ; atk_dir = -1 (UP)
                tst.w   G_HALF_DIR.l
                beq.s   .cg_ok
                move.w  #1088,d5                ; 2nd half: bottom goal
                moveq   #1,d7
.cg_ok:
                ; --- IF ALREADY CHARGING A KICK ((a3) > 0), RELEASE TO FIRE OR FINISH CHARGE! ---
                tst.w   (a3)
                beq.s   .chk_shoot
                tst.w   st_cpu_shoot
                beq.s   .rel_pass               ; pass charged 1 frame -> RELEASE FIRE NOW!
                cmpi.w  #6,(a3)
                bge.s   .rel_shot               ; shot fully charged (6 frames) -> RELEASE FIRE NOW!
                ; Keep holding Fire while aiming at goal!
                move.w  #320,d1
                move.w  d5,d2
                bsr.w   .steer_to_d1d2
                bset    #7,d0
                bra.w   .cj_done
.rel_shot:
                clr.w   st_cpu_shoot
                clr.w   st_cpu_hold
                move.w  #320,d1
                move.w  d5,d2
                bsr.w   .steer_to_d1d2          ; bit 7 = 0 -> RELEASES FIRE -> SHOOTS!
                bra.w   .cj_done
.rel_pass:
                clr.w   st_cpu_hold
                ; Re-aim at best pass target and release Fire (bit 7 = 0 -> PASSES!)
                bsr.w   .pick_pass_target
                move.l  a1,d1
                beq.s   .rel_shot
                move.w  2(a1),d1
                move.w  4(a1),d2
                bsr.w   .steer_to_d1d2          ; bit 7 = 0 -> RELEASES FIRE -> CRISP PASS!
                bra.w   .cj_done

.chk_shoot:
                ; 1. SHOOTING CHECK: within 250 px of goalY and X in [150..490]
                move.w  4(a5),d2
                sub.w   d5,d2
                bpl.s   .gdist_pos
                neg.w   d2
.gdist_pos:
                cmpi.w  #250,d2
                bgt.s   .chk_pass
                move.w  2(a5),d1
                cmpi.w  #150,d1
                blt.s   .chk_pass
                cmpi.w  #490,d1
                bgt.s   .chk_pass
                ; Start charging power shot at goal!
                move.w  #1,st_cpu_shoot
                move.w  #320,d1
                move.w  d5,d2
                bsr.w   .steer_to_d1d2
                bset    #7,d0                   ; Hold FIRE to charge shot!
                bra.w   .cj_done

.chk_pass:
                ; 2. KICK OFF 2 PASSING: pass if pressured (< 72px) OR dribbled >= 14 frames!
                cmpi.w  #14,st_cpu_hold
                bge.s   .find_pass
                lea     G_PLAYERS+$3a.l,a0      ; P01..P10
                moveq   #9,d6
.opp_loop:
                move.w  2(a0),d1
                sub.w   2(a5),d1
                bpl.s   .oxp
                neg.w   d1
.oxp:
                move.w  4(a0),d2
                sub.w   4(a5),d2
                bpl.s   .oyp
                neg.w   d2
.oyp:
                add.w   d2,d1
                cmpi.w  #72,d1
                blt.s   .find_pass              ; pressured -> look for Kick Off 2 pass!
                lea     $3a(a0),a0
                dbra    d6,.opp_loop

                ; Open space -> dribble briskly toward goal!
                move.w  #320,d1
                move.w  d5,d2
                bsr.w   .steer_to_d1d2
                bra.w   .cj_done

.find_pass:
                bsr.w   .pick_pass_target
                move.l  a1,d1
                beq.s   .dribble_goal           ; no pass target -> dribble!
                clr.w   st_cpu_shoot            ; 1-frame tap pass!
                move.w  2(a1),d1
                move.w  4(a1),d2
                bsr.w   .steer_to_d1d2
                bset    #7,d0                   ; Tap FIRE (next frame releases -> crisp pass!)
                bra.w   .cj_done

.dribble_goal:
                move.w  #320,d1
                move.w  d5,d2
                bsr.w   .steer_to_d1d2
                bra.s   .cj_done

; Subroutine: scan CPU teammates (P12..P21) for best forward/wide pass target -> a1 (or 0)
.pick_pass_target:
                lea     G_PLAYERS+12*$3a.l,a0
                moveq   #9,d6
                suba.l  a1,a1                   ; best teammate ptr
                move.w  #-999,d3                ; best forwardness score (higher = better)
.tm_loop:
                cmpa.l  a0,a5
                beq.s   .tm_next                ; skip self
                ; Forward progress: (tmY - myY) * atk_dir
                move.w  4(a0),d2
                sub.w   4(a5),d2
                tst.w   d7
                bpl.s   .tm_fwd
                neg.w   d2
.tm_fwd:
                cmpi.w  #-10,d2                 ; allow sideways/diagonal & forward passes!
                blt.s   .tm_next
                cmpi.w  #280,d2
                bgt.s   .tm_next
                ; Manhattan distance check: [50..320]
                move.w  2(a0),d1
                sub.w   2(a5),d1
                bpl.s   .tmxp
                neg.w   d1
.tmxp:
                move.w  d2,d4
                bpl.s   .tmyp
                neg.w   d4
.tmyp:          add.w   d4,d1
                cmpi.w  #50,d1
                blt.s   .tm_next                ; too close
                cmpi.w  #320,d1
                bgt.s   .tm_next                ; too far
                ; Prefer teammates further forward (higher d2)
                cmp.w   d3,d2
                ble.s   .tm_next
                move.w  d2,d3
                move.l  a0,a1
.tm_next:
                lea     $3a(a0),a0
                dbra    d6,.tm_loop
                rts

.cj_done:
                move.w  d0,$bc32.l
                movem.l (a7)+,d1-d7/a0-a2/a4
                rts

; Helper: steer player a5 toward (d1=targetX, d2=targetY) -> sets bits 0..3 of d0
.steer_to_d1d2:
                moveq   #0,d0
                move.w  d2,d6
                sub.w   4(a5),d6                ; dy = targetY - myY
                cmpi.w  #-2,d6
                bge.s   .st_dn
                bset    #0,d0                   ; UP
                bra.s   .st_x
.st_dn:
                cmpi.w  #2,d6
                ble.s   .st_x
                bset    #1,d0                   ; DOWN
.st_x:
                move.w  d1,d6
                sub.w   2(a5),d6                ; dx = targetX - myX
                cmpi.w  #-2,d6
                bge.s   .st_rt
                bset    #2,d0                   ; LEFT
                rts
.st_rt:
                cmpi.w  #2,d6
                ble.s   .st_end
                bset    #3,d0                   ; RIGHT
.st_end:
                rts

; =============================================================================
; 11. KICK OFF 2-STYLE 'X'-KEY PITCH RADAR (draw_radar)
;     Draws a crisp 41x65 px mini-pitch radar in the top-left of back_pitch_buf
;     at bufX = 8 + st_back_fine_x, bufY = 6 (so STE HSCROLL locks it at (8,6)!).
;     Input: d1.l = back_pitch_buf ($80000 or $90000). Preserves all regs!
;     Palette indices: 0=Black (lines), 13=Red (Team1), 11=Yellow (Team2), 1=White (Ball)
; =============================================================================
RADAR_Y0        equ     6
RADAR_W         equ     40
RADAR_H         equ     64

draw_radar:
                movem.l d0-d7/a0-a4,-(a7)
                move.l  d1,a4                   ; a4 = pitch buffer base
                moveq   #8,d7
                add.w   st_back_fine_x(pc),d7   ; d7 = radar left X in buffer (8..23)

                ; --- Draw black (col 0) pitch lines: top, bottom, halfway, left, right, penalty boxes ---
                ; Top border (y = 6, x = d7..d7+40)
                move.w  d7,d0
                moveq   #RADAR_Y0,d1
                moveq   #RADAR_W,d2
                bsr.w   .rad_hline
                ; Bottom border (y = 70)
                move.w  d7,d0
                moveq   #RADAR_Y0+RADAR_H,d1
                moveq   #RADAR_W,d2
                bsr.w   .rad_hline
                ; Halfway line (y = 38)
                move.w  d7,d0
                moveq   #RADAR_Y0+32,d1
                moveq   #RADAR_W,d2
                bsr.w   .rad_hline
                ; Top penalty box bottom (y = 16, x = d7+10..d7+30)
                move.w  d7,d0
                addi.w  #10,d0
                moveq   #RADAR_Y0+10,d1
                moveq   #20,d2
                bsr.w   .rad_hline
                ; Bottom penalty box top (y = 60, x = d7+10..d7+30)
                move.w  d7,d0
                addi.w  #10,d0
                moveq   #RADAR_Y0+54,d1
                moveq   #20,d2
                bsr.w   .rad_hline

                ; Left & Right vertical touchlines (y = 6..70)
                move.w  d7,d0
                moveq   #RADAR_Y0,d1
                moveq   #RADAR_H,d2
                bsr.w   .rad_vline
                move.w  d7,d0
                addi.w  #RADAR_W,d0
                moveq   #RADAR_Y0,d1
                moveq   #RADAR_H,d2
                bsr.w   .rad_vline
                ; Top & bottom penalty box vertical sides
                move.w  d7,d0
                addi.w  #10,d0
                moveq   #RADAR_Y0,d1
                moveq   #10,d2
                bsr.w   .rad_vline
                move.w  d7,d0
                addi.w  #30,d0
                moveq   #RADAR_Y0,d1
                moveq   #10,d2
                bsr.w   .rad_vline
                move.w  d7,d0
                addi.w  #10,d0
                moveq   #RADAR_Y0+54,d1
                moveq   #10,d2
                bsr.w   .rad_vline
                move.w  d7,d0
                addi.w  #30,d0
                moveq   #RADAR_Y0+54,d1
                moveq   #10,d2
                bsr.w   .rad_vline

                ; --- Draw all 22 players as 2x1 pips (inlined, zero mulu/bsr/movem -> 4x faster!) ---
                lea     G_PLAYERS.l,a2
                moveq   #21,d6                  ; 22 players (0..21)
.rad_ploop:
                move.w  2(a2),d0                ; worldX (0..640)
                lsr.w   #4,d0                   ; 0..39
                cmpi.w  #RADAR_W-2,d0
                ble.s   .rx_ok
                moveq   #RADAR_W-2,d0
.rx_ok:
                add.w   d7,d0                   ; + radar X0

                move.w  4(a2),d1                ; worldY (96..1120)
                subi.w  #64,d1
                bpl.s   .ry_pos
                moveq   #0,d1
.ry_pos:
                lsr.w   #4,d1                   ; 0..63
                cmpi.w  #RADAR_H-2,d1
                ble.s   .ry_ok
                moveq   #RADAR_H-2,d1
.ry_ok:
                addq.w  #RADAR_Y0,d1
                ; Fast y * 168 = (y << 7) + (y << 5) + (y << 3) (zero mulu!)
                lsl.w   #3,d1                   ; y * 8
                move.w  d1,d2
                lsl.w   #2,d2                   ; y * 32
                add.w   d2,d1                   ; y * 40
                lsl.w   #2,d2                   ; y * 128
                add.w   d2,d1                   ; y * 168
                lea     (a4,d1.w),a0
                move.w  d0,d4
                lsr.w   #4,d4
                lsl.w   #3,d4
                adda.w  d4,a0
                andi.w  #15,d0
                move.w  #$c000,d5
                lsr.w   d0,d5                   ; d5 = set mask (2px wide)
                move.w  d5,d4
                not.w   d4                      ; d4 = clear mask

                cmpi.w  #11,0(a2)
                bge.s   .rad_t2
                ; Team 1 = Red (col 13 = %1101: p0=1, p1=0, p2=1, p3=1)
                or.w    d5,(a0)
                and.w   d4,2(a0)
                or.w    d5,4(a0)
                or.w    d5,6(a0)
                bra.s   .rad_pnext
.rad_t2:
                ; Team 2 = Yellow (col 11 = %1011: p0=1, p1=1, p2=0, p3=1)
                or.w    d5,(a0)
                or.w    d5,2(a0)
                and.w   d4,4(a0)
                or.w    d5,6(a0)
.rad_pnext:
                lea     $3a(a2),a2
                dbra    d6,.rad_ploop

                ; --- Draw Ball as bright White (col 1 = %0001) 2x1 pip ---
                lea     G_BALL_STRUCT.l,a2
                move.w  2(a2),d0
                lsr.w   #4,d0
                cmpi.w  #RADAR_W-2,d0
                ble.s   .bx_ok
                moveq   #RADAR_W-2,d0
.bx_ok:
                add.w   d7,d0
                move.w  4(a2),d1
                subi.w  #64,d1
                bpl.s   .by_pos
                moveq   #0,d1
.by_pos:
                lsr.w   #4,d1
                cmpi.w  #RADAR_H-2,d1
                ble.s   .by_ok
                moveq   #RADAR_H-2,d1
.by_ok:
                addq.w  #RADAR_Y0,d1
                lsl.w   #3,d1
                move.w  d1,d2
                lsl.w   #2,d2
                add.w   d2,d1
                lsl.w   #2,d2
                add.w   d2,d1
                lea     (a4,d1.w),a0
                move.w  d0,d4
                lsr.w   #4,d4
                lsl.w   #3,d4
                adda.w  d4,a0
                andi.w  #15,d0
                move.w  #$c000,d5
                lsr.w   d0,d5
                move.w  d5,d4
                not.w   d4
                or.w    d5,(a0)
                and.w   d4,2(a0)
                and.w   d4,4(a0)
                and.w   d4,6(a0)

                movem.l (a7)+,d0-d7/a0-a4
                rts

; Fast word-mask horizontal black line at (d0=x0, d1=y, d2=len) — 10x faster than per-pixel!
.rad_hline:
                movem.l d0-d6/a0,-(a7)
                mulu.w  #PITCH_STRIDE,d1
                lea     (a4,d1.l),a0
                move.w  d0,d3
                add.w   d2,d3                   ; d3 = x1 (inclusive)
                move.w  d0,d4
                lsr.w   #4,d4                   ; word0 = x0 >> 4
                move.w  d3,d5
                lsr.w   #4,d5                   ; word1 = x1 >> 4
                move.w  d4,d6
                lsl.w   #3,d6
                adda.w  d6,a0                   ; a0 -> first word group

                ; Left mask: clear bits [15-(x0&15) .. 0] -> keep bits [15 .. 16-(x0&15)]
                andi.w  #15,d0
                move.w  #$ffff,d1
                lsr.w   d0,d1                   ; 1s in drawn pixels
                not.w   d1                      ; 0s in drawn pixels (AND mask)

                ; Right mask: clear bits [15 .. 15-(x1&15)] -> keep bits [14-(x1&15) .. 0]
                andi.w  #15,d3
                move.w  #$7fff,d2
                lsr.w   d3,d2                   ; 1s to the right of x1 (AND mask)

                cmp.w   d4,d5
                bne.s   .hl_multi
                ; Single word! Combined AND mask = d1 | d2
                or.w    d2,d1
                and.w   d1,(a0)
                and.w   d1,2(a0)
                and.w   d1,4(a0)
                and.w   d1,6(a0)
                bra.s   .hl_done
.hl_multi:
                ; First word
                and.w   d1,(a0)+
                and.w   d1,(a0)+
                and.w   d1,(a0)+
                and.w   d1,(a0)+
                addq.w  #1,d4
                ; Middle full-black words
                bra.s   .hl_mchk
.hl_mloop:
                clr.l   (a0)+
                clr.l   (a0)+
                addq.w  #1,d4
.hl_mchk:       cmp.w   d5,d4
                blt.s   .hl_mloop
                ; Last word
                and.w   d2,(a0)+
                and.w   d2,(a0)+
                and.w   d2,(a0)+
                and.w   d2,(a0)+
.hl_done:
                movem.l (a7)+,d0-d6/a0
                rts

; Fast vertical black line at (d0=x, d1=y, d2=len) using 2x and.l per row!
.rad_vline:
                movem.l d0-d5/a0,-(a7)
                mulu.w  #PITCH_STRIDE,d1
                lea     (a4,d1.l),a0
                move.w  d0,d3
                lsr.w   #4,d3
                lsl.w   #3,d3
                adda.w  d3,a0
                moveq   #15,d4
                sub.w   d0,d4
                andi.w  #15,d4
                moveq   #0,d5
                bset    d4,d5
                not.w   d5
                move.w  d5,d4
                swap    d5
                move.w  d4,d5                   ; d5.l = mask replicated in high & low words!
                lsr.w   #1,d2                   ; step every 2px (2x faster!)
.vl_loop:
                and.l   d5,(a0)
                and.l   d5,4(a0)
                lea     PITCH_STRIDE*2(a0),a0
                dbra    d2,.vl_loop
                movem.l (a7)+,d0-d5/a0
                rts

; =============================================================================
; 12. DIRTY-CHECKED HUD POWER BARS (hook_hud_bars, replaces $d2d4 bsr $cd52)
;     Skips redrawing the 4 power bars ($10cec..$10cf3) when unchanged (saves ~13k cyc!)
; =============================================================================
hook_hud_bars:
                move.l  $10cec.l,d0
                cmp.l   st_hud_p12(pc),d0
                bne.s   .hb_changed
                move.l  $10cf0.l,d0
                cmp.l   st_hud_p34(pc),d0
                bne.s   .hb_changed
                tst.w   st_hud_dirty
                beq.s   .hb_skip
                subq.w  #1,st_hud_dirty
                movea.l G_SCR_BACK.l,a0
                jmp     $cd58.l
.hb_changed:
                move.l  $10cec.l,st_hud_p12
                move.l  $10cf0.l,st_hud_p34
                move.w  #2,st_hud_dirty         ; update both double-buffers
                movea.l G_SCR_BACK.l,a0
                jmp     $cd58.l
.hb_skip:
                rts

; =============================================================================
; 13. 1P/2P/3P/4P PLAYER INDICATOR BUBBLE (hook_num_bubble, replaces $8ed0)
;     Draws the active-player '1'/'2'/'3'/'4' bubble above the player's head
;     into our 336x168 pitch buffer via STE Blitter!
;     Inputs: d0=bufX, d1=screenY, d2=icon index (0..3)
; =============================================================================
hook_num_bubble:
                lea     $43e48.l,a1             ; Icon sprite table ($46 bytes = 7 rows x 10 B each)
                mulu.w  #$46,d2
                adda.l  d2,a1
                moveq   #6,d2                   ; 7 rows (dbra count = 6)
                bra.w   hook_sprite_draw

; =============================================================================
; 14. FAST FADE / TRANSITION WAIT (hook_fast_wait, replaces $230c)
;     Clamps slow 3..6-VBL fade step waits down to 1 VBL (6x snappier menus!)
; =============================================================================
hook_fast_wait:
                cmpi.w  #1,d0
                ble.s   .fw_go
                cmpi.w  #8,d0
                bgt.s   .fw_long
                moveq   #1,d0                   ; 3..6 VBL fade steps -> 1 VBL!
                bra.s   .fw_go
.fw_long:
                lsr.w   #1,d0                   ; Long waits halved
.fw_go:
                add.w   $1213a.l,d0
.fw_wait:
                cmp.w   $1213a.l,d0
                bne.s   .fw_wait
                rts

; =============================================================================
; 15. KICK OFF 2 SLIDING TACKLE + JUMPING/HEADING + REAL REFEREE FOUL RULES
;     Called from $c6e4 when a player presses FIRE without the ball!
;     - Ball in air (ball.z > 6) & dist < 95 px -> JUMP + HEADER (with ground shadow!)
;     - Ball on ground (ball.z <= 6) & dist < 80 px -> CUSTOM PIXEL-ART SLIDE TACKLE!
;       * Wins ball cleanly if ball hit first (+-18px)
;       * Referee foul ($d824) ONLY if tackling from behind or hitting player w/o ball!
;     - Far from ball -> switch to nearest teammate ($c6ec).
; =============================================================================
hook_fire_noball:
                cmpi.w  #1,$24(a5)
                bne.w   .fn_switch
                tst.w   G_MATCH_STATE.l
                bne.w   .fn_switch
                tst.w   st_tackle_tmr
                bne.w   .fn_ret                 ; already sliding!
                tst.w   st_jump_tmr
                bne.w   .fn_ret                 ; already jumping!

                ; If my selected player is NOT the closest teammate to the ball, Fire selects the closest!
                move.w  0(a5),d0
                cmp.w   st_t1_chaser(pc),d0
                beq.s   .fn_is_closest
                move.w  st_t1_chaser(pc),d0
                bmi.w   .fn_switch
                clr.w   $24(a5)                 ; release current player to AI
                move.w  d0,$ede0.l              ; select closest player ID
                jsr     $cc0e.l                 ; a5 -> new player struct
                move.w  #1,$24(a5)              ; assign 1P control
                move.w  #$ffff,$20(a5)
                rts
.fn_is_closest:

                ; Compute Manhattan distance to ball
                lea     G_BALL_STRUCT.l,a0
                move.w  2(a0),d0
                sub.w   2(a5),d0
                bpl.s   .tdx
                neg.w   d0
.tdx:           move.w  4(a0),d1
                sub.w   4(a5),d1
                bpl.s   .tdy
                neg.w   d1
.tdy:           add.w   d1,d0

                ; --- CHECK JUMP / HEADER (ball in air: ball.z > 6) ---
                cmpi.w  #6,6(a0)
                ble.s   .chk_slide
                cmpi.w  #95,d0
                bge.w   .fn_switch
                move.w  0(a5),st_jump_id
                move.w  #6,st_jump_vz           ; upward jump impulse!
                move.w  #14,st_jump_tmr
                rts

.chk_slide:
                ; Only slide tackle if the opponent (ID >= 11) had the ball last!
                ; Prevents accidental slide tackles when tapping Fire after your own pass!
                cmpi.w  #11,$ee0a.l
                blt.w   .fn_ret
                cmpi.w  #80,d0
                bge.w   .fn_switch

                ; --- LAUNCH 12-FRAME CUSTOM-SPRITE SLIDE TACKLE! ---
                move.w  0(a5),st_tackle_id
                move.w  #12,st_tackle_tmr
                clr.w   st_tackle_won

                ; Direction = $1c(a5) (0..7); look up sign pair from $10998
                move.w  $1c(a5),d0
                andi.w  #7,d0
                move.w  d0,st_tackle_dir
                move.w  d0,d1
                add.w   d1,d1
                lea     $10998.l,a0
                move.b  0(a0,d1.w),d2           ; sx (-1, 0, +1)
                ext.w   d2
                muls.w  #52,d2
                move.w  d2,st_tackle_vx
                move.w  d2,8(a5)
                move.b  1(a0,d1.w),d2           ; sy (-1, 0, +1)
                ext.w   d2
                muls.w  #52,d2
                move.w  d2,st_tackle_vy
                move.w  d2,10(a5)

                ; Map 8-way dir (0=U,1=UR,2=R,3=DR,4=D,5=DL,6=L,7=UL) -> custom pose (0=R,1=L,2=D,3=U)
                lea     slide_dir_to_pose(pc),a0
                moveq   #0,d1
                move.b  0(a0,d0.w),d1
                move.w  d1,st_tackle_pose
                clr.w   $32(a5)
.fn_ret:
                rts
.fn_switch:
                move.w  $24(a5),d0              ; Execute displaced $c6e4..$c6eb instructions
                cmp.w   #1,d0
                jmp     $c6ec.l                 ; Far from ball -> switch to nearest teammate!

; Clean sprite-queue override at $bd36 (never mutates player's $2a/$26/$28!)
hook_player_spr:
                tst.w   st_tackle_tmr
                beq.s   .hps_norm
                move.w  0(a5),d3
                cmp.w   st_tackle_id(pc),d3
                bne.s   .hps_norm
                ; Return our custom 16x30 slide tackle sprite directly with 0 offset!
                move.w  st_tackle_pose(pc),d3
                lsl.w   #2,d3
                lea     slide_ptr_table(pc),a0
                movea.l (a0,d3.w),a0
                moveq   #29,d3                  ; 30 rows (d3+1 = 30)
                rts
.hps_norm:
                ; Prevent players from ever running backwards: sync facing $26(a5) to move dir $1c(a5) in open play!
                tst.w   G_MATCH_STATE.l
                bne.s   .hps_use26
                move.w  8(a5),d3
                or.w    10(a5),d3
                beq.s   .hps_use26
                move.w  $1c(a5),d3
                andi.w  #7,d3
                move.w  d3,$26(a5)
.hps_use26:
                move.w  $26(a5),d3
                lsl.w   #2,d3
                movea.l $2a(a5),a0
                movea.l (a0,d3.w),a0
                move.w  $28(a5),d3
                lea.l   (a0,d3.w),a0
                move.w  $2e(a5),d3
                rts

slide_dir_to_pose:
                dc.b    3,0,0,0,2,1,1,1         ; 0=U->3, 1..3=R->0, 4=D->2, 5..7=L->1
                even
slide_ptr_table:
                dc.l    slide_spr_right
                dc.l    slide_spr_left
                dc.l    slide_spr_down
                dc.l    slide_spr_up

; Per-frame slide tackle physics, ball-win & real foul rules!
tick_slide_tackle:
                tst.w   st_tackle_tmr
                beq.w   .ts_done
                movem.l d0-d5/a0-a2,-(a7)
                subq.w  #1,st_tackle_tmr
                move.w  st_tackle_id(pc),d0
                mulu.w  #$3a,d0
                lea     G_PLAYERS.l,a0
                adda.l  d0,a0

                ; Apply decaying slide velocity
                move.w  st_tackle_vx(pc),d1
                move.w  st_tackle_vy(pc),d2
                move.w  d1,8(a0)
                move.w  d2,10(a0)
                move.w  st_tackle_tmr(pc),d3
                btst    #0,d3
                bne.s   .ts_chk_hit
                asr.w   #1,d1
                add.w   st_tackle_vx(pc),d1
                asr.w   #1,d1
                move.w  d1,st_tackle_vx
                asr.w   #1,d2
                add.w   st_tackle_vy(pc),d2
                asr.w   #1,d2
                move.w  d2,st_tackle_vy

.ts_chk_hit:
                tst.w   st_tackle_won
                bne.w   .ts_chk_end

                ; 1. Check BALL hit first (+-18px, ball.z <= 10)
                lea     G_BALL_STRUCT.l,a1
                cmpi.w  #10,6(a1)
                bgt.s   .ts_chk_opp
                move.w  2(a1),d0
                sub.w   2(a0),d0
                bpl.s   .tbx
                neg.w   d0
.tbx:           cmpi.w  #18,d0
                bgt.s   .ts_chk_opp
                move.w  4(a1),d0
                sub.w   4(a0),d0
                bpl.s   .tby
                neg.w   d0
.tby:           cmpi.w  #18,d0
                bgt.s   .ts_chk_opp

                ; Check if tackling the ball owner FROM BEHIND (same facing direction!)
                move.w  G_BALL_OWNER.l,d4
                cmpi.w  #11,d4
                blt.s   .ts_clean_win           ; loose or teammate -> clean!
                mulu.w  #$3a,d4
                lea     G_PLAYERS.l,a2
                adda.l  d4,a2
                move.w  $1c(a2),d4
                andi.w  #7,d4
                cmp.w   st_tackle_dir(pc),d4    ; sliding in exact same direction as ball owner = FROM BEHIND!
                beq.s   .ts_foul

.ts_clean_win:
                ; CLEAN TACKLE! Win the ball and knock it forward!
                move.w  #1,st_tackle_won
                move.w  #$ffff,G_BALL_OWNER.l
                move.w  st_tackle_vx(pc),d0
                add.w   d0,d0
                move.w  d0,8(a1)
                move.w  st_tackle_vy(pc),d0
                add.w   d0,d0
                move.w  d0,10(a1)
                move.w  #2,6(a1)
                bra.s   .ts_chk_end

.ts_chk_opp:
                ; 2. Didn't get the ball -> check if we clipped an opponent (P12..P21, +-12px) = FOUL!
                lea     G_PLAYERS+12*$3a.l,a2
                moveq   #9,d5
.opp_foul_loop:
                move.w  2(a2),d0
                sub.w   2(a0),d0
                bpl.s   .ofx
                neg.w   d0
.ofx:           cmpi.w  #12,d0
                bgt.s   .of_next
                move.w  4(a2),d0
                sub.w   4(a0),d0
                bpl.s   .ofy
                neg.w   d0
.ofy:           cmpi.w  #12,d0
                ble.s   .ts_foul
.of_next:
                lea     $3a(a2),a2
                dbra    d5,.opp_foul_loop
                bra.s   .ts_chk_end

.ts_foul:
                move.w  st_tackle_id(pc),$ee0a.l ; record Team 1 as fouler so CPU gets free kick!
                clr.w   st_tackle_tmr
                jsr     $d824.l
                bra.s   .ts_exit

.ts_chk_end:
                tst.w   st_tackle_tmr
                bne.s   .ts_exit
                clr.w   8(a0)
                clr.w   10(a0)
.ts_exit:
                movem.l (a7)+,d0-d5/a0-a2
.ts_done:
                rts

; =============================================================================
; 16. JUMPING / HEADING PHYSICS + GROUND SHADOW (tick_jump + draw_jump_shadow)
; =============================================================================
tick_jump:
                tst.w   st_jump_tmr
                beq.w   .tj_done
                movem.l d0-d3/a0-a2,-(a7)
                subq.w  #1,st_jump_tmr
                move.w  st_jump_id(pc),d0
                mulu.w  #$3a,d0
                lea     G_PLAYERS.l,a0
                adda.l  d0,a0

                ; Parabolic Z arc: player.z += vz; vz -= 1
                move.w  6(a0),d1
                add.w   st_jump_vz(pc),d1
                bpl.s   .tj_air
                moveq   #0,d1
                clr.w   st_jump_tmr             ; landed!
.tj_air:
                move.w  d1,6(a0)
                subq.w  #1,st_jump_vz

                ; Check HEADER contact with airborne ball!
                lea     G_BALL_STRUCT.l,a1
                move.w  2(a1),d0
                sub.w   2(a0),d0
                bpl.s   .hdx
                neg.w   d0
.hdx:           cmpi.w  #16,d0
                bgt.s   .tj_exit
                move.w  4(a1),d0
                sub.w   4(a0),d0
                bpl.s   .hdy
                neg.w   d0
.hdy:           cmpi.w  #16,d0
                bgt.s   .tj_exit
                move.w  6(a1),d0
                sub.w   d1,d0
                bpl.s   .hdz
                neg.w   d0
.hdz:           cmpi.w  #16,d0
                bgt.s   .tj_exit

                ; HEADER!! Knock ball crisply in facing direction!
                move.w  #$ffff,G_BALL_OWNER.l
                move.w  $1c(a0),d0
                andi.w  #7,d0
                add.w   d0,d0
                lea     $10998.l,a2
                move.b  0(a2,d0.w),d2
                ext.w   d2
                muls.w  #44,d2
                move.w  d2,8(a1)
                move.b  1(a2,d0.w),d2
                ext.w   d2
                muls.w  #44,d2
                move.w  d2,10(a1)
                move.w  #4,12(a1)               ; slight upward header pop
.tj_exit:
                movem.l (a7)+,d0-d3/a0-a2
.tj_done:
                rts

; Draw semi-transparent (50% dithered dark-grey col 3) 12x5 ellipse shadow beneath jumping player!
draw_jump_shadow:
                movem.l d0-d6/a0-a2,-(a7)
                move.l  d1,a1                   ; back pitch buffer
                move.w  st_jump_id(pc),d0
                mulu.w  #$3a,d0
                lea     G_PLAYERS.l,a0
                adda.l  d0,a0
                ; Ground position in pitch buffer: bufX = player.x - coarse_x + 2, scrY = player.y - camY - 5
                move.w  G_CAM_X.l,d2
                andi.w  #$fff0,d2
                move.w  2(a0),d0
                sub.w   d2,d0                   ; bufX
                addq.w  #2,d0
                cmpi.w  #2,d0
                blt.s   .js_done
                cmpi.w  #320,d0
                bgt.s   .js_done
                move.w  4(a0),d1
                sub.w   G_CAM_Y.l,d1
                subq.w  #5,d1
                cmpi.w  #2,d1
                blt.s   .js_done
                cmpi.w  #PITCH_HEIGHT-6,d1
                bgt.s   .js_done

                mulu.w  #PITCH_STRIDE,d1
                lea     (a1,d1.l),a0
                move.w  d0,d2
                lsr.w   #4,d2
                lsl.w   #3,d2
                adda.w  d2,a0
                andi.w  #15,d0                  ; d0 = bit shift (0..15)
                lea     jump_shadow_rows(pc),a2
                moveq   #4,d4                   ; 5 scanlines (12x5 dithered ellipse)
.js_row:
                moveq   #0,d3
                move.w  (a2)+,d3
                swap    d3                      ; mask in upper 16 bits
                lsr.l   d0,d3                   ; hi word = word0 mask, lo word = word1 mask
                ; Color 3 (0x222 dark grey) = planes 0 & 1 SET, planes 2 & 3 CLEAR -> 50% dithered semi-transparent!
                move.w  d3,d5                   ; d5 = word1 set mask
                move.w  d5,d6
                not.w   d6                      ; d6 = word1 clear mask
                swap    d3                      ; d3.w = word0 set mask
                move.w  d3,d2
                not.w   d2                      ; d2.w = word0 clear mask
                or.w    d3,(a0)
                or.w    d3,2(a0)
                and.w   d2,4(a0)
                and.w   d2,6(a0)
                or.w    d5,8(a0)
                or.w    d5,10(a0)
                and.w   d6,12(a0)
                and.w   d6,14(a0)
                lea     PITCH_STRIDE(a0),a0
                dbra    d4,.js_row
.js_done:
                movem.l (a7)+,d0-d6/a0-a2
                rts

jump_shadow_rows:
                dc.w    $0a80                   ; row 0: width 6, checkerboard even
                dc.w    $5540                   ; row 1: width 10, checkerboard odd
                dc.w    $aaa0                   ; row 2: width 12, checkerboard even
                dc.w    $5540                   ; row 3: width 10, checkerboard odd
                dc.w    $0a80                   ; row 4: width 6, checkerboard even

; =============================================================================
; 17. SMART PASS / REVERSE-CHIP / BALANCED SHOT (hook_kick, replaces $cb64)
;     Inputs: a5 = kicker struct, a3 = &charge (1..24), d2.w = joystick bits
;     - Tap Fire (charge < 6):
;         * Default: crisp ON-THE-GROUND pass (vz=0, speed 44) aimed directly at
;           the nearest teammate in your facing cone!
;         * Suddenly reverse stick (dot(facing, joy) < 0): CHIP/LOB (vz=18)!
;     - Hold Fire (charge >= 6):
;         * Power shot (speed 66 / diag 52) with sensible, uniform height (vz=10)
;           going UP, DOWN, LEFT, or RIGHT (or high chip vz=20 if reversed)!
; =============================================================================
hook_kick:
                movem.l d0-d7/a0-a2/a4,-(a7)
                lea     G_BALL_STRUCT.l,a4
                move.w  #$ffff,$20(a5)
                move.w  #$ffff,G_BALL_OWNER.l
                move.w  0(a5),$ee0a.l
                move.w  (a3),d7                 ; d7 = charge (1..24)
                clr.w   (a3)

                ; Get facing unit vector (fx=d3, fy=d4) from $10998[dir*2]
                move.w  $1c(a5),d0
                andi.w  #7,d0
                add.w   d0,d0
                lea     $10998.l,a0
                move.b  0(a0,d0.w),d3
                ext.w   d3                      ; d3 = fx (-1, 0, +1)
                move.b  1(a0,d0.w),d4
                ext.w   d4                      ; d4 = fy (-1, 0, +1)

                ; Compute joystick unit vector (jx=d5, jy=d6) from d2 (0=U,1=D,2=L,3=R)
                moveq   #0,d5
                btst    #2,d2
                beq.s   .hk_jr
                moveq   #-1,d5
.hk_jr:         btst    #3,d2
                beq.s   .hk_ju
                moveq   #1,d5
.hk_ju:         moveq   #0,d6
                btst    #0,d2
                beq.s   .hk_jd
                moveq   #-1,d6
.hk_jd:         btst    #1,d2
                beq.s   .hk_dot
                moveq   #1,d6
.hk_dot:
                ; Detect sudden reverse direction: dot = fx*jx + fy*jy < 0 -> chip flag in d2!
                move.w  d3,d0
                muls.w  d5,d0
                move.w  d4,d1
                muls.w  d6,d1
                add.w   d1,d0
                slt     d2                      ; d2.b = $ff if reversed (CHIP!), 0 otherwise

                ; Charged shot (charge >= 6) vs Tap pass (charge < 6)?
                cmpi.w  #6,d7
                bge.w   .hk_shot

                ; --- TAP FIRE: SMART GROUND PASS TO NEAREST TEAMMATE IN FACING DIRECTION ---
                lea     G_PLAYERS+$3a.l,a0      ; Team 1: P01..P10
                cmpi.w  #11,0(a5)
                blt.s   .hk_scan
                lea     G_PLAYERS+12*$3a.l,a0   ; Team 2: P12..P21
.hk_scan:
                moveq   #9,d6
                suba.l  a1,a1                   ; best teammate ptr
                move.w  #999,d7                 ; best distance
.hk_loop:
                cmpa.l  a0,a5
                beq.s   .hk_next                ; skip self
                move.w  2(a0),d0
                sub.w   2(a5),d0                ; dx
                move.w  4(a0),d1
                sub.w   4(a5),d1                ; dy
                ; Must be in facing direction: dot = dx*fx + dy*fy > 0
                move.w  d0,d5
                muls.w  d3,d5
                move.w  d1,-(a7)
                muls.w  d4,d1
                add.w   d1,d5
                move.w  (a7)+,d1
                ble.s   .hk_next                ; behind or perpendicular -> skip
                ; Manhattan distance in [28 .. 420]
                tst.w   d0
                bpl.s   .hk_ax
                neg.w   d0
.hk_ax:         tst.w   d1
                bpl.s   .hk_ay
                neg.w   d1
.hk_ay:         add.w   d1,d0
                cmpi.w  #28,d0
                blt.s   .hk_next
                cmpi.w  #420,d0
                bgt.s   .hk_next
                cmp.w   d7,d0
                bge.s   .hk_next
                move.w  d0,d7
                move.l  a0,a1
.hk_next:
                lea     $3a(a0),a0
                dbra    d6,.hk_loop

                move.l  a1,d0
                beq.s   .hk_pass_dir            ; no teammate in cone -> pass along facing!

                ; Aim distance-scaled ground pass directly at teammate (a1)!
                ; Short (<90px): 30, Medium (90..180px): 38, Long (>180px): 46
                moveq   #30,d3
                cmpi.w  #90,d7
                blt.s   .hk_pspd
                moveq   #38,d3
                cmpi.w  #180,d7
                blt.s   .hk_pspd
                moveq   #46,d3
.hk_pspd:
                move.w  2(a1),d0
                sub.w   2(a5),d0                ; dx
                move.w  4(a1),d1
                sub.w   4(a5),d1                ; dy
                move.w  d0,d5
                bpl.s   .hk_m1
                neg.w   d5
.hk_m1:         move.w  d1,d6
                bpl.s   .hk_m2
                neg.w   d6
.hk_m2:         cmp.w   d6,d5
                bge.s   .hk_m3
                move.w  d6,d5                   ; d5 = max(|dx|, |dy|) >= 14
.hk_m3:         muls.w  d3,d0
                divs.w  d5,d0                   ; vx = dx * speed / max
                muls.w  d3,d1
                divs.w  d5,d1                   ; vy = dy * speed / max
                bra.s   .hk_pass_vz

.hk_pass_dir:
                ; No teammate in facing direction -> controlled short knock-on (28 straight / 22 diag)
                move.w  d3,d0
                muls.w  #28,d0
                move.w  d4,d1
                muls.w  #28,d1
                tst.w   d3
                beq.s   .hk_pass_vz
                tst.w   d4
                beq.s   .hk_pass_vz
                move.w  d3,d0
                muls.w  #22,d0
                move.w  d4,d1
                muls.w  #22,d1

.hk_pass_vz:
                moveq   #0,d5                   ; ON THE GROUND by default!
                tst.b   d2
                beq.s   .hk_apply
                moveq   #18,d5                  ; Reversed stick -> crisp CHIP!
                bra.s   .hk_apply

.hk_shot:
                ; --- CHARGED SHOT (charge >= 6): POWERFUL & SENSIBLE HEIGHT IN ALL DIRECTIONS! ---
                moveq   #66,d6                  ; straight power shot speed
                tst.w   d3
                beq.s   .hk_svec
                tst.w   d4
                beq.s   .hk_svec
                moveq   #52,d6                  ; diagonal power shot speed
.hk_svec:
                move.w  d3,d0
                muls.w  d6,d0
                move.w  d4,d1
                muls.w  d6,d1
                moveq   #10,d5                  ; sensible shot height UP, DOWN, LEFT, or RIGHT!
                tst.b   d2
                beq.s   .hk_apply
                moveq   #20,d5                  ; Reversed stick -> high lofted chip/cross!

.hk_apply:
                move.w  d0,8(a4)                ; ball.vx
                move.w  d1,10(a4)               ; ball.vy
                move.w  d5,12(a4)               ; ball.vz
                clr.w   $ee18.l
                clr.w   $bbd6.l
                move.l  #$2026,$1cb6.l          ; kick SFX
                move.w  #1,$1cae.l
                movem.l (a7)+,d0-d7/a0-a2/a4
                rts

; =============================================================================
; 18. KICK OFF 2-STYLE GOALKEEPER AI (hook_gk_ai, replaces $96b0)
;     Called per goalkeeper with a5 = P00 ($f0b8) or P11 ($f336).
;     - Generous +-12px catch hitbox (ball.z < 28) -> clean saves!
;     - Continuous lateral tracking & angle-narrowing depth every frame
;     - Predictive 5px/frame shot-stopping lunge on incoming shots
; =============================================================================
hook_gk_ai:
                movem.l d0-d6/a0/a4,-(a7)
                lea     G_BALL_STRUCT.l,a4

                ; 1. CATCH CHECK: ball within +-12px & ball.z < 28 (and not held by teammate)?
                cmpi.w  #28,6(a4)
                bge.s   .gk_move
                move.w  2(a4),d0
                sub.w   2(a5),d0
                bpl.s   .gk_cdx
                neg.w   d0
.gk_cdx:        cmpi.w  #12,d0
                bgt.s   .gk_move
                move.w  4(a4),d0
                sub.w   4(a5),d0
                bpl.s   .gk_cdy
                neg.w   d0
.gk_cdy:        cmpi.w  #12,d0
                bgt.s   .gk_move
                ; Caught the ball! Trigger game's clean GK catch & punt routine ($9b28)!
                move.w  #8,$32(a5)
                clr.w   $38(a5)
                move.w  #$d,G_MATCH_STATE.l
                st.b    $32(a4)
                movem.l (a7)+,d0-d6/a0/a4
                jmp     $9b28.l

.gk_move:
                ; 2. Determine which goal this GK defends: top (Y=112, dir=+1) or bottom (Y=1072, dir=-1)
                ;    1st half ($12172==0): P00 defends TOP (112), P11 defends BOTTOM (1072)
                ;    2nd half ($12172!=0): swapped!
                moveq   #0,d6                   ; 0 = top goal, 1 = bottom goal
                tst.w   0(a5)                   ; P00?
                beq.s   .gk_p0
                moveq   #1,d6                   ; P11 default bottom
.gk_p0:         tst.w   G_HALF_DIR.l
                beq.s   .gk_gok
                eori.w  #1,d6                   ; swap in 2nd half
.gk_gok:
                move.w  #112,d1                 ; goalY (top)
                moveq   #1,d5                   ; out_dir = +1 (down into box)
                tst.w   d6
                beq.s   .gk_pos
                move.w  #1072,d1                ; goalY (bottom)
                moveq   #-1,d5                  ; out_dir = -1 (up into box)

.gk_pos:
                ; Lateral targetX = clamp(ball.x, 268, 372); predictive lead if shot incoming!
                move.w  2(a4),d0                ; ball.x
                moveq   #3,d4                   ; normal GK step speed = 3 px/frame

                ; Distance from goal line: dy_g = (ball.y - goalY) * out_dir
                move.w  4(a4),d2
                sub.w   d1,d2
                tst.w   d5
                bpl.s   .gk_dyok
                neg.w   d2
.gk_dyok:
                ; Is a shot coming toward our goal? (ball.vy * out_dir < -10 and dy_g < 140)
                move.w  10(a4),d3               ; ball.vy
                tst.w   d5
                bpl.s   .gk_vyok
                neg.w   d3
.gk_vyok:
                cmpi.w  #-10,d3
                bgt.s   .gk_no_shot
                cmpi.w  #140,d2
                bgt.s   .gk_no_shot
                ; INCOMING SHOT! Lead X by ball.vx*2 & lunge at 5 px/frame!
                move.w  8(a4),d3
                add.w   d3,d3
                add.w   d3,d0
                moveq   #5,d4
                bra.s   .gk_clamp_x

.gk_no_shot:
                ; Angle-narrowing depth: if ball in box (0 < dy_g < 180), step out up to 30px!
                tst.w   d2
                ble.s   .gk_clamp_x
                cmpi.w  #180,d2
                bge.s   .gk_clamp_x
                move.w  #180,d3
                sub.w   d2,d3
                lsr.w   #3,d3                   ; 0..22 px forward
                addq.w  #8,d3                   ; 8..30 px out from goal line
                tst.w   d5
                bpl.s   .gk_add_y
                neg.w   d3
.gk_add_y:      add.w   d3,d1

.gk_clamp_x:
                cmpi.w  #268,d0
                bge.s   .gk_xhi
                move.w  #268,d0
                bra.s   .gk_step
.gk_xhi:        cmpi.w  #372,d0
                ble.s   .gk_step
                move.w  #372,d0

.gk_step:
                ; Move GK toward (d0=targetX, d1=targetY) at max step d4 px/frame
                move.w  d0,d2
                sub.w   2(a5),d2                ; dx
                cmp.w   d4,d2
                ble.s   .gk_dxlo
                move.w  d4,d2
                bra.s   .gk_dxap
.gk_dxlo:       neg.w   d4
                cmp.w   d4,d2
                bge.s   .gk_dxr
                move.w  d4,d2
.gk_dxr:        neg.w   d4
.gk_dxap:       add.w   d2,2(a5)

                move.w  d1,d2
                sub.w   4(a5),d2                ; dy
                cmp.w   d4,d2
                ble.s   .gk_dylo
                move.w  d4,d2
                bra.s   .gk_dyap
.gk_dylo:       neg.w   d4
                cmp.w   d4,d2
                bge.s   .gk_dyap
                move.w  d4,d2
.gk_dyap:       add.w   d2,4(a5)

                ; Face the ball cleanly
                jsr     $b466.l
                andi.w  #7,d0
                move.w  d0,$26(a5)
                movem.l (a7)+,d0-d6/a0/a4
                rts

; =============================================================================
; 19. MANUAL HUMAN THROW-INS (hook_throwin, replaces $db2e)
;     - CPU taker (ID >= 11): runs original $db2e throw-in.
;     - Human taker (ID < 11): hold Fire & point joystick! Aims directly at
;       the nearest Team 1 teammate in that joystick direction!
; =============================================================================
hook_throwin:
                cmpi.w  #11,0(a5)
                blt.s   .ht_human
                ; CPU throw-in: execute displaced $db2e..$db33 & resume $db34
                move.w  $ee36.l,d0
                jmp     $db34.l

.ht_human:
                movem.l d0-d7/a0-a1/a4,-(a7)
                lea     G_BALL_STRUCT.l,a4
                st.b    $32(a4)                 ; keep ball in thrower's hands
                ; Read Joystick 1 ($2612 with d0=0)
                moveq   #0,d0
                jsr     $2612.l
                move.w  d0,d2                   ; d2 = joy bits (0=U,1=D,2=L,3=R,7=FIRE)

                ; Pick throw-in sprite pose (left touchline: 8=UR,9=R,10=DR; right: 11=UL,12=L,13=DL)
                moveq   #9,d1                   ; default Right (for $ee08==1)
                cmpi.w  #1,G_MATCH_STATE.l
                beq.s   .ht_pose
                moveq   #12,d1                  ; default Left (for $ee08==2)
.ht_pose:       btst    #0,d2                   ; UP?
                beq.s   .ht_pdn
                subq.w  #1,d1
                bra.s   .ht_psto
.ht_pdn:        btst    #1,d2                   ; DOWN?
                beq.s   .ht_psto
                addq.w  #1,d1
.ht_psto:       move.w  d1,$26(a5)
                bsr.w   .ht_hold_ball

                ; Hold Fire -> charge; Release Fire (after holding >= 1 frame) -> THROW!
                btst    #7,d2
                beq.s   .ht_chk_rel
                addq.w  #1,st_setp_chg
                bra.w   .ht_done
.ht_chk_rel:
                tst.w   st_setp_chg
                beq.w   .ht_done
                clr.w   st_setp_chg

                ; Compute aim unit vector (d3=ax, d4=ay) from joystick (default inward!)
                moveq   #1,d3                   ; inward right for $ee08==1
                cmpi.w  #1,G_MATCH_STATE.l
                beq.s   .ht_aim
                moveq   #-1,d3                  ; inward left for $ee08==2
.ht_aim:        moveq   #0,d4
                btst    #0,d2
                beq.s   .ht_adn
                moveq   #-1,d4
.ht_adn:        btst    #1,d2
                beq.s   .ht_find
                moveq   #1,d4

.ht_find:
                ; Aim at nearest Team 1 teammate in (d3, d4) direction, speed 38, vz=14!
                moveq   #38,d6
                bsr.w   setp_aim_teammate
                move.w  d0,8(a4)                ; ball.vx
                move.w  d1,10(a4)               ; ball.vy
                move.w  #14,12(a4)              ; ball.vz (crisp throw arc)
                clr.w   $32(a4)
                move.w  0(a5),$ee0a.l
                move.w  #$ffff,G_BALL_OWNER.l
                clr.w   G_MATCH_STATE.l
                clr.w   $24(a5)
                clr.w   $32(a5)
                move.w  #2,$26(a5)              ; restore normal facing (2=R or 6=L)
                cmpi.w  #1,d3
                beq.s   .ht_sfx
                move.w  #6,$26(a5)
.ht_sfx:        move.w  #$708,$28(a5)
                move.l  #$2026,$1cb6.l
                move.w  #1,$1cae.l
.ht_done:
                movem.l (a7)+,d0-d7/a0-a1/a4
                rts

.ht_hold_ball:
                move.w  2(a5),2(a4)
                move.w  4(a5),4(a4)
                move.w  #16,6(a4)
                clr.w   8(a4)
                clr.w   10(a4)
                clr.w   12(a4)
                rts

; =============================================================================
; 20. MANUAL HUMAN GOAL KICKS (hook_goalkick, replaces $b004)
;     - CPU GK (ID >= 11): runs brisk 16-frame original goal kick ($b00a).
;     - Human GK (ID < 11): hold Fire & point joystick! Aims at nearest Team 1
;       teammate in that direction; longer Fire hold = booming upfield punt!
; =============================================================================
hook_goalkick:
                cmpi.w  #11,0(a5)
                blt.s   .hg_human
                ; CPU goal kick: brisk 16-frame wait instead of 50!
                move.w  $38(a5),d0
                cmp.w   #$10,d0
                jmp     $b00c.l

.hg_human:
                movem.l d0-d7/a0-a1/a4,-(a7)
                lea     G_BALL_STRUCT.l,a4
                ; Read Joystick 1 ($2612 with d0=0)
                moveq   #0,d0
                jsr     $2612.l
                move.w  d0,d2

                ; Hold Fire -> charge; Release Fire -> KICK!
                btst    #7,d2
                beq.s   .hg_chk_rel
                addq.w  #1,st_setp_chg
                bra.w   .hg_done
.hg_chk_rel:
                move.w  st_setp_chg(pc),d7
                beq.w   .hg_done
                clr.w   st_setp_chg

                ; Compute aim vector (d3=ax, d4=ay): default upfield from our goal!
                moveq   #0,d3
                btst    #2,d2
                beq.s   .hg_jr
                moveq   #-1,d3
.hg_jr:         btst    #3,d2
                beq.s   .hg_jy
                moveq   #1,d3
.hg_jy:         moveq   #1,d4                   ; top goal ($ee08==7/8) kicks DOWN (+1)
                cmpi.w  #9,G_MATCH_STATE.l
                blt.s   .hg_chk_chg
                moveq   #-1,d4                  ; bottom goal ($ee08==9/10) kicks UP (-1)
.hg_chk_chg:
                ; Short tap (charge < 8) -> speed 44, vz=14; Held punt (charge >= 8) -> speed 60, vz=24!
                moveq   #44,d6
                moveq   #14,d5
                cmpi.w  #8,d7
                blt.s   .hg_aim
                moveq   #60,d6
                moveq   #24,d5
.hg_aim:
                bsr.s   setp_aim_teammate
                move.w  d0,8(a4)                ; ball.vx
                move.w  d1,10(a4)               ; ball.vy
                move.w  d5,12(a4)               ; ball.vz
                clr.w   $32(a4)
                move.w  0(a5),$ee0a.l
                move.w  #$ffff,G_BALL_OWNER.l
                clr.w   G_MATCH_STATE.l
                clr.w   $24(a5)
                clr.w   $38(a5)
                move.l  #$2026,$1cb6.l
                move.w  #1,$1cae.l
.hg_done:
                movem.l (a7)+,d0-d7/a0-a1/a4
                rts

; Helper: find nearest Team 1 teammate (P01..P10) in aim dir (d3=ax, d4=ay),
;         return normalized (d0=vx, d1=vy) at speed d6.w!
setp_aim_teammate:
                movem.l d2/d5/d7/a0-a1,-(a7)
                lea     G_PLAYERS+$3a.l,a0
                moveq   #9,d5
                suba.l  a1,a1
                move.w  #999,d7
.sa_loop:
                cmpa.l  a0,a5
                beq.s   .sa_next
                move.w  2(a0),d0
                sub.w   2(a5),d0                ; dx
                move.w  4(a0),d1
                sub.w   4(a5),d1                ; dy
                ; dot = dx*ax + dy*ay > 0
                move.w  d0,d2
                muls.w  d3,d2
                move.w  d1,-(a7)
                muls.w  d4,d1
                add.w   d1,d2
                move.w  (a7)+,d1
                ble.s   .sa_next
                tst.w   d0
                bpl.s   .sa_ax
                neg.w   d0
.sa_ax:         tst.w   d1
                bpl.s   .sa_ay
                neg.w   d1
.sa_ay:         add.w   d1,d0
                cmpi.w  #24,d0
                blt.s   .sa_next
                cmpi.w  #440,d0
                bgt.s   .sa_next
                cmp.w   d7,d0
                bge.s   .sa_next
                move.w  d0,d7
                move.l  a0,a1
.sa_next:       lea     $3a(a0),a0
                dbra    d5,.sa_loop

                move.l  a1,d0
                beq.s   .sa_fallback
                move.w  2(a1),d0
                sub.w   2(a5),d0
                move.w  4(a1),d1
                sub.w   4(a5),d1
                move.w  d0,d2
                bpl.s   .sa_m1
                neg.w   d2
.sa_m1:         move.w  d1,d5
                bpl.s   .sa_m2
                neg.w   d5
.sa_m2:         cmp.w   d5,d2
                bge.s   .sa_m3
                move.w  d5,d2
.sa_m3:         muls.w  d6,d0
                divs.w  d2,d0
                muls.w  d6,d1
                divs.w  d2,d1
                bra.s   .sa_done
.sa_fallback:
                move.w  d3,d0
                muls.w  d6,d0
                move.w  d4,d1
                muls.w  d6,d1
.sa_done:
                movem.l (a7)+,d2/d5/d7/a0-a1
                rts

; Custom 16x30 pixel-art slide tackle sprites (generated by build_italy.py: 4 x 300 = 1200 bytes)
                even
slide_spr_right:
                incbin  "games/in_progress/italy-1990-codemasters/work/slide_sprites.bin"
slide_spr_left  equ     slide_spr_right+300
slide_spr_down  equ     slide_spr_right+600
slide_spr_up    equ     slide_spr_right+900

; Helper: plot 2x1 Kick Off 2-style player dash at (d0=x, d1=y, d3=color 0..15) — 2x faster!
rad_plot2x2:
                movem.l d0-d5/a0,-(a7)
                mulu.w  #PITCH_STRIDE,d1
                lea     (a4,d1.l),a0
                move.w  d0,d4
                lsr.w   #4,d4
                lsl.w   #3,d4
                adda.w  d4,a0                   ; a0 -> word group for (x, y)
                andi.w  #15,d0
                move.w  #$c000,d5
                lsr.w   d0,d5
                not.w   d5
                and.w   d5,(a0)
                and.w   d5,2(a0)
                and.w   d5,4(a0)
                and.w   d5,6(a0)
                not.w   d5
                btst    #0,d3
                beq.s   .q1
                or.w    d5,(a0)
.q1:            btst    #1,d3
                beq.s   .q2
                or.w    d5,2(a0)
.q2:            btst    #2,d3
                beq.s   .q3
                or.w    d5,4(a0)
.q3:            btst    #3,d3
                beq.s   .q4
                or.w    d5,6(a0)
.q4:            movem.l (a7)+,d0-d5/a0
                rts
