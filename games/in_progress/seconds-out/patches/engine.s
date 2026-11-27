; =============================================================================
; Seconds Out (1988, Tynesoft) — Enhanced STE Engine (v1.0)
; =============================================================================
; Assembled at fixed PATCH_BASE = $88000, with relocated game at GAME_BASE = $80000.
;
; Features:
;   1. STE Blitter (HOG mode) + dirty-strip BG restore + fast CPU fallback
;   2. Uncoupled 50 Hz render / fixed 12.5 Hz (4-VBL) real-time logic + 50 Hz tweening
;   3. Stamina bars (HUD y=26..28, Gold normal / Red exhausted) for both fighters
;   4. Fatigue penalties (slower movement + half punch damage when exhausted)
;   5. Rebalanced Fighter AI (fair reactive timers, 50% read gate, special cooldown,
;      stamina-aware CPU, human-reactable late-game telegraphs)
;   6. 2-Player Versus Mode (F1 toggle, F3 opponent select; Joy 0 or WASD+LShift)
;   7. Career Fighting Styles / Perks (F2: Balanced, Speedster, Heavy, Iron Chin)
; =============================================================================

GAME_BASE       equ     $00080000
PATCH_BASE      equ     $00088000
HW_FLAGS_ADDR   equ     $00087f00       ; bit 0 = Blitter present

MASK4_BASE      equ     $00090000
MASK2_BOX1      equ     $000a2000
MASK2_PUNCHES   equ     $000a4000

; Game RAM addresses
G_BUF_IDX       equ     GAME_BASE+$0004 ; word: 0 or 1
G_BLIT_MODE     equ     GAME_BASE+$01b6 ; word: blit mode
G_VBL_CNT       equ     GAME_BASE+$0716 ; word: VBL counter
G_JOY1          equ     GAME_BASE+$07e4 ; byte: Joystick 1 (bits 0=U,1=D,2=L,3=R,7=Fire)
G_SCR_BACK      equ     GAME_BASE+$0a0a ; long: backbuffer ($70000 or $78000)
G_VBL_FLAG      equ     GAME_BASE+$0ada ; word: VBL flag
G_SHIFT         equ     GAME_BASE+$0adc ; word: fine X shift (0..15)
G_P2_X          equ     GAME_BASE+$1166 ; word: opponent X
G_P1_X          equ     GAME_BASE+$16d4 ; word: player X
G_P1_GUARD      equ     GAME_BASE+$16ee ; word: player guard/pose
G_P1_PUNCH_CD   equ     GAME_BASE+$16f2 ; word: player punch recovery cooldown
G_P1_DUCK       equ     GAME_BASE+$1bee ; word: player duck anim counter
G_P1_KO_GAUGE   equ     GAME_BASE+$225e ; word: KO meter (0..9)
G_P1_ATK_TYPE   equ     GAME_BASE+$29e2 ; word: player attack type
G_OPP_STRUCT    equ     GAME_BASE+$2bf8 ; 134-byte active opponent descriptor
G_P1_HP         equ     GAME_BASE+$2d4a ; word: player health (0..63)
G_P2_HP         equ     GAME_BASE+$2d4c ; word: opponent health (0..63)
G_P2_STUN       equ     GAME_BASE+$2f54 ; word: opponent hit-stun flag
G_P2_ATK_ACT    equ     GAME_BASE+$2f5a ; word: opponent attack active flag
G_SHAKE_FLAG    equ     GAME_BASE+$30bc ; word: screen shake flag
G_P2_Y          equ     GAME_BASE+$31ae ; word: opponent Y
G_P2_GRP        equ     GAME_BASE+$34ac ; word: opponent sprite group
G_P2_FRM        equ     GAME_BASE+$34ae ; word: opponent sprite frame
G_P2_BLK        equ     GAME_BASE+$34b4 ; word: opponent block state (0=hi,1=lo,2=open,3=duck)
G_P2_DUCK       equ     GAME_BASE+$3600 ; word: opponent ducking flag
G_P1_BLK_STATE  equ     GAME_BASE+$373e ; word: player block state (0=hi,1=lo)
G_P1_STUN       equ     GAME_BASE+$3742 ; word: player hit-stun flag
G_JOY0          equ     GAME_BASE+$3fef ; byte: Joystick 0 packet byte
G_KEY_BASE      equ     GAME_BASE+$4223 ; 128-byte scancode table ($ff=pressed)
G_OPP_IDX       equ     GAME_BASE+$44d0 ; word: current opponent index (0..4)

; Keyboard scancodes (added to G_KEY_BASE)
KEY_W           equ     $11
KEY_A           equ     $1e
KEY_S           equ     $1f
KEY_D           equ     $20
KEY_LSHIFT      equ     $2a
KEY_F1          equ     $3b
KEY_F2          equ     $3c
KEY_F3          equ     $3d

; Original routines
G_ORIG_BLIT2    equ     GAME_BASE+$0bc4
G_ORIG_BLIT4    equ     GAME_BASE+$1bfa
G_ORIG_CSP_UNPK equ     GAME_BASE+$5004
G_ORIG_CLEAR_T  equ     GAME_BASE+$45bc
G_ORIG_P1_HPBAR equ     GAME_BASE+$2d4e
G_ORIG_P2_HPBAR equ     GAME_BASE+$2e5c
G_ORIG_PRINT    equ     GAME_BASE+$499e

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

BLT_GO_HOG      macro
                move.b  #$c0,BLT_CTRL.w
                endm

                org     PATCH_BASE

; -----------------------------------------------------------------------------
; Fixed Entry Jump Table (24 * 4 = 96 bytes at PATCH_BASE + $00..$5f)
; -----------------------------------------------------------------------------
entry_table:
                jmp     hook_post_pi1_load(pc)  ; +$00: $02b8
                jmp     hook_post_csp_load(pc)  ; +$04: $455a
                jmp     hook_bg_partial(pc)     ; +$08: $10b6
                jmp     hook_bg_full(pc)        ; +$0c: $10ec
                jmp     hook_blit_mode2(pc)     ; +$10: $0bc4
                jmp     hook_blit_mode4(pc)     ; +$14: $1bfa
                jmp     hook_fight_loop(pc)     ; +$18: $0506
                jmp     hook_spr_record(pc)     ; +$1c: $241a
                jmp     hook_fight_init(pc)     ; +$20: $03d6 (init HP + stamina)
                jmp     hook_round_init(pc)     ; +$24: $047a (reset stamina on new round)
                jmp     hook_load_opp(pc)       ; +$28: $2d24 (rebalance opponent stats)
                jmp     hook_opp_ai_entry(pc)   ; +$2c: $134c (2P control or CPU AI)
                jmp     hook_opp_move_add(pc)   ; +$30: $1392 (P2 fatigue move right)
                jmp     hook_opp_move_sub(pc)   ; +$34: $13a8 (P2 fatigue move left)
                jmp     hook_opp_punch_a(pc)    ; +$38: $1568 (P2 Punch A stamina)
                jmp     hook_opp_special(pc)    ; +$3c: $159c (P2 Special stamina)
                jmp     hook_opp_punch_b(pc)    ; +$40: $15d2 (P2 Punch B stamina)
                jmp     hook_p1_punch_l(pc)     ; +$44: $1736 (P1 Left punch stamina)
                jmp     hook_p1_punch_r(pc)     ; +$48: $1780 (P1 Right punch stamina)
                jmp     hook_p1_special(pc)     ; +$4c: $1b72 (P1 Special KO stamina)
                jmp     hook_p1_move_l(pc)      ; +$50: $1a9e (P1 move left + style/fatigue)
                jmp     hook_p1_move_r(pc)      ; +$54: $1abc (P1 move right + style/fatigue)
                jmp     hook_p1_dmg(pc)         ; +$58: $2b44 (P1 damage + style/fatigue)
                jmp     hook_p2_dmg(pc)         ; +$5c: $38a6 (P2 damage + fatigue/chin)
                jmp     hook_p2_block(pc)       ; +$60: $2bb8 (P2 block stamina drain)
                jmp     hook_p1_block(pc)       ; +$64: $3912 (P1 block stamina drain)
                jmp     hook_cpu_react(pc)      ; +$68: $360c (rebalanced reactive AI)
                jmp     hook_react_blk(pc)      ; +$6c: $4ab8 (stamina-gated auto-block)
                jmp     hook_title_draw(pc)     ; +$70: $1d54 (draw menu + credit)
                jmp     hook_title_poll1(pc)    ; +$74: $1da6 (F1/F2/F3 on title)
                jmp     hook_title_poll2(pc)    ; +$78: $1e7a (F1/F2/F3 on title alt)
                jmp     hook_ikbd_joy0(pc)      ; +$7c: $40ac (fix Joy 0 $fe packet!)
                jmp     hook_newspaper(pc)      ; +$80: $0708 (between-fights newspaper!)
                jmp     hook_ko_draw(pc)        ; +$84: $2262 (2P tug-of-war KO gauge!)
                jmp     hook_p1_ko_inc(pc)      ; +$88: $2b8e (2P tug-of-war P1 hit pull!)
                jmp     hook_trainer_2p(pc)     ; +$8c: $060c (skip trainer in 2P mode!)
                jmp     hook_ikbd_joy1(pc)      ; +$90: $4108 (race-free raw_joy1 capture!)
                jmp     hook_p2_kd_cnt(pc)      ; +$94: $2f6e (low stamina -> longer floor count P2!)
                jmp     hook_p1_kd_cnt(pc)      ; +$98: $3a74 (low stamina -> longer floor count P1!)

; Runtime config words (at PATCH_BASE + $9c)
cfg_use_blitter: dc.w   1                       ; +$9c: 1 = STE Blitter
cfg_uncouple:    dc.w   1                       ; +$8a: 1 = 50 Hz uncoupled
cfg_tween:       dc.w   1                       ; +$8c: 1 = 50 Hz motion tween
cfg_2p_mode:     dc.w   0                       ; +$8e: 0 = 1P Career, 1 = 2P Versus
cfg_style:       dc.w   0                       ; +$90: 0=Bal, 1=Speed, 2=Heavy, 3=IronChin
cfg_2p_opp:      dc.w   0                       ; +$92: 0..4 opponent for 2P mode

; =============================================================================
; 1. MASK CACHE BUILDERS
; =============================================================================
build_mask4_sheet:
                movem.l d0-d2/a0-a1,-(sp)
                move.w  #4000-1,d2
.bm4_lp:
                move.w  (a0)+,d0
                or.w    (a0)+,d0
                or.w    (a0)+,d0
                or.w    (a0)+,d0
                not.w   d0
                move.w  d0,(a1)+
                dbra    d2,.bm4_lp
                movem.l (sp)+,d0-d2/a0-a1
                rts

build_mask2_sheet:
                movem.l d0-d2/a0-a1,-(sp)
                move.w  #4000-1,d2
.bm2_lp:
                move.w  (a0)+,d0
                or.w    (a0)+,d0
                addq.l  #4,a0
                not.w   d0
                move.w  d0,(a1)+
                dbra    d2,.bm2_lp
                movem.l (sp)+,d0-d2/a0-a1
                rts

hook_post_pi1_load:
                movem.l d0-d2/a0-a1,-(sp)
                lea     $20000,a0
                lea     MASK4_BASE+$0000,a1
                bsr.w   build_mask4_sheet
                lea     $28000,a0
                lea     MASK4_BASE+$2000,a1
                bsr.w   build_mask4_sheet
                lea     $30000,a0
                lea     MASK4_BASE+$4000,a1
                bsr.w   build_mask4_sheet
                lea     $38000,a0
                lea     MASK4_BASE+$6000,a1
                bsr.w   build_mask4_sheet
                lea     $58000,a0
                lea     MASK4_BASE+$e000,a1
                bsr.w   build_mask4_sheet
                lea     $58000,a0
                lea     MASK2_BOX1,a1
                bsr.w   build_mask2_sheet
                lea     $30000,a0
                lea     MASK2_PUNCHES,a1
                bsr.w   build_mask2_sheet
                movem.l (sp)+,d0-d2/a0-a1
                jmp     G_ORIG_CLEAR_T

hook_post_csp_load:
                jsr     G_ORIG_CSP_UNPK
                movem.l d0-d2/a0-a1,-(sp)
                lea     $40000,a0
                lea     MASK4_BASE+$8000,a1
                bsr.w   build_mask4_sheet
                lea     $48000,a0
                lea     MASK4_BASE+$a000,a1
                bsr.w   build_mask4_sheet
                lea     $60000,a0
                lea     MASK4_BASE+$10000,a1
                bsr.w   build_mask4_sheet
                movem.l (sp)+,d0-d2/a0-a1
                rts

; =============================================================================
; 2. BACKGROUND COPY (STE Blitter + Dirty-Strip Optimisation + CPU Fallback)
; =============================================================================
hook_bg_partial:
                tst.w   cfg_use_blitter
                beq.w   .bgp_cpu
                btst.b  #0,HW_FLAGS_ADDR.l
                beq.w   .bgp_cpu

                ; If dirty-strip tracking is active for this buffer, restore ONLY
                ; the horizontal word-column span [x0..x1] instead of full 320 px!
                move.w  G_BUF_IDX.l,d0
                andi.w  #1,d0
                add.w   d0,d0
                lea     buf_dirty_ok(pc),a0
                tst.w   (a0,d0.w)
                beq.w   .bgp_full_strip

                lea     buf_x0_bytes(pc),a1
                move.w  (a1,d0.w),d1            ; x0 byte offset (0..152, mult of 8)
                lea     buf_x1_bytes(pc),a2
                move.w  (a2,d0.w),d2            ; x1 byte offset (8..160, mult of 8)
                sub.w   d1,d2                   ; width in bytes (8..160)
                ble.w   .bgp_full_strip
                move.w  d2,d3
                lsr.w   #1,d3                   ; XCNT in words (4..80)
                move.w  #160,d4
                sub.w   d2,d4
                addq.w  #2,d4                   ; SYINC = DYINC = 160 - width + 2

                move.l  #$00053e80,d0           ; y = 100 ($3e80)
                ext.l   d1
                add.l   d1,d0
                move.l  d0,BLT_SADDR.w
                move.l  G_SCR_BACK.l,d0
                addi.l  #$3e80,d0
                add.l   d1,d0
                move.l  d0,BLT_DADDR.w
                move.w  #2,BLT_SXINC.w
                move.w  d4,BLT_SYINC.w
                move.w  #2,BLT_DXINC.w
                move.w  d4,BLT_DYINC.w
                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                move.w  #$ffff,BLT_EM3.w
                move.b  #2,BLT_HOP.w
                move.b  #3,BLT_OP.w
                move.b  #0,BLT_SKEW.w
                move.w  d3,BLT_XCNT.w
                ; 100 lines in 25 x 4-line HOG bursts (~0.15ms each -> 100% IKBD-safe!)
                moveq   #25-1,d7
.bgp_s_lp:
                move.w  #4,BLT_YCNT.w
                BLT_GO_HOG
                dbra    d7,.bgp_s_lp
                rts

.bgp_full_strip:
                move.l  #$00053e80,BLT_SADDR.w
                move.l  G_SCR_BACK.l,d0
                addi.l  #$3e80,d0
                move.l  d0,BLT_DADDR.w
                move.w  #2,BLT_SXINC.w
                move.w  #2,BLT_SYINC.w
                move.w  #2,BLT_DXINC.w
                move.w  #2,BLT_DYINC.w
                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                move.w  #$ffff,BLT_EM3.w
                move.b  #2,BLT_HOP.w
                move.b  #3,BLT_OP.w
                move.b  #0,BLT_SKEW.w
                move.w  #80,BLT_XCNT.w
                moveq   #25-1,d7
.bgp_f_lp:
                move.w  #4,BLT_YCNT.w
                BLT_GO_HOG
                dbra    d7,.bgp_f_lp
                rts
.bgp_cpu:
                lea     $57cd0,a0
                movea.l G_SCR_BACK.l,a1
                adda.l  #$7d00,a1
                move.w  #$a6-1,d0
.bgp_lp:
                movem.l (a0),d1-d7/a2-a6
                movem.l d1-d7/a2-a6,-(a1)
                lea     -$30(a0),a0
                movem.l (a0),d1-d7/a2-a6
                movem.l d1-d7/a2-a6,-(a1)
                lea     -$30(a0),a0
                dbra    d0,.bgp_lp
                rts

hook_bg_full:
                ; Clear dirty-strip cache since full BG covers everything
                clr.l   buf_dirty_ok
                tst.w   cfg_use_blitter
                beq.w   .bgf_cpu
                btst.b  #0,HW_FLAGS_ADDR.l
                beq.w   .bgf_cpu
                move.l  #$000525a0,BLT_SADDR.w
                move.l  G_SCR_BACK.l,d0
                addi.l  #$25a0,d0
                move.l  d0,BLT_DADDR.w
                move.w  #2,BLT_SXINC.w
                move.w  #2,BLT_SYINC.w
                move.w  #2,BLT_DXINC.w
                move.w  #2,BLT_DYINC.w
                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                move.w  #$ffff,BLT_EM3.w
                move.b  #2,BLT_HOP.w
                move.b  #3,BLT_OP.w
                move.b  #0,BLT_SKEW.w
                move.w  #64,BLT_XCNT.w
                move.w  #1,BLT_YCNT.w
                BLT_GO_HOG
                move.w  #80,BLT_XCNT.w
                ; 139 lines = 34*4 + 3 lines (IKBD-safe 4-line bursts!)
                moveq   #34-1,d7
.bgf_s_lp:
                move.w  #4,BLT_YCNT.w
                BLT_GO_HOG
                dbra    d7,.bgf_s_lp
                move.w  #3,BLT_YCNT.w
                BLT_GO_HOG
                rts
.bgf_cpu:
                lea     $57cd0,a0
                movea.l G_SCR_BACK.l,a1
                adda.l  #$7d00,a1
                move.w  #$e9-1,d0
.bgf_lp:
                movem.l (a0),d1-d7/a2-a6
                movem.l d1-d7/a2-a6,-(a1)
                lea     -$30(a0),a0
                movem.l (a0),d1-d7/a2-a6
                movem.l d1-d7/a2-a6,-(a1)
                lea     -$30(a0),a0
                dbra    d0,.bgf_lp
                rts

; =============================================================================
; 3. SHIFTED 4-PLANE MASKED SPRITE BLITTER (hook_blit_mode2)
; =============================================================================
hook_blit_mode2:
                move.l  a1,d0
                subi.l  #$20000,d0
                bcs.w   m2_slow_orig
                cmpi.l  #$48000,d0
                bcc.w   m2_slow_orig

                lsr.l   #2,d0
                addi.l  #MASK4_BASE,d0
                movea.l d0,a0

                move.w  d1,d3
                lsr.w   #2,d3
                move.w  G_SHIFT.l,d2

                tst.w   cfg_use_blitter
                beq.w   blit_mode2_cpu_fast
                btst.b  #0,HW_FLAGS_ADDR.l
                beq.w   blit_mode2_cpu_fast

                tst.w   d2
                bne.s   .m2_shifted
                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                move.w  #$ffff,BLT_EM3.w
                move.b  #0,BLT_SKEW.w
                move.w  d3,d4
                move.w  d3,d5
                subq.w  #1,d5
                bra.s   .m2_blt_common
.m2_shifted:
                move.w  #$ffff,d0
                lsr.w   d2,d0
                move.w  d0,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                not.w   d0
                move.w  d0,BLT_EM3.w
                move.b  d2,d0
                ori.b   #$40,d0
                move.b  d0,BLT_SKEW.w
                move.w  d3,d4
                addq.w  #1,d4
                move.w  d3,d5
                subq.w  #1,d5
.m2_blt_common:
                move.b  #2,BLT_HOP.w
                move.w  #8,BLT_DXINC.w
                move.w  d4,d0
                subq.w  #1,d0
                lsl.w   #3,d0
                move.w  #160,d1
                sub.w   d0,d1
                move.w  d1,BLT_DYINC.w
                move.w  d4,BLT_XCNT.w

                move.w  #2,BLT_SXINC.w
                move.w  d5,d0
                add.w   d0,d0
                move.w  #40,d1
                sub.w   d0,d1
                move.w  d1,BLT_SYINC.w
                move.b  #1,BLT_OP.w

                movea.l a2,a3
                moveq   #3,d7
.m2_and_lp:
                move.l  a0,BLT_SADDR.w
                move.l  a3,BLT_DADDR.w
                bsr.s   blt_go_lines_16
                addq.l  #2,a3
                dbra    d7,.m2_and_lp

                move.w  #8,BLT_SXINC.w
                move.w  d5,d0
                lsl.w   #3,d0
                move.w  #160,d1
                sub.w   d0,d1
                move.w  d1,BLT_SYINC.w
                move.b  #7,BLT_OP.w

                movea.l a1,a4
                movea.l a2,a3
                moveq   #3,d7
.m2_or_lp:
                move.l  a4,BLT_SADDR.w
                move.l  a3,BLT_DADDR.w
                bsr.s   blt_go_lines_16
                addq.l  #2,a4
                addq.l  #2,a3
                dbra    d7,.m2_or_lp
                rts

; IKBD-safe helper: run d6.w lines in <=16-line HOG bursts (~0.1ms max per burst!)
blt_go_lines_16:
                move.w  d6,d0
.bg16_lp:
                cmpi.w  #16,d0
                ble.s   .bg16_last
                move.w  #16,BLT_YCNT.w
                BLT_GO_HOG
                subi.w  #16,d0
                bra.s   .bg16_lp
.bg16_last:
                move.w  d0,BLT_YCNT.w
                BLT_GO_HOG
                rts

blit_mode2_cpu_fast:
                movem.l d0-d7/a0-a6,-(sp)
                subq.w  #1,d6
                subq.w  #1,d3
                tst.w   d2
                bne.s   .m2c_shifted
.m2c_u_row:
                movea.l a0,a3
                movea.l a1,a4
                movea.l a2,a5
                move.w  d3,d7
.m2c_u_col:
                move.w  (a3)+,d0
                move.w  d0,d1
                swap    d0
                move.w  d1,d0
                and.l   d0,(a5)
                move.l  (a4)+,d1
                or.l    d1,(a5)+
                and.l   d0,(a5)
                move.l  (a4)+,d1
                or.l    d1,(a5)+
                dbra    d7,.m2c_u_col
                lea     40(a0),a0
                lea     160(a1),a1
                lea     160(a2),a2
                dbra    d6,.m2c_u_row
                movem.l (sp)+,d0-d7/a0-a6
                rts
.m2c_shifted:
                move.w  d3,cpu_nchunks
                move.w  d6,cpu_rows
.m2c_s_row:
                movea.l a0,a3
                movea.l a1,a4
                movea.l a2,a5
                move.w  cpu_nchunks(pc),d7
                move.l  #$ffff0000,d4
                clr.l   cpu_p01_hi
                clr.l   cpu_p23_hi
.m2c_s_col:
                move.w  (a3)+,d4
                move.l  d4,d0
                lsr.l   d2,d0
                swap    d4
                move.w  d0,d1
                swap    d0
                move.w  d1,d0

                move.w  cpu_p01_hi(pc),d1
                swap    d1
                move.w  (a4)+,d1
                move.w  d1,cpu_p01_hi
                lsr.l   d2,d1
                and.w   d0,(a5)
                or.w    d1,(a5)+

                move.w  cpu_p01_hi+2(pc),d1
                swap    d1
                move.w  (a4)+,d1
                move.w  d1,cpu_p01_hi+2
                lsr.l   d2,d1
                and.w   d0,(a5)
                or.w    d1,(a5)+

                move.w  cpu_p23_hi(pc),d1
                swap    d1
                move.w  (a4)+,d1
                move.w  d1,cpu_p23_hi
                lsr.l   d2,d1
                and.w   d0,(a5)
                or.w    d1,(a5)+

                move.w  cpu_p23_hi+2(pc),d1
                swap    d1
                move.w  (a4)+,d1
                move.w  d1,cpu_p23_hi+2
                lsr.l   d2,d1
                and.w   d0,(a5)
                or.w    d1,(a5)+
                dbra    d7,.m2c_s_col

                move.w  #$ffff,d4
                lsr.l   d2,d4
                moveq   #0,d1
                move.w  cpu_p01_hi(pc),d1
                swap    d1
                lsr.l   d2,d1
                and.w   d4,(a5)
                or.w    d1,(a5)+
                moveq   #0,d1
                move.w  cpu_p01_hi+2(pc),d1
                swap    d1
                lsr.l   d2,d1
                and.w   d4,(a5)
                or.w    d1,(a5)+
                moveq   #0,d1
                move.w  cpu_p23_hi(pc),d1
                swap    d1
                lsr.l   d2,d1
                and.w   d4,(a5)
                or.w    d1,(a5)+
                moveq   #0,d1
                move.w  cpu_p23_hi+2(pc),d1
                swap    d1
                lsr.l   d2,d1
                and.w   d4,(a5)
                or.w    d1,(a5)+

                lea     40(a0),a0
                lea     160(a1),a1
                lea     160(a2),a2
                subq.w  #1,cpu_rows
                bpl.w   .m2c_s_row
                movem.l (sp)+,d0-d7/a0-a6
                rts

m2_slow_orig:
                move.w  d6,GAME_BASE+$cb8.l
                jmp     G_ORIG_BLIT2+6

; =============================================================================
; 4. SHIFTED 2-PLANE MASKED SPRITE BLITTER (hook_blit_mode4)
; =============================================================================
hook_blit_mode4:
                move.l  a1,d0
                cmpi.l  #$58000,d0
                bcs.s   .m4_chk_punches
                cmpi.l  #$60000,d0
                bcc.w   m4_slow_orig
                subi.l  #$58000,d0
                lsr.l   #2,d0
                addi.l  #MASK2_BOX1,d0
                bra.s   .m4_have_mask
.m4_chk_punches:
                cmpi.l  #$30000,d0
                bcs.w   m4_slow_orig
                cmpi.l  #$38000,d0
                bcc.w   m4_slow_orig
                subi.l  #$30000,d0
                lsr.l   #2,d0
                addi.l  #MASK2_PUNCHES,d0
.m4_have_mask:
                movea.l d0,a0
                move.w  d1,d3
                lsr.w   #2,d3
                move.w  G_SHIFT.l,d2

                tst.w   cfg_use_blitter
                beq.w   blit_mode4_cpu_fast
                btst.b  #0,HW_FLAGS_ADDR.l
                beq.w   blit_mode4_cpu_fast

                tst.w   d2
                bne.s   .m4_shifted
                move.w  #$ffff,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                move.w  #$ffff,BLT_EM3.w
                move.b  #0,BLT_SKEW.w
                move.w  d3,d4
                move.w  d3,d5
                subq.w  #1,d5
                bra.s   .m4_blt_common
.m4_shifted:
                move.w  #$ffff,d0
                lsr.w   d2,d0
                move.w  d0,BLT_EM1.w
                move.w  #$ffff,BLT_EM2.w
                not.w   d0
                move.w  d0,BLT_EM3.w
                move.b  d2,d0
                ori.b   #$40,d0
                move.b  d0,BLT_SKEW.w
                move.w  d3,d4
                addq.w  #1,d4
                move.w  d3,d5
                subq.w  #1,d5
.m4_blt_common:
                move.b  #2,BLT_HOP.w
                move.w  #8,BLT_DXINC.w
                move.w  d4,d0
                subq.w  #1,d0
                lsl.w   #3,d0
                move.w  #160,d1
                sub.w   d0,d1
                move.w  d1,BLT_DYINC.w
                move.w  d4,BLT_XCNT.w

                move.w  #2,BLT_SXINC.w
                move.w  d5,d0
                add.w   d0,d0
                move.w  #40,d1
                sub.w   d0,d1
                move.w  d1,BLT_SYINC.w
                move.b  #1,BLT_OP.w

                movea.l a2,a3
                moveq   #3,d7
.m4_and_lp:
                move.l  a0,BLT_SADDR.w
                move.l  a3,BLT_DADDR.w
                bsr.w   blt_go_lines_16
                addq.l  #2,a3
                dbra    d7,.m4_and_lp

                move.w  #8,BLT_SXINC.w
                move.w  d5,d0
                lsl.w   #3,d0
                move.w  #160,d1
                sub.w   d0,d1
                move.w  d1,BLT_SYINC.w
                move.b  #7,BLT_OP.w

                move.l  a1,BLT_SADDR.w
                move.l  a2,BLT_DADDR.w
                bsr.w   blt_go_lines_16

                lea     2(a1),a4
                lea     2(a2),a3
                move.l  a4,BLT_SADDR.w
                move.l  a3,BLT_DADDR.w
                bsr.w   blt_go_lines_16
                rts

blit_mode4_cpu_fast:
                movem.l d0-d7/a0-a6,-(sp)
                subq.w  #1,d6
                subq.w  #1,d3
                tst.w   d2
                bne.s   .m4c_shifted
.m4c_u_row:
                movea.l a0,a3
                movea.l a1,a4
                movea.l a2,a5
                move.w  d3,d7
.m4c_u_col:
                move.w  (a3)+,d0
                move.w  d0,d1
                swap    d0
                move.w  d1,d0
                and.l   d0,(a5)
                move.l  (a4),d1
                or.l    d1,(a5)+
                and.l   d0,(a5)+
                addq.l  #8,a4
                dbra    d7,.m4c_u_col
                lea     40(a0),a0
                lea     160(a1),a1
                lea     160(a2),a2
                dbra    d6,.m4c_u_row
                movem.l (sp)+,d0-d7/a0-a6
                rts
.m4c_shifted:
                move.w  d3,cpu_nchunks
                move.w  d6,cpu_rows
.m4c_s_row:
                movea.l a0,a3
                movea.l a1,a4
                movea.l a2,a5
                move.w  cpu_nchunks(pc),d7
                move.l  #$ffff0000,d4
                clr.l   cpu_p01_hi
.m4c_s_col:
                move.w  (a3)+,d4
                move.l  d4,d0
                lsr.l   d2,d0
                swap    d4
                move.w  d0,d1
                swap    d0
                move.w  d1,d0
                move.w  cpu_p01_hi(pc),d1
                swap    d1
                move.w  (a4)+,d1
                move.w  d1,cpu_p01_hi
                lsr.l   d2,d1
                and.w   d0,(a5)
                or.w    d1,(a5)+
                move.w  cpu_p01_hi+2(pc),d1
                swap    d1
                move.w  (a4)+,d1
                move.w  d1,cpu_p01_hi+2
                lsr.l   d2,d1
                and.w   d0,(a5)
                or.w    d1,(a5)+
                and.l   d0,(a5)+
                addq.l  #4,a4
                dbra    d7,.m4c_s_col

                move.w  #$ffff,d4
                lsr.l   d2,d4
                move.w  d4,d0
                swap    d0
                move.w  d4,d0
                moveq   #0,d1
                move.w  cpu_p01_hi(pc),d1
                swap    d1
                lsr.l   d2,d1
                and.w   d4,(a5)
                or.w    d1,(a5)+
                moveq   #0,d1
                move.w  cpu_p01_hi+2(pc),d1
                swap    d1
                lsr.l   d2,d1
                and.w   d4,(a5)
                or.w    d1,(a5)+
                and.l   d0,(a5)+

                lea     40(a0),a0
                lea     160(a1),a1
                lea     160(a2),a2
                subq.w  #1,cpu_rows
                bpl.w   .m4c_s_row
                movem.l (sp)+,d0-d7/a0-a6
                rts

m4_slow_orig:
                move.w  d6,GAME_BASE+$cb8.l
                jmp     G_ORIG_BLIT4+6

; =============================================================================
; 5. UNCOUPLED 50 Hz RENDER / FIXED 12.5 Hz LOGIC LOOP + TWEENING + DIRTY STRIP
; =============================================================================
hook_fight_loop:
                tst.w   cfg_uncouple
                bne.s   .uncoupled_entry
                move.w  G_BUF_IDX.l,d0
                jmp     GAME_BASE+$50c

.uncoupled_entry:
                clr.w   vbl_accum
                clr.l   buf_dirty_ok
                move.w  G_P2_X.l,p2_prev_x
                move.w  G_P1_X.l,p1_prev_x
                move.w  #1,need_first_tick

.ul_frame:
                move.w  G_BUF_IDX.l,d0
                bsr.w   flip_1vbl
                jsr     GAME_BASE+$aa0          ; pause check (P key)

                move.w  G_VBL_CNT.l,d0
                clr.w   G_VBL_CNT.l
                add.w   d0,vbl_accum
                ; Clamp accumulator to 9 VBLs (max 3 catch-up ticks)
                cmpi.w  #9,vbl_accum
                ble.s   .ul_acc_ok
                move.w  #9,vbl_accum
.ul_acc_ok:
                tst.w   need_first_tick
                bne.s   .ul_do_tick
                ; Snappy 16.7 Hz (3-VBL) logic tick + 50 Hz render & tweening!
                cmpi.w  #3,vbl_accum
                blt.w   .ul_render_only

.ul_tick_loop:
                subq.w  #3,vbl_accum
.ul_do_tick:
                clr.w   need_first_tick
                addq.w  #1,logic_tick_cnt
                move.w  G_P2_X.l,p2_prev_x
                move.w  G_P1_X.l,p1_prev_x

                ; Stamina regeneration & cooldowns (once per 12.5 Hz logic tick!)
                bsr.w   stamina_tick

                tst.w   GAME_BASE+$27e.l
                bne.w   .ul_round_end

                clr.w   dl_count
                move.w  #1,dl_recording

                clr.w   dl_bg_full
                tst.w   GAME_BASE+$3a5e.l
                bne.s   .ul_bg_is_full
                tst.w   GAME_BASE+$3be6.l
                beq.s   .ul_bg_done
.ul_bg_is_full:
                move.w  #1,dl_bg_full
                addq.w  #1,GAME_BASE+$5002.l
                cmpi.w  #1,GAME_BASE+$5002.l
                ble.s   .ul_bg_done
                andi.w  #3,GAME_BASE+$5002.l
                jsr     GAME_BASE+$4fd2
.ul_bg_done:
                clr.w   dl_cur_owner
                jsr     GAME_BASE+$4bbe
                move.w  #2,dl_cur_owner
                jsr     GAME_BASE+$1318
                tst.w   G_P1_HP.l
                beq.s   .ul_skip_p2_atk
                tst.w   G_P2_HP.l
                beq.s   .ul_skip_p2_atk
                jsr     GAME_BASE+$374e
.ul_skip_p2_atk:
                move.w  #1,dl_cur_owner
                bsr.w   call_p1_with_daze
                tst.w   G_P1_HP.l
                beq.s   .ul_skip_p1_atk
                tst.w   G_P2_HP.l
                beq.s   .ul_skip_p1_atk
                jsr     GAME_BASE+$29e8
.ul_skip_p1_atk:
                clr.w   dl_cur_owner
                tst.w   GAME_BASE+$3940.l
                beq.s   .ul_no_kd
                jsr     GAME_BASE+$3974
.ul_no_kd:
                clr.w   dl_recording

                ; Update HUD stamina bars if dirty
                bsr.w   draw_stamina_bars

                tst.b   GAME_BASE+$4250.l
                bne.w   .ul_fight_end
                tst.w   GAME_BASE+$3d1a.l
                bne.w   .ul_fight_end
                jsr     GAME_BASE+$986

                cmpi.w  #3,vbl_accum
                bge.w   .ul_tick_loop

.ul_render_only:
                tst.w   dl_bg_full
                bne.s   .ul_r_bgf
                bsr.w   hook_bg_partial
                bra.s   .ul_r_sprites
.ul_r_bgf:
                bsr.w   hook_bg_full

.ul_r_sprites:
                ; Track dirty X bounds for this buffer's next BG partial restore
                move.w  #160,cur_min_xb
                clr.w   cur_max_xb
                move.w  #1,cur_only_partial

                ; Tween alpha in [0..3] mapped to [0, 1, 2, 4] (div by 4)
                move.w  vbl_accum(pc),d7
                cmpi.w  #3,d7
                blt.s   .ul_a_ok
                moveq   #4,d7
.ul_a_ok:
                tst.w   cfg_tween
                bne.s   .ul_do_replay
                moveq   #4,d7

.ul_do_replay:
                move.w  dl_count(pc),d5
                beq.w   .ul_r_done
                lea     dl_entries(pc),a6
                subq.w  #1,d5
.ul_r_lp:
                movem.w d5/d7,-(sp)
                move.w  0(a6),d0                ; group
                move.w  2(a6),d6                ; frame
                move.w  4(a6),d4                ; x
                move.w  6(a6),d5                ; y
                move.w  8(a6),G_BLIT_MODE.l
                move.w  10(a6),d1               ; owner
                cmpi.w  #1,d1
                bne.s   .ul_chk_p2
                move.w  p1_prev_x(pc),d2
                move.w  d4,d3
                sub.w   d2,d3
                muls.w  d7,d3
                asr.w   #2,d3
                add.w   d2,d3
                move.w  d3,d4
                bra.s   .ul_track_bounds
.ul_chk_p2:
                cmpi.w  #2,d1
                bne.s   .ul_track_bounds
                move.w  p2_prev_x(pc),d2
                move.w  d4,d3
                sub.w   d2,d3
                muls.w  d7,d3
                asr.w   #2,d3
                add.w   d2,d3
                move.w  d3,d4
.ul_track_bounds:
                ; If sprite touches y < 100 (crowd flash / standing tall), disable partial strip
                cmpi.w  #100,d5
                bge.s   .ul_tb_x
                clr.w   cur_only_partial
.ul_tb_x:
                ; Expand cur_min_xb / cur_max_xb (conservatively +112 px width = 56 bytes)
                move.w  d4,d2
                lsr.w   #1,d2
                andi.w  #$fff8,d2               ; left byte offset (mult of 8)
                cmp.w   cur_min_xb(pc),d2
                bge.s   .ul_tb_max
                move.w  d2,cur_min_xb
.ul_tb_max:
                addi.w  #64,d2                  ; conservative +128 px right bound
                cmpi.w  #160,d2
                ble.s   .ul_tb_m2
                move.w  #160,d2
.ul_tb_m2:
                cmp.w   cur_max_xb(pc),d2
                ble.s   .ul_call_spr
                move.w  d2,cur_max_xb

.ul_call_spr:
                move.l  a6,-(sp)
                bsr.w   call_orig_spr_draw
                movea.l (sp)+,a6
                movem.w (sp)+,d5/d7
                lea     12(a6),a6
                dbra    d5,.ul_r_lp

.ul_r_done:
                ; Save dirty X bounds for THIS buffer
                move.w  G_BUF_IDX.l,d0
                andi.w  #1,d0
                add.w   d0,d0
                lea     buf_dirty_ok(pc),a0
                move.w  cur_only_partial(pc),(a0,d0.w)
                lea     buf_x0_bytes(pc),a1
                move.w  cur_min_xb(pc),(a1,d0.w)
                lea     buf_x1_bytes(pc),a2
                move.w  cur_max_xb(pc),(a2,d0.w)

                eori.w  #1,G_BUF_IDX.l
                bra.w   .ul_frame

.ul_round_end:
                clr.w   dl_recording
                clr.l   buf_dirty_ok
                jmp     GAME_BASE+$5ea
.ul_fight_end:
                clr.w   dl_recording
                clr.l   buf_dirty_ok
                jmp     GAME_BASE+$6da

flip_1vbl:
                lea     GAME_BASE+$a02.l,a0
                lsl.w   #2,d0
                andi.w  #7,d0
                move.l  (a0,d0.w),d1
                eori.w  #4,d0
                move.l  (a0,d0.w),G_SCR_BACK.l
                lsr.l   #8,d1
                move.b  d1,d2
                tst.w   G_SHAKE_FLAG.l
                beq.s   .f1_noshake
                tst.w   G_BUF_IDX.l
                beq.s   .f1_clrsh
                subi.b  #5,d2
.f1_clrsh:
                clr.w   G_SHAKE_FLAG.l
.f1_noshake:
                move.b  d2,$ffff8203.w
                lsr.l   #8,d1
                move.b  d1,$ffff8201.w
                clr.w   G_VBL_FLAG.l
.f1_wait:
                tst.w   G_VBL_FLAG.l
                beq.s   .f1_wait
                clr.w   G_VBL_FLAG.l
                rts

hook_spr_record:
                tst.w   dl_recording
                beq.s   call_orig_spr_draw
                move.w  dl_count(pc),d2
                cmpi.w  #16,d2
                bge.s   .rec_full
                mulu.w  #12,d2
                lea     dl_entries(pc),a0
                adda.w  d2,a0
                move.w  d0,0(a0)
                move.w  d6,2(a0)
                move.w  d4,4(a0)
                move.w  d5,6(a0)
                move.w  G_BLIT_MODE.l,8(a0)
                move.w  dl_cur_owner(pc),10(a0)
                addq.w  #1,dl_count
.rec_full:
                rts

call_orig_spr_draw:
                lsl.w   #2,d0
                lea     GAME_BASE+$243a.l,a0
                jmp     GAME_BASE+$2422

; =============================================================================
; 6. STAMINA SYSTEM, FATIGUE PENALTIES & HUD BARS
; =============================================================================
hook_fight_init:
                ; Replaces $3d6..$3e5 (init P1/P2 HP to $3f)
                move.w  #$3f,G_P1_HP.l
                move.w  #$3f,G_P2_HP.l
                move.w  #63,p1_max_stamina
                move.w  #63,p2_max_stamina
                clr.w   p1_combo
                clr.w   p2_combo
                clr.w   p1_combo_tmr
                clr.w   p2_combo_tmr
                clr.w   p1_best_combo
                clr.w   p1_head_streak
                clr.w   p2_head_streak
                clr.w   p1_daze_tmr
                clr.w   p2_daze_tmr
                clr.w   tow_val
                clr.w   p2_guard_stance
                clr.w   cpu_resting
                clr.w   ko_finisher_flag
                clr.w   stat_head
                clr.w   stat_body
                clr.w   stat_dazes
                clr.w   stat_blocks
                clr.w   stat_exh
                bsr.s   reset_stamina
                jmp     GAME_BASE+$3e6

hook_round_init:
                ; Replaces jsr $21e8 at $47a (new round: dropped max stamina persists within the fight!)
                jsr     GAME_BASE+$21e8
                clr.w   p1_combo
                clr.w   p2_combo
                clr.w   p1_head_streak
                clr.w   p2_head_streak
                clr.w   p1_daze_tmr
                clr.w   p2_daze_tmr
                clr.w   tow_val
                clr.w   p2_guard_stance
                clr.w   cpu_resting
                clr.w   ko_finisher_flag
                clr.w   stat_head
                clr.w   stat_body
                clr.w   stat_dazes
                clr.w   stat_blocks
                clr.w   stat_exh
                bsr.s   reset_stamina
                rts

reset_stamina:
                move.w  p1_max_stamina(pc),p1_stamina
                move.w  p2_max_stamina(pc),p2_stamina
                clr.w   p1_exhausted
                clr.w   p2_exhausted
                clr.w   p2_spec_cd
                move.w  #$ffff,p1_stam_drawn
                move.w  #$ffff,p2_stam_drawn
                bsr.w   draw_stamina_bars
                rts

; Drain P1 stamina by d0.w (sets p1_exhausted if hits 0, tracks stat_exh)
drain_p1_stamina:
                sub.w   d0,p1_stamina
                bgt.s   .dp1_ok
                clr.w   p1_stamina
                tst.w   p1_exhausted
                bne.s   .dp1_ok
                move.w  #1,p1_exhausted
                addq.w  #1,stat_exh
.dp1_ok:
                rts

; Drain P2 stamina by d0.w (sets p2_exhausted if hits 0)
drain_p2_stamina:
                sub.w   d0,p2_stamina
                bgt.s   .dp2_ok
                clr.w   p2_stamina
                move.w  #1,p2_exhausted
.dp2_ok:
                rts

; Reduce P1 max stamina by 4 (floor 24) when hit by 3+ combo
reduce_p1_max_stamina:
                subq.w  #4,p1_max_stamina
                cmpi.w  #24,p1_max_stamina
                bge.s   .rm1_ok
                move.w  #24,p1_max_stamina
.rm1_ok:
                move.w  p1_max_stamina(pc),d0
                cmp.w   p1_stamina(pc),d0
                bge.s   .rm1_done
                move.w  d0,p1_stamina
.rm1_done:
                move.w  #$ffff,p1_stam_drawn    ; force HUD bar redraw
                rts

; Reduce P2 max stamina by 4 (floor 24) when hit by 3+ combo
reduce_p2_max_stamina:
                subq.w  #4,p2_max_stamina
                cmpi.w  #24,p2_max_stamina
                bge.s   .rm2_ok
                move.w  #24,p2_max_stamina
.rm2_ok:
                move.w  p2_max_stamina(pc),d0
                cmp.w   p2_stamina(pc),d0
                bge.s   .rm2_done
                move.w  d0,p2_stamina
.rm2_done:
                move.w  #$ffff,p2_stam_drawn
                rts

; Called once per logic tick (16.7 Hz)
stamina_tick:
                ; Decay combo timers (2.0s window = 33 ticks)
                tst.w   p1_combo_tmr
                beq.s   .st_c2
                subq.w  #1,p1_combo_tmr
                bne.s   .st_c2
                clr.w   p1_combo
.st_c2:
                tst.w   p2_combo_tmr
                beq.s   .st_cd
                subq.w  #1,p2_combo_tmr
                bne.s   .st_cd
                clr.w   p2_combo
.st_cd:
                ; Defensive clamps: punch cooldown <= 2, daze <= 50, stamina <= max
                cmpi.w  #2,G_P1_PUNCH_CD.l
                ble.s   .st_dz1
                move.w  #2,G_P1_PUNCH_CD.l
.st_dz1:
                ; Decrement daze timers (50 ticks = 3.0s at 16.7 Hz)
                tst.w   p1_daze_tmr
                beq.s   .st_dz2
                subq.w  #1,p1_daze_tmr
.st_dz2:
                tst.w   p2_daze_tmr
                beq.s   .st_scd
                subq.w  #1,p2_daze_tmr
.st_scd:
                ; Decrement CPU special cooldown
                tst.w   p2_spec_cd
                beq.s   .st_p1
                subq.w  #1,p2_spec_cd
.st_p1:
                ; P1 regen (faster than CPU to balance CPU's instant guard reads!):
                ;   Normal: +1 every 3 ticks (~5.6/s); Speedster: +1 every 2 ticks (~8.3/s)
                tst.w   G_P1_HP.l               ; don't regen stamina while knocked down on canvas!
                beq.s   .st_p2
                tst.w   G_P1_STUN.l
                bne.s   .st_p2
                tst.w   G_P1_ATK_TYPE.l
                bgt.s   .st_p2
                addq.w  #1,p1_reg_div
                moveq   #3,d0
                cmpi.w  #1,cfg_style
                bne.s   .st_p1_div
                moveq   #2,d0
.st_p1_div:
                cmp.w   p1_reg_div(pc),d0
                bgt.s   .st_p2
                clr.w   p1_reg_div
.st_p1_add:
                move.w  p1_max_stamina(pc),d1
                cmp.w   p1_stamina(pc),d1
                ble.s   .st_p1_chk_rec
                addq.w  #1,p1_stamina
.st_p1_chk_rec:
                tst.w   p1_exhausted
                beq.s   .st_p2
                cmpi.w  #16,p1_stamina
                blt.s   .st_p2
                clr.w   p1_exhausted

.st_p2:
                ; P2 regen: CPU = +1 every 5 ticks (~3.3/s), 2P Human = +1 every 3 ticks (symmetric!)
                tst.w   G_P2_HP.l               ; don't regen stamina while knocked down on canvas!
                beq.s   .st_done
                tst.w   G_P2_STUN.l
                bne.s   .st_done
                tst.w   G_P2_ATK_ACT.l
                bne.s   .st_done
                addq.w  #1,p2_reg_div
                moveq   #5,d0                   ; CPU: slower regen (+1 / 5 ticks)
                tst.w   cfg_2p_mode
                beq.s   .st_p2_div
                moveq   #3,d0                   ; 2P Human: symmetric with P1 (+1 / 3 ticks)
.st_p2_div:
                cmp.w   p2_reg_div(pc),d0
                bgt.s   .st_done
                clr.w   p2_reg_div
                move.w  p2_max_stamina(pc),d1
                cmp.w   p2_stamina(pc),d1
                ble.s   .st_p2_chk_rec
                addq.w  #1,p2_stamina
.st_p2_chk_rec:
                tst.w   p2_exhausted
                beq.s   .st_done
                cmpi.w  #16,p2_stamina
                blt.s   .st_done
                clr.w   p2_exhausted
.st_done:
                rts

; Draw P1 & P2 Stamina bars at y=26..28 ($1060 / $10a0) on BOTH screens ($70000 & $78000)
; Shows: Gold (normal) / Red (exhausted) for [0..stamina], Black for [stamina..max],
;        Dark Grey (col 7 = p0|p1|p2) for lost max stamina [max..63]!
draw_stamina_bars:
                movem.l d0-d7/a0-a3,-(sp)
                ; Check P1 dirty (stamina | (mode<<8) | (max_stamina<<6))
                ; mode: 0=Gold, 1=Red (exhausted or daze off-phase), 2=Flash White (daze on-phase)
                move.w  p1_exhausted(pc),d1
                tst.w   p1_daze_tmr
                beq.s   .ds_p1_k
                moveq   #1,d1
                btst    #1,logic_tick_cnt+1(pc)
                beq.s   .ds_p1_k
                moveq   #2,d1
.ds_p1_k:
                move.w  d1,d3
                move.w  p1_stamina(pc),d0
                lsl.w   #8,d1
                or.w    d0,d1
                move.w  p1_max_stamina(pc),d2
                lsl.w   #6,d2
                eor.w   d2,d1
                cmp.w   p1_stam_drawn(pc),d1
                beq.s   .ds_p2
                move.w  d1,p1_stam_drawn
                move.w  p1_stamina(pc),d0
                move.w  d3,d1
                move.w  p1_max_stamina(pc),d7
                lea     $70000+$1060,a1
                lea     $78000+$1060,a2
                bsr.s   draw_bar_right_aligned

.ds_p2:
                move.w  p2_exhausted(pc),d1
                tst.w   p2_daze_tmr
                beq.s   .ds_p2_k
                moveq   #1,d1
                btst    #1,logic_tick_cnt+1(pc)
                beq.s   .ds_p2_k
                moveq   #2,d1
.ds_p2_k:
                move.w  d1,d3
                move.w  p2_stamina(pc),d0
                lsl.w   #8,d1
                or.w    d0,d1
                move.w  p2_max_stamina(pc),d2
                lsl.w   #6,d2
                eor.w   d2,d1
                cmp.w   p2_stam_drawn(pc),d1
                beq.s   .ds_done
                move.w  d1,p2_stam_drawn
                move.w  p2_stamina(pc),d0
                move.w  d3,d1
                move.w  p2_max_stamina(pc),d7
                lea     $70000+$10a0,a1
                lea     $78000+$10a0,a2
                bsr.w   draw_bar_left_aligned

.ds_done:
                movem.l (sp)+,d0-d7/a0-a3
                rts

; Helper: draw 64px x 3-line bar right-aligned (d0=val, d1=exhausted, d7=max_val, a1/a2=bufs)
draw_bar_right_aligned:
                ; Compute fill mask (d3) and lost-max grey mask (d7 -> temp on stack) per 16px chunk
                moveq   #64,d2
                sub.w   d0,d2                   ; d2 = empty bits from left (64 - val)
                moveq   #64,d4
                sub.w   d7,d4                   ; d4 = lost-max bits from left (64 - max)
                move.w  d4,bar_lost_cnt
                moveq   #3,d5
                moveq   #0,d6
.dbr_chk:
                ; Active fill mask (right-aligned)
                moveq   #0,d3
                cmpi.w  #16,d2
                bge.s   .dbr_empty
                tst.w   d2
                ble.s   .dbr_full
                move.w  #$ffff,d3
                lsr.w   d2,d3
                moveq   #0,d2
                bra.s   .dbr_lost
.dbr_empty:
                subi.w  #16,d2
                bra.s   .dbr_lost
.dbr_full:
                move.w  #$ffff,d3
.dbr_lost:
                ; Lost-max grey mask (left-aligned within bar_lost_cnt bits)
                moveq   #0,d7
                move.w  bar_lost_cnt(pc),d4
                ble.s   .dbr_write
                cmpi.w  #16,d4
                bge.s   .dbr_lfull
                moveq   #16,d0
                sub.w   d4,d0
                move.w  #$ffff,d7
                lsl.w   d0,d7
                clr.w   bar_lost_cnt
                bra.s   .dbr_write
.dbr_lfull:
                move.w  #$ffff,d7
                subi.w  #16,bar_lost_cnt
.dbr_write:
                bsr.s   write_3lines_chunk
                addq.w  #8,d6
                dbra    d5,.dbr_chk
                rts

; Helper: draw 64px x 3-line bar left-aligned (d0=val, d1=exhausted, d7=max_val, a1/a2=bufs)
draw_bar_left_aligned:
                move.w  d0,d2                   ; filled bits from left
                move.w  d7,bar_lost_cnt         ; valid max bits from left (grey is beyond this!)
                moveq   #3,d5
                moveq   #0,d6
.dbl_chk:
                moveq   #0,d3
                tst.w   d2
                ble.s   .dbl_lost
                cmpi.w  #16,d2
                bge.s   .dbl_full
                moveq   #16,d4
                sub.w   d2,d4
                move.w  #$ffff,d3
                lsl.w   d4,d3
                moveq   #0,d2
                bra.s   .dbl_lost
.dbl_full:
                move.w  #$ffff,d3
                subi.w  #16,d2
.dbl_lost:
                ; Lost-max grey mask = bits beyond bar_lost_cnt (right side of P2 bar!)
                moveq   #0,d7
                move.w  bar_lost_cnt(pc),d4
                cmpi.w  #16,d4
                bge.s   .dbl_lskip
                tst.w   d4
                ble.s   .dbl_lfull
                move.w  #$ffff,d7
                lsr.w   d4,d7                   ; right (16-d4) bits are lost-max grey!
                clr.w   bar_lost_cnt
                bra.s   .dbl_write
.dbl_lskip:
                subi.w  #16,bar_lost_cnt
                bra.s   .dbl_write
.dbl_lfull:
                move.w  #$ffff,d7
.dbl_write:
                bsr.s   write_3lines_chunk
                addq.w  #8,d6
                dbra    d5,.dbl_chk
                rts

; Write 16-px chunk: d3.w = fill (d1=0 Gold, d1=1 Red, d1=2 Daze Flash), d7.w = lost-max (Grey)
write_3lines_chunk:
                ; Gold (col 6): p0=0,  p1=d3, p2=d3, p3=0
                ; Red  (col 3): p0=d3, p1=d3, p2=0,  p3=0
                ; Grey (col 7): p0=d7, p1=d7, p2=d7, p3=0
                ; Daze (col 15): p0=p1=p2=p3=$ffff (flashing bar!)
                cmpi.w  #2,d1
                beq.s   .w3_daze
                tst.w   d1
                bne.s   .w3_red
                ; Gold + Grey: p0=d7, p1=d3|d7, p2=d3|d7, p3=0
                move.w  d7,d4
                swap    d4
                move.w  d3,d4
                or.w    d7,d4                   ; d4 = p0:p1
                move.w  d3,d0
                or.w    d7,d0
                swap    d0
                clr.w   d0                      ; d0 = p2:p3
                bra.s   .w3_put
.w3_daze:
                moveq   #-1,d4                  ; col 15 bright flash across whole bar!
                moveq   #-1,d0
                bra.s   .w3_put
.w3_red:
                ; Red + Grey: p0=d3|d7, p1=d3|d7, p2=d7, p3=0
                move.w  d3,d4
                or.w    d7,d4
                move.w  d4,d0
                swap    d4
                move.w  d0,d4                   ; d4 = p0:p1
                move.w  d7,d0
                swap    d0
                clr.w   d0                      ; d0 = p2:p3
.w3_put:
                lea     0(a1,d6.w),a0
                move.l  d4,0(a0)
                move.l  d0,4(a0)
                move.l  d4,160(a0)
                move.l  d0,164(a0)
                move.l  d4,320(a0)
                move.l  d0,324(a0)

                lea     0(a2,d6.w),a0
                move.l  d4,0(a0)
                move.l  d0,4(a0)
                move.l  d4,160(a0)
                move.l  d0,164(a0)
                move.l  d4,320(a0)
                move.l  d0,324(a0)
                rts

; =============================================================================
; 7. COMBAT HOOKS: STAMINA DRAIN, BODY SHOTS, 3-HIT COMBOS & +20% MOVEMENT
; =============================================================================
; P1 Left Punch ($1736): block if stamina < 10% (<6), else drain (-10, Iron Chin -7)
hook_p1_punch_l:
                cmpi.w  #6,p1_stamina
                blt.s   .pl_tired
                moveq   #10,d0
                cmpi.w  #3,cfg_style
                bne.s   .pl_dr
                moveq   #7,d0
.pl_dr:
                bsr.w   drain_p1_stamina
                jmp     GAME_BASE+$1742
.pl_tired:
                jmp     GAME_BASE+$1a80         ; too tired to punch -> movement/stance only

; P1 Right Punch ($1780): block if stamina < 10% (<6), else drain (-10, Iron Chin -7)
hook_p1_punch_r:
                cmpi.w  #6,p1_stamina
                blt.s   .pr_tired
                moveq   #10,d0
                cmpi.w  #3,cfg_style
                bne.s   .pr_dr
                moveq   #7,d0
.pr_dr:
                bsr.w   drain_p1_stamina
                jmp     GAME_BASE+$178c
.pr_tired:
                jmp     GAME_BASE+$1a80

; P1 Special KO Uppercut ($1b72): block if stamina < 10% (<6), else drain 22 & reset 2P tug-of-war!
hook_p1_special:
                cmpi.w  #6,p1_stamina
                blt.s   .ps_tired
                tst.w   cfg_2p_mode
                beq.s   .ps_go
                clr.w   tow_val
                bsr.w   sync_2p_tow
.ps_go:
                moveq   #22,d0
                bsr.w   drain_p1_stamina
                move.w  #$ffff,GAME_BASE+$2f56.l
                jmp     GAME_BASE+$1b7a
.ps_tired:
                jmp     GAME_BASE+$1b1a

; P1 Move Left ($1a9e): ~20% faster (Balanced 4, Speedster 5, Heavy/Iron 3, Exhausted 2)
hook_p1_move_l:
                bsr.s   get_p1_speed
                sub.w   d0,G_P1_X.l
                cmpi.w  #3,G_P1_X.l
                bge.s   .pml_ok
                move.w  #3,G_P1_X.l
.pml_ok:
                jmp     GAME_BASE+$1aa4

; P1 Move Right ($1abc):
hook_p1_move_r:
                bsr.s   get_p1_speed
                add.w   d0,G_P1_X.l
                cmpi.w  #$dd,G_P1_X.l
                ble.s   .pmr_ok
                move.w  #$dd,G_P1_X.l
.pmr_ok:
                jmp     GAME_BASE+$1ac2

get_p1_speed:
                tst.w   p1_exhausted
                beq.s   .gps_norm
                moveq   #2,d0                   ; exhausted: slower (2 vs 4)
                rts
.gps_norm:
                move.w  cfg_style(pc),d0
                cmpi.w  #1,d0                   ; Speedster: 5 px/tick
                beq.s   .gps_fast
                cmpi.w  #2,d0                   ; Heavy Hitter: 3 px/tick
                beq.s   .gps_slow
                cmpi.w  #3,d0                   ; Iron Chin: 3 px/tick
                beq.s   .gps_slow
                moveq   #4,d0                   ; Balanced: 4 px/tick (+25% faster!)
                rts
.gps_fast:
                moveq   #5,d0
                rts
.gps_slow:
                moveq   #3,d0
                rts

; P1 Punch Damage ($2b44): body-shot stamina hit + 3-hit combo + 3-head-hit DAZE!
; Inputs: a0 = G_OPP_STRUCT, d7 = punch index (0,2=High/Head, 4,6=Low/Body, 8=Special/Head)
hook_p1_dmg:
                ; P1 landed a hit -> breaks any head-hit streak against P1
                clr.w   p1_head_streak
                ; If AI is already dazed, further punches reset its 3.0s daze timer!
                tst.w   cfg_2p_mode
                bne.s   .p1d_body_chk
                tst.w   p2_daze_tmr
                beq.s   .p1d_body_chk
                move.w  #50,p2_daze_tmr
.p1d_body_chk:
                ; 1. Body-shot stamina impact & head-hit daze tracking
                cmpi.w  #4,d7
                beq.s   .p1d_body
                cmpi.w  #6,d7
                beq.s   .p1d_body
                ; Head hit (0, 2, 8): drain -3 stamina, increment P2 head-hit streak!
                addq.w  #1,stat_head
                addq.w  #1,p2_head_streak
                cmpi.w  #3,p2_head_streak
                blt.s   .p1d_head_st
                move.w  #50,p2_daze_tmr         ; 3 head hits in a row -> DAZED for 3.0s!
                addq.w  #1,stat_dazes
                clr.w   p2_head_streak
                tst.w   cfg_2p_mode
                bne.s   .p1d_head_st
                clr.w   G_P2_ATK_ACT.l          ; cancel any active CPU punch!
                move.w  #$ff00,GAME_BASE+$34aa.l ; force CPU evade!
.p1d_head_st:
                moveq   #3,d0
                bra.s   .p1d_stam
.p1d_body:
                addq.w  #1,stat_body
                clr.w   p2_head_streak          ; body hit resets head-hit streak
                moveq   #10,d0                  ; heavy body-shot stamina drain!
                ; Hagman (2 = weedy body) & Ronco (3 = stamina-weak) take extra -14 body drain!
                cmpi.w  #2,G_OPP_IDX.l
                beq.s   .p1d_body_ex
                cmpi.w  #3,G_OPP_IDX.l
                bne.s   .p1d_stam
.p1d_body_ex:
                moveq   #14,d0
.p1d_stam:
                bsr.w   drain_p2_stamina
                ; Reward human P1 with +6 stamina for landing a clean unblocked punch!
                addq.w  #6,p1_stamina
                move.w  p1_max_stamina(pc),d0
                cmp.w   p1_stamina(pc),d0
                bge.s   .p1d_r_ok
                move.w  d0,p1_stamina
.p1d_r_ok:
                cmpi.w  #16,p1_stamina
                blt.s   .p1d_combo
                clr.w   p1_exhausted
.p1d_combo:

                ; 2. Combo tracking: 3+ consecutive hits reduce opponent's MAX stamina!
                clr.w   p2_combo
                addq.w  #1,p1_combo
                move.w  #33,p1_combo_tmr        ; 2.0s combo chain window
                move.w  p1_combo(pc),d0
                cmp.w   p1_best_combo(pc),d0
                ble.s   .p1d_chk3
                move.w  d0,p1_best_combo
.p1d_chk3:
                cmpi.w  #3,d0
                blt.s   .p1d_dmg
                bsr.w   reduce_p2_max_stamina

.p1d_dmg:
                move.w  $14(a0,d7.w),d6
                tst.w   p1_exhausted
                beq.s   .p1d_style
                lsr.w   #1,d6
                bne.s   .p1d_apply
                moveq   #1,d6
                bra.s   .p1d_apply
.p1d_style:
                move.w  cfg_style(pc),d0
                cmpi.w  #1,d0                   ; Speedster: -1 dmg (min 2) so hits always register!
                bne.s   .p1d_chk_hvy
                subq.w  #1,d6
                cmpi.w  #2,d6
                bge.s   .p1d_apply
                moveq   #2,d6
                bra.s   .p1d_apply
.p1d_chk_hvy:
                cmpi.w  #2,d0                   ; Heavy Hitter: +50% power!
                bne.s   .p1d_apply
                move.w  d6,d0
                lsr.w   #1,d0
                addq.w  #1,d0
                add.w   d0,d6
.p1d_apply:
                sub.w   d6,G_P2_HP.l
                ; If this blow dropped P2 (HP <= 0), record whether it was a KO Super finisher (d7==8)!
                tst.w   G_P2_HP.l
                bgt.s   .p1d_ret
                clr.w   ko_finisher_flag
                cmpi.w  #8,d7
                bne.s   .p1d_ret
                move.w  #1,ko_finisher_flag
.p1d_ret:
                jmp     GAME_BASE+$2b4e

; P2 Punch Damage ($38a6): body-shot stamina hit + 3-hit combo + 3-head-hit DAZE!
; Inputs: a0 = G_OPP_STRUCT, d7 = attack index (0,2,4); $5e(a0,d7.w) != 0 means LOW body shot!
hook_p2_dmg:
                ; P2 landed a hit -> breaks any head-hit streak against P2
                clr.w   p2_head_streak
                ; 1. Body-shot stamina impact & head-hit daze tracking
                tst.w   $5e(a0,d7.w)
                bne.s   .p2d_body
                ; Head hit: drain -3 stamina, increment P1 head-hit streak!
                addq.w  #1,p1_head_streak
                cmpi.w  #3,p1_head_streak
                blt.s   .p2d_head_st
                move.w  #50,p1_daze_tmr         ; 3 head hits in a row -> P1 DAZED for 3.0s!
                clr.w   p1_head_streak
.p2d_head_st:
                moveq   #3,d0
                bra.s   .p2d_stam
.p2d_body:
                clr.w   p1_head_streak
                moveq   #10,d0
.p2d_stam:
                bsr.w   drain_p1_stamina
                ; In 2P mode ONLY (never CPU!), reward human P2 with +6 stamina for landing a clean hit!
                tst.w   cfg_2p_mode
                beq.s   .p2d_combo
                addq.w  #6,p2_stamina
                move.w  p2_max_stamina(pc),d0
                cmp.w   p2_stamina(pc),d0
                bge.s   .p2d_r_ok
                move.w  d0,p2_stamina
.p2d_r_ok:
                cmpi.w  #16,p2_stamina
                blt.s   .p2d_combo
                clr.w   p2_exhausted
.p2d_combo:

                ; 2. Combo tracking: 3+ consecutive hits reduce player's MAX stamina!
                clr.w   p1_combo
                addq.w  #1,p2_combo
                move.w  #33,p2_combo_tmr
                cmpi.w  #3,p2_combo
                blt.s   .p2d_dmg
                bsr.w   reduce_p1_max_stamina

.p2d_dmg:
                move.w  $30(a0,d7.w),d6
                tst.w   p2_exhausted
                beq.s   .p2d_chin
                lsr.w   #1,d6
                bne.s   .p2d_chin
                moveq   #1,d6
.p2d_chin:
                move.w  cfg_style(pc),d0
                cmpi.w  #2,d0                   ; Heavy Hitter = Glass Jaw (+40% dmg taken!)
                bne.s   .p2d_chk_iron
                move.w  d6,d0
                lsr.w   #1,d0
                add.w   d0,d6
                bra.s   .p2d_apply
.p2d_chk_iron:
                cmpi.w  #3,d0                   ; Iron Chin (-25% dmg taken!)
                bne.s   .p2d_apply
                move.w  d6,d0
                lsr.w   #2,d0
                sub.w   d0,d6
                bgt.s   .p2d_apply
                moveq   #1,d6
.p2d_apply:
                sub.w   d6,G_P1_HP.l
                ; If this blow dropped P1 (HP <= 0), record whether it was a Special finisher (d7==4)!
                tst.w   G_P1_HP.l
                bgt.s   .p2d_tow
                clr.w   ko_finisher_flag
                cmpi.w  #4,d7
                bne.s   .p2d_tow
                move.w  #1,ko_finisher_flag
.p2d_tow:
                ; In 2P mode, P2 landing a clean punch pulls the KO tug-of-war RIGHT (+1, max +3)!
                tst.w   cfg_2p_mode
                beq.s   .p2d_ret
                cmpi.w  #3,tow_val
                bge.s   .p2d_ret
                addq.w  #1,tow_val
                bsr.w   sync_2p_tow
.p2d_ret:
                jmp     GAME_BASE+$38b0

; Blocking drains MORE stamina (-9) for both P1 and P2, and breaks head-hit streaks!
hook_p2_block:
                clr.w   p2_head_streak
                moveq   #9,d0
                bsr.w   drain_p2_stamina
                move.l  #GAME_BASE+$34fe,-(sp)
                jmp     GAME_BASE+$2bbe

hook_p1_block:
                tst.w   GAME_BASE+$374c.l
                bne.s   .p1b_skip
                clr.w   p1_head_streak
                addq.w  #1,stat_blocks
                moveq   #9,d0
                bsr.w   drain_p1_stamina
.p1b_skip:
                tst.w   GAME_BASE+$374c.l
                jmp     GAME_BASE+$3918

; Opponent movement ($1392 add, $13a8 sub): halve when exhausted!
hook_opp_move_add:
                tst.w   p2_exhausted
                beq.s   .oma_ok
                lsr.w   #1,d0
                bne.s   .oma_ok
                btst    #0,logic_tick_cnt+1(pc)
                beq.s   .oma_skip
                moveq   #1,d0
.oma_ok:
                add.w   d0,G_P2_X.l
.oma_skip:
                jmp     GAME_BASE+$1398

hook_opp_move_sub:
                tst.w   p2_exhausted
                beq.s   .oms_ok
                lsr.w   #1,d0
                bne.s   .oms_ok
                btst    #0,logic_tick_cnt+1(pc)
                beq.s   .oms_skip
                moveq   #1,d0
.oms_ok:
                sub.w   d0,G_P2_X.l
.oms_skip:
                jmp     GAME_BASE+$13ae

; Opponent attack initiation: block if dazed, exhausted, stamina < 10%, or CPU resting!
hook_opp_punch_a:
                tst.w   p2_daze_tmr
                bne.s   .opa_skip
                tst.w   p2_exhausted
                bne.s   .opa_skip
                cmpi.w  #6,p2_stamina
                blt.s   .opa_skip
                tst.w   cfg_2p_mode
                bne.s   .opa_go
                tst.w   cpu_resting
                bne.s   .opa_skip
.opa_go:
                moveq   #10,d0
                bsr.w   drain_p2_stamina
                lea     G_OPP_STRUCT.l,a0
                jmp     GAME_BASE+$156e
.opa_skip:
                rts

hook_opp_punch_b:
                tst.w   p2_daze_tmr
                bne.s   .opb_skip
                tst.w   p2_exhausted
                bne.s   .opb_skip
                cmpi.w  #6,p2_stamina
                blt.s   .opb_skip
                tst.w   cfg_2p_mode
                bne.s   .opb_go
                tst.w   cpu_resting
                bne.s   .opb_skip
.opb_go:
                moveq   #10,d0
                bsr.w   drain_p2_stamina
                lea     G_OPP_STRUCT.l,a0
                jmp     GAME_BASE+$15d8
.opb_skip:
                rts

hook_opp_special:
                tst.w   p2_daze_tmr
                bne.s   .ops_skip
                tst.w   cfg_2p_mode
                beq.s   .ops_cpu
                ; 2P Mode: P2 Super requires >=10% stamina (>=6) & Tug-of-War pulled to +3!
                cmpi.w  #6,p2_stamina
                blt.s   .ops_skip
                cmpi.w  #3,tow_val
                blt.s   .ops_skip
                clr.w   tow_val
                bsr.w   sync_2p_tow
                bra.s   .ops_go
.ops_cpu:
                tst.w   p2_exhausted
                bne.s   .ops_skip
                tst.w   cpu_resting
                bne.s   .ops_skip
                cmpi.w  #30,p2_stamina          ; Smart CPU: save Specials for >=30 stamina!
                blt.s   .ops_skip
                tst.w   p2_spec_cd
                bne.s   .ops_skip
                move.w  #25,p2_spec_cd
.ops_go:
                moveq   #22,d0
                bsr.w   drain_p2_stamina
                lea     G_OPP_STRUCT.l,a0
                jmp     GAME_BASE+$15a2
.ops_skip:
                rts

; =============================================================================
; 8. FIGHTER AI REBALANCE & HIGH/LOW WEAKNESS PROFILES
; =============================================================================
; Replaces $2d24: copies opponent struct from EMPTY.TOS, then applies distinct tactical profiles!
; $14/$16 = High L/R dmg taken, $18/$1a = Low L/R dmg taken, $1c = Special dmg taken
hook_load_opp:
                move.w  d0,d1                   ; save fighter index (0..4)
                lsl.w   #2,d0
                lea     GAME_BASE+$534e.l,a0
                movea.l (a0,d0.w),a0
                adda.l  #GAME_BASE+$534e,a0
                lea     G_OPP_STRUCT.l,a1
                move.b  #$86,d0
.lo_cp:
                move.w  (a0)+,(a1)+
                subq.b  #2,d0
                bne.s   .lo_cp

                lea     G_OPP_STRUCT.l,a0
                cmpi.w  #1,d1
                beq.s   .bal_jones
                cmpi.w  #2,d1
                beq.s   .bal_hagman
                cmpi.w  #3,d1
                beq.w   .bal_ronco
                cmpi.w  #4,d1
                beq.w   .bal_malone
                ; Joe Weed (0): Glass Jaw — weak up top (High 5 / Low 3 / Spec 8)
                move.w  #150,$3a(a0)
                move.w  #5,$14(a0)
                move.w  #5,$16(a0)
                move.w  #3,$18(a0)
                move.w  #3,$1a(a0)
                move.w  #8,$1c(a0)
                bra.w   .bal_init_tmr
.bal_jones:
                ; B. Jones (1): Muscular Brawler — rock-solid abs (Low 3), open chin (High 5 / Spec 8)
                move.w  #14,$20(a0)
                move.w  #130,$3a(a0)
                move.w  #5,$14(a0)
                move.w  #5,$16(a0)
                move.w  #3,$18(a0)
                move.w  #3,$1a(a0)
                move.w  #8,$1c(a0)
                bra.w   .bal_init_tmr
.bal_hagman:
                ; M. "Hammerhead" Hagman (2): Iron Skull (High 2!), Soft Weedy Body (Low 6 + -14 stam!)
                move.w  #12,$20(a0)
                move.w  #115,$3a(a0)
                move.w  #2,$14(a0)
                move.w  #2,$16(a0)
                move.w  #6,$18(a0)
                move.w  #6,$1a(a0)
                move.w  #8,$1c(a0)
                move.w  #2,$7e(a0)
                move.w  #2,$82(a0)
                bra.s   .bal_init_tmr
.bal_ronco:
                ; J. Ronco (3): Tight Guard Technician (High 3 / Low 4, -14 body stam drain!)
                move.w  #10,$20(a0)
                move.w  #100,$3a(a0)
                move.w  #3,$14(a0)
                move.w  #3,$16(a0)
                move.w  #4,$18(a0)
                move.w  #4,$1a(a0)
                move.w  #7,$1c(a0)
                move.w  #2,$7e(a0)
                move.w  #2,$82(a0)
                bra.s   .bal_init_tmr
.bal_malone:
                ; M. Malone (4): Complete Champion (High 4 / Low 4 / Spec 8)
                move.w  #8,$20(a0)
                move.w  #90,$3a(a0)
                move.w  #2,$1e(a0)
                move.w  #12,$34(a0)
                move.w  #4,$14(a0)
                move.w  #4,$16(a0)
                move.w  #4,$18(a0)
                move.w  #4,$1a(a0)
                move.w  #8,$1c(a0)
.bal_init_tmr:
                move.w  $3a(a0),GAME_BASE+$34b0.l ; seed CPU regen countdown cleanly
                rts

; Reactive AI ($360c): skip when dazed, exhausted, or resting + 50% fair-read gate!
hook_cpu_react:
                tst.w   p2_daze_tmr
                bne.s   .cr_skip
                tst.w   p2_exhausted
                bne.s   .cr_skip
                tst.w   cpu_resting
                bne.s   .cr_skip
                ; 50% fair-read gate when timer is about to trigger ($2f52 == 1)
                cmpi.w  #1,GAME_BASE+$2f52.l
                bne.s   .cr_orig
                btst    #1,logic_tick_cnt+1(pc) ; pseudo-random 50% window
                beq.s   .cr_orig
                ; Reset timer without telepathic counter-read
                lea     G_OPP_STRUCT.l,a0
                move.w  $20(a0),GAME_BASE+$2f52.l
                rts
.cr_orig:
                tst.w   G_P2_DUCK.l
                jmp     GAME_BASE+$3612
.cr_skip:
                rts

; Auto-block ($4ab8, opcode 13): skip when dazed or exhausted!
hook_react_blk:
                tst.w   p2_daze_tmr
                bne.s   .rb_skip
                tst.w   p2_exhausted
                bne.s   .rb_skip
                tst.w   G_P2_ATK_ACT.l
                jmp     GAME_BASE+$4abe
.rb_skip:
                rts

; =============================================================================
; 9. 2-PLAYER MODE & DAZED CONTROL REVERSAL
; =============================================================================
hook_opp_ai_entry:
                tst.w   cfg_2p_mode
                bne.w   p2_human_ctrl
                ; If CPU is dazed, force evade/retreat flag ($34aa) so it only backs off!
                tst.w   p2_daze_tmr
                bne.s   .oae_evade
                ; Smarter CPU stamina management (hysteresis breather per fighter!):
                ; Ronco (3) & Malone (4) press aggressively if player is dazed or exhausted!
                move.w  G_OPP_IDX.l,d0
                cmpi.w  #3,d0
                blt.s   .oae_stam
                tst.w   p1_daze_tmr
                bne.s   .oae_push
                tst.w   p1_exhausted
                beq.s   .oae_stam
.oae_push:
                clr.w   cpu_resting
                bra.s   .oae_go
.oae_stam:
                ; Thresholds: Weed=12/26, Jones=14/28, Hagman=20/34, Ronco=22/36, Malone=22/38
                cmpi.w  #4,d0
                ble.s   .oae_idx_ok
                moveq   #4,d0
.oae_idx_ok:
                add.w   d0,d0
                lea     cpu_rest_lo(pc),a1
                move.w  (a1,d0.w),d1            ; low threshold -> start resting
                lea     cpu_rest_hi(pc),a1
                move.w  (a1,d0.w),d2            ; high threshold -> resume fighting
                ; Cap recovery target to p2_max_stamina - 4 so reduced max doesn't trap CPU resting!
                move.w  p2_max_stamina(pc),d3
                subq.w  #4,d3
                cmp.w   d3,d2
                ble.s   .oae_hi_ok
                move.w  d3,d2
.oae_hi_ok:
                tst.w   cpu_resting
                bne.s   .oae_chk_rec
                cmp.w   p2_stamina(pc),d1       ; if p2_stamina <= low_thresh -> rest!
                blt.s   .oae_go
                move.w  #1,cpu_resting
                bra.s   .oae_evade
.oae_chk_rec:
                cmp.w   p2_stamina(pc),d2       ; if p2_stamina >= hi_thresh -> resume!
                bgt.s   .oae_evade
                clr.w   cpu_resting
                bra.s   .oae_go
.oae_evade:
                move.w  #$ff00,GAME_BASE+$34aa.l
.oae_go:
                lea     G_OPP_STRUCT.l,a0
                jmp     GAME_BASE+$1352

cpu_rest_lo:    dc.w    12, 14, 20, 22, 22
cpu_rest_hi:    dc.w    26, 28, 34, 36, 38

; Wrapper for P1 logic ($196e): when dazed, reverses directions & disables Fire!
; Uses race-free raw_joy1 captured by hook_ikbd_joy1 so IKBD packets are NEVER lost or stuck!
call_p1_with_daze:
                tst.w   p1_daze_tmr
                bne.s   .cpd_dazed
                jmp     GAME_BASE+$196e
.cpd_dazed:
                move.b  G_JOY1.l,d0             ; works for both real IKBD and debugger writes!
                move.b  d0,raw_joy1
                bsr.s   scramble_daze_byte
                move.b  d0,G_JOY1.l
                jsr     GAME_BASE+$196e
                move.b  raw_joy1(pc),G_JOY1.l   ; always restore latest true IKBD Joy 1!
                rts

; Reverse Up<->Down (bits 0<->1), Left<->Right (bits 2<->3), clear Fire (bit 7)
scramble_daze_byte:
                moveq   #0,d1
                btst    #0,d0
                beq.s   .sdb1
                bset    #1,d1                   ; Up -> Down
.sdb1:          btst    #1,d0
                beq.s   .sdb2
                bset    #0,d1                   ; Down -> Up
.sdb2:          btst    #2,d0
                beq.s   .sdb3
                bset    #3,d1                   ; Left -> Right
.sdb3:          btst    #3,d0
                beq.s   .sdb4
                bset    #2,d1                   ; Right -> Left
.sdb4:          move.b  d1,d0
                rts

p2_human_ctrl:
                ; If hit-stunned ($2f54 != 0), run normal hit-stun decay at $13ea
                tst.w   G_P2_STUN.l
                bne.w   .p2h_stun
                ; If ducking ($3600 != 0), advance duck anim at $35a6
                tst.w   G_P2_DUCK.l
                beq.s   .p2h_chk_atk
                jsr     GAME_BASE+$35a6
                jmp     GAME_BASE+$14fe
.p2h_chk_atk:
                ; If currently punching ($2f5a != 0), advance attack animation at $1460!
                tst.w   G_P2_ATK_ACT.l
                beq.s   .p2h_input
                ; Advance attack frame (inline $1460..$14ae, then draw at $14fe!)
                subq.w  #1,GAME_BASE+$2f5c.l
                bne.w   .p2h_draw
                lea     G_OPP_STRUCT.l,a0
                move.w  GAME_BASE+$44ce.l,d0
                move.w  $7e(a0,d0.w),GAME_BASE+$2f5c.l
                addq.w  #1,G_P2_FRM.l
                moveq   #5,d0
                cmpi.w  #$12,G_P2_GRP.l
                bne.s   .p2h_nf
                moveq   #6,d0
.p2h_nf:
                cmp.w   G_P2_FRM.l,d0
                bgt.w   .p2h_draw
                clr.w   G_P2_ATK_ACT.l
                clr.w   G_P2_FRM.l
                bra.w   .p2h_draw

.p2h_input:
                ; Read combined P2 input: Joy 0 ($3fef) OR Keyboard (W/A/S/D + LShift)
                move.b  G_JOY0.l,d7
                lea     G_KEY_BASE.l,a1
                tst.b   KEY_W(a1)
                beq.s   .k_no_w
                bset    #0,d7                   ; Up
.k_no_w:
                tst.b   KEY_S(a1)
                beq.s   .k_no_s
                bset    #1,d7                   ; Down
.k_no_s:
                tst.b   KEY_A(a1)
                beq.s   .k_no_a
                bset    #2,d7                   ; Left
.k_no_a:
                tst.b   KEY_D(a1)
                beq.s   .k_no_d
                bset    #3,d7                   ; Right
.k_no_d:
                tst.b   KEY_LSHIFT(a1)
                beq.s   .k_no_f
                bset    #7,d7                   ; Fire
.k_no_f:
                ; If P2 human is dazed, reverse controls and disable punches!
                tst.w   p2_daze_tmr
                beq.s   .p2h_no_daze
                move.b  d7,d0
                bsr.w   scramble_daze_byte
                move.b  d0,d7
.p2h_no_daze:
                ; Check Fire + direction = Attack / Duck!
                btst    #7,d7
                beq.s   .p2h_move_guard
                btst    #0,d7                   ; Fire + Up = Special!
                beq.s   .p2h_chk_fl
                jsr     GAME_BASE+$159c
                bra.w   .p2h_draw
.p2h_chk_fl:
                ; Fire + Left OR Fire + Right = High Punch ($1568) if High Stance, Low Punch ($15d2) if Low Stance!
                move.b  d7,d0
                andi.b  #$0c,d0                 ; Left (bit 2) or Right (bit 3)?
                beq.s   .p2h_chk_fd
                tst.w   p2_guard_stance
                bne.s   .p2h_do_low
                clr.w   G_OPP_STRUCT+$5e.l      ; guarantee Punch A is High/Head (even for Hagman!)
                jsr     GAME_BASE+$1568         ; High Punch (Head)
                bra.w   .p2h_draw
.p2h_do_low:
                jsr     GAME_BASE+$15d2         ; Low Punch (Body shot!)
                bra.w   .p2h_draw
.p2h_chk_fd:
                btst    #1,d7                   ; Fire + Down = Duck!
                beq.w   .p2h_draw
                move.w  #$ffff,G_P2_DUCK.l
                clr.w   G_P2_FRM.l
                moveq   #4,d0
                bsr.w   drain_p2_stamina
                bra.w   .p2h_draw

.p2h_move_guard:
                ; Movement: ~20% faster (4 normal, 2 exhausted)
                moveq   #4,d0
                tst.w   p2_exhausted
                beq.s   .p2h_m_go
                moveq   #2,d0
.p2h_m_go:
                btst    #2,d7                   ; Left
                beq.s   .p2h_mr
                sub.w   d0,G_P2_X.l
                cmpi.w  #6,G_P2_X.l
                bge.s   .p2h_mr
                move.w  #6,G_P2_X.l
.p2h_mr:
                btst    #3,d7                   ; Right
                beq.s   .p2h_guard
                add.w   d0,G_P2_X.l
                cmpi.w  #$dc,G_P2_X.l
                ble.s   .p2h_guard
                move.w  #$dc,G_P2_X.l
.p2h_guard:
                ; Sticky Guard (matches P1!): Up -> High Guard (0), Down -> Low Guard (1), stays set!
                btst    #0,d7
                beq.s   .p2h_chk_dn
                clr.w   p2_guard_stance
                bra.s   .p2h_apply_g
.p2h_chk_dn:
                btst    #1,d7
                beq.s   .p2h_apply_g
                move.w  #1,p2_guard_stance
.p2h_apply_g:
                tst.w   p2_guard_stance
                bne.s   .p2h_glo
                jsr     GAME_BASE+$1674         ; High guard
                bra.w   .p2h_draw
.p2h_glo:
                jsr     GAME_BASE+$168a         ; Low guard
.p2h_draw:
                jmp     GAME_BASE+$14fe

.p2h_stun:
                subq.w  #1,GAME_BASE+$1168.l
                bne.s   .p2h_draw
                move.w  #3,GAME_BASE+$1168.l
                clr.w   G_P2_STUN.l
                bra.w   .p2h_draw

; =============================================================================
; 10. TITLE SCREEN MENU (F1: 1P/2P, F2: STYLE, F3: OPPONENT, CREDIT LINE)
; =============================================================================
hook_title_draw:
                ; Draw our enhanced menu & credit in the left/right title boxes!
                bsr.w   render_title_options
                move.l  #$68300,d1              ; original instruction at $1d54
                jmp     GAME_BASE+$1d5a

hook_title_poll1:
                bsr.w   poll_title_keys
                btst.b  #7,G_JOY1.l
                beq.s   .htp1_wait
                bsr.s   on_title_fire
                jmp     GAME_BASE+$1db2         ; Fire pressed -> go straight into fight!
.htp1_wait:
                jmp     GAME_BASE+$1d78

hook_title_poll2:
                bsr.w   poll_title_keys
                btst.b  #7,G_JOY1.l
                beq.s   .htp2_wait
                bsr.s   on_title_fire
                jmp     GAME_BASE+$1db2         ; Fire pressed -> go straight into fight!
.htp2_wait:
                jmp     GAME_BASE+$1e4c

; Called right when Fire is pressed on the title screen:
; loads F3/2P opponent if needed, shows Pre-Fight THE RING SUN preview in 1P Career,
; and restores $70000 cleanly before the game's single $1cba scroll-down!
on_title_fire:
                bsr.w   clear_bottom_credit
                moveq   #0,d7                   ; d7=1 if $70000 was used as scratch
                tst.w   cfg_2p_mode
                bne.s   .otf_load
                tst.w   opp_picked_f3
                beq.s   .otf_chk_pre
.otf_load:
                clr.w   opp_picked_f3
                move.w  cfg_2p_opp(pc),G_OPP_IDX.l
                jsr     GAME_BASE+$44d2         ; unpack chosen opponent BxA/B/C.CSP (uses $70000!)
                jsr     GAME_BASE+$4428         ; clear title option boxes
                jsr     GAME_BASE+$4572         ; draw MARCO vs chosen opponent Tale-of-the-Tape!
                moveq   #1,d7
.otf_chk_pre:
                ; In 1P Career mode, show Pre-Fight THE RING SUN with opponent scouting report!
                tst.w   cfg_2p_mode
                bne.s   .otf_chk_rst
                move.w  #1,np_is_preview
                bsr.w   draw_newspaper_common
                clr.w   np_is_preview
                ; Restore title screen ($68300) display before $1cba scrolls down into $70000!
                move.b  #$06,$ffff8201.w
                move.b  #$83,$ffff8203.w
                moveq   #1,d7
.otf_chk_rst:
                tst.w   d7
                beq.s   .otf_done
                ; Restore $70000 cleanly: copy untouched HUD top ($78000->$70000) + $10ec ring BG!
                movem.l d0/a0-a1,-(sp)
                lea     $78000,a0
                lea     $70000,a1
                move.w  #2400-1,d0
.otf_hud_cp:
                move.l  (a0)+,(a1)+
                dbra    d0,.otf_hud_cp
                movem.l (sp)+,d0/a0-a1
                move.l  #$70000,G_SCR_BACK.l
                jsr     GAME_BASE+$10ec
.otf_done:
                rts

; Clear the discreet 2-line bottom credit in the middle bridge (y=161..177, x=96..223)
clear_bottom_credit:
                movem.l d0-d1/a0-a1,-(sp)
                lea     $68300+161*160+$30,a0   ; x=96 ($30)
                moveq   #17-1,d1
.cbc_row:
                movea.l a0,a1
                moveq   #16-1,d0                ; 16 longs = 64 bytes = 128 px (x=96..223)
.cbc_col:
                clr.l   (a1)+
                dbra    d0,.cbc_col
                adda.w  #$a0,a0
                dbra    d1,.cbc_row
                movem.l (sp)+,d0-d1/a0-a1
                rts

poll_title_keys:
                lea     G_KEY_BASE.l,a0
                ; F1: toggle 1P Career / 2P Versus
                tst.b   KEY_F1(a0)
                beq.s   .pt_f1_up
                tst.w   key_f1_held
                bne.s   .pt_chk_f2
                move.w  #1,key_f1_held
                eori.w  #1,cfg_2p_mode
                bsr.w   render_title_options
                bra.s   .pt_chk_f2
.pt_f1_up:
                clr.w   key_f1_held
.pt_chk_f2:
                ; F2: cycle Career Fighting Style (0..3)
                tst.b   KEY_F2(a0)
                beq.s   .pt_f2_up
                tst.w   key_f2_held
                bne.s   .pt_chk_f3
                move.w  #1,key_f2_held
                addq.w  #1,cfg_style
                andi.w  #3,cfg_style
                bsr.w   render_title_options
                bra.s   .pt_chk_f3
.pt_f2_up:
                clr.w   key_f2_held
.pt_chk_f3:
                ; F3: cycle Opponent (0..4) when in 2P mode
                tst.b   KEY_F3(a0)
                beq.s   .pt_f3_up
                tst.w   key_f3_held
                bne.s   .pt_done
                move.w  #1,key_f3_held
                addq.w  #1,cfg_2p_opp
                cmpi.w  #5,cfg_2p_opp
                blt.s   .pt_f3_ok
                clr.w   cfg_2p_opp
.pt_f3_ok:
                move.w  #1,opp_picked_f3
                ; Do NOT call $44d2 on the title screen (title wipe overwrites $60000)!
                ; Chosen opponent is loaded cleanly in hook_fight_init after leaving title screen.
                bsr.w   render_title_options
                bra.s   .pt_done
.pt_f3_up:
                clr.w   key_f3_held
.pt_done:
                rts

render_title_options:
                movem.l d0-d7/a0-a6,-(sp)
                ; Only draw on initial title (opp_idx == 0 or 2P mode)
                ; Clear both title boxes first ($4428)
                jsr     GAME_BASE+$4428
                ; Left box ($6bd28 + 1 byte = 8px left margin!): Controls
                lea     $6bd29,a6
                movea.l a6,a4
                lea     str_controls(pc),a5
                jsr     G_ORIG_PRINT

                ; Discreet 2-line credit strictly inside middle bridge (x=104..207, y=162..176)
                ; Never clipped when left/right title boxes cycle!
                bsr.w   clear_bottom_credit
                lea     $68300+162*160+$31,a6   ; x=104 (centered 13 chars inside x=96..223!)
                movea.l a6,a4
                lea     str_bottom_credit(pc),a5
                jsr     G_ORIG_PRINT

                ; Right box ($6bd90 + 1 byte = 8px left margin!): Mode + Style + Opponent
                lea     $6bd91,a6
                movea.l a6,a4
                lea     str_mode_1p(pc),a5
                tst.w   cfg_2p_mode
                beq.s   .rto_m
                lea     str_mode_2p(pc),a5
.rto_m:
                jsr     G_ORIG_PRINT

                ; Style line (+24 scanlines = $0f00)
                lea     $6bd91+$0f00,a6
                movea.l a6,a4
                move.w  cfg_style(pc),d0
                add.w   d0,d0
                add.w   d0,d0
                lea     style_str_tbl(pc),a0
                movea.l (a0,d0.w),a5
                jsr     G_ORIG_PRINT

                ; Opponent line (+48 scanlines = $1e00)
                ; In 1P Career (if F3 wasn't pressed), sync displayed OPP with actual scheduled G_OPP_IDX!
                tst.w   cfg_2p_mode
                bne.s   .rto_opp
                tst.w   opp_picked_f3
                bne.s   .rto_opp
                move.w  G_OPP_IDX.l,d0
                cmpi.w  #4,d0
                ble.s   .rto_sync
                moveq   #4,d0
.rto_sync:
                move.w  d0,cfg_2p_opp
.rto_opp:
                lea     $6bd91+$1e00,a6
                movea.l a6,a4
                move.w  cfg_2p_opp(pc),d0
                add.w   d0,d0
                add.w   d0,d0
                lea     opp_str_tbl(pc),a0
                movea.l (a0,d0.w),a5
                jsr     G_ORIG_PRINT

                movem.l (sp)+,d0-d7/a0-a6
                rts

; =============================================================================
; Title Screen Strings (Game font: 0..9 = $00..$09, A..Z = $41..$5a, ' '=$5b, '.'=$5c, NL=$ff, END=$fe)
; =============================================================================
str_controls:
                dc.b    'O','P','T','I','O','N','S',$ff,$ff
                dc.b    'F',1,$5b,'M','O','D','E',$ff
                dc.b    'F',2,$5b,'S','T','Y','L','E',$ff
                dc.b    'F',3,$5b,'O','P','P',$ff,$ff,$ff
                dc.b    $5b,'P','R','E','S','S',$ff
                dc.b    $5b,$5b,'F','I','R','E',$fe

str_bottom_credit:
                dc.b    'E','N','H','A','N','C','E','D',$5b,'V',1,$5c,1,$ff
                dc.b    $5b,$5b,'B','Y',$5b,'D','A','D',$5b,'P','R','G',$fe

str_mode_1p:
                dc.b    'M','O','D','E',$ff
                dc.b    1,'P',$5b,'C','A','R','E','E','R',$fe
str_mode_2p:
                dc.b    'M','O','D','E',$ff
                dc.b    2,'P',$5b,'W','A','S','D',$fe

str_st_bal:     dc.b    'S','T','Y','L','E',$ff,'B','A','L','A','N','C','E','D',$fe
str_st_spd:     dc.b    'S','T','Y','L','E',$ff,'S','P','E','E','D','S','T','E','R',$fe
str_st_hvy:     dc.b    'S','T','Y','L','E',$ff,'H','E','A','V','Y',$5b,'H','I','T',$fe
str_st_irn:     dc.b    'S','T','Y','L','E',$ff,'I','R','O','N',$5b,'C','H','I','N',$fe

str_opp_0:      dc.b    'O','P','P',$ff,'J','O','E',$5b,'W','E','E','D',$fe
str_opp_1:      dc.b    'O','P','P',$ff,'B',$5c,'J','O','N','E','S',$fe
str_opp_2:      dc.b    'O','P','P',$ff,'M',$5c,'H','A','G','M','A','N',$fe
str_opp_3:      dc.b    'O','P','P',$ff,'J',$5c,'R','O','N','C','O',$fe
str_opp_4:      dc.b    'O','P','P',$ff,'M',$5c,'M','A','L','O','N','E',$fe

                even
style_str_tbl:  dc.l    str_st_bal, str_st_spd, str_st_hvy, str_st_irn
opp_str_tbl:    dc.l    str_opp_0, str_opp_1, str_opp_2, str_opp_3, str_opp_4

; =============================================================================
; 11. IKBD JOYSTICK 0 ($fe) FIX (Tynesoft's $4112 table had a byte/word bug!)
; =============================================================================
hook_ikbd_joy0:
                tst.w   ikbd_joy0_pend
                beq.s   .ij0_chk
                clr.w   ikbd_joy0_pend
                move.b  d0,G_JOY0.l             ; store Joystick 0 state byte!
                rts
.ij0_chk:
                ; Only intercept $fe if not already inside Joy 1 ($4110) or multi-byte ($3fac)
                tst.b   GAME_BASE+$4110.l
                bne.s   .ij0_orig
                tst.b   GAME_BASE+$3fac.l
                bne.s   .ij0_orig
                cmpi.b  #$fe,d0
                bne.s   .ij0_orig
                move.w  #1,ikbd_joy0_pend
                rts
.ij0_orig:
                tst.b   GAME_BASE+$4110.l
                jmp     GAME_BASE+$40b2

; Race-free Joy 1 capture ($4108): keeps raw_joy1 updated even during daze!
hook_ikbd_joy1:
                move.b  d0,raw_joy1
                move.b  d0,G_JOY1.l
                rts

; =============================================================================
; 12. BETWEEN-FIGHTS BRITISH RED-TOP TABLOID ("THE RING SUN", hooks $0708)
; =============================================================================
; Palette preserves WIN.PI1/RING.PI1 fighter colours (col 0..13, 15) and puts
; Cream Newsprint Paper in unused col 14 ($665) + Tabloid Red in col 3 ($600)!
;   - col 0  ($000): Black bezel, photo backdrop & crisp black ink (VBL-safe!)
;   - col 3  ($600): Red-top masthead & footer banner (and boxing gloves!)
;   - col 14 ($665): Cream newsprint paper (p0=0, p1=1, p2=1, p3=1)
;   - col 15 ($777): Pure white masthead & footer text (p0=p1=p2=p3=1)
hook_newspaper:
                clr.w   np_is_preview
                bsr.s   draw_newspaper_common
                jmp     GAME_BASE+$1cf4

; Shared renderer for BOTH Post-Fight (np_is_preview=0) and Pre-Fight Scouting Preview (np_is_preview=1)!
draw_newspaper_common:
                movem.l d0-d7/a0-a6,-(sp)

                ; 1. Clear $70000 to black bezel (col 0 = $000, VBL-safe!)
                lea     $70000,a0
                move.w  #8000-1,d0
.np_clr:
                clr.l   (a0)+
                dbra    d0,.np_clr

                ; 2. Fill tabloid page (x=16..303, y=4..195) with Cream Paper (col 14: p0=0, p1=p2=p3=$ffff)
                lea     $70000+4*160+8,a0       ; x=16..303 (288 px = 18 chunks), y=4..195 (192 rows)
                move.w  #192-1,d1
.np_paper_r:
                movea.l a0,a1
                moveq   #18-1,d0
.np_paper_c:
                move.l  #$0000ffff,(a1)+        ; p0=0, p1=$ffff
                move.l  #$ffffffff,(a1)+        ; p2=$ffff, p3=$ffff -> col 14!
                dbra    d0,.np_paper_c
                adda.w  #160,a0
                dbra    d1,.np_paper_r

                ; 3. Crimson RED-TOP MASTHEAD BANNER (x=16..303, y=6..27, 22 rows, col 3: p0=p1=$ffff, p2=p3=0)
                lea     $70000+6*160+8,a0
                moveq   #22-1,d1
.np_red_top:
                movea.l a0,a1
                moveq   #18-1,d0
.np_red_tc:
                move.l  #$ffffffff,(a1)+        ; p0=$ffff, p1=$ffff
                clr.l   (a1)+                   ; p2=0, p3=0 -> col 3 (Tabloid Red!)
                dbra    d0,.np_red_tc
                adda.w  #160,a0
                dbra    d1,.np_red_top

                ; 4. Crimson RED-TOP FOOTER BANNER (x=16..303, y=178..191, 14 rows, col 3)
                lea     $70000+178*160+8,a0
                moveq   #14-1,d1
.np_red_bot:
                movea.l a0,a1
                moveq   #18-1,d0
.np_red_bc:
                move.l  #$ffffffff,(a1)+
                clr.l   (a1)+
                dbra    d0,.np_red_bc
                adda.w  #160,a0
                dbra    d1,.np_red_bot

                ; 5. Black rules (col 0 = all 0s)
                lea     $70000+4*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+28*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+38*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+39*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+72*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+73*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+147*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+177*160+8,a0
                bsr.w   np_draw_rule
                lea     $70000+194*160+8,a0
                bsr.w   np_draw_rule

                ; Vertical side borders (x=16 and x=303, col 0 black)
                lea     $70000+4*160+8,a0
                move.w  #191-1,d0
.np_vside:
                andi.w  #$3fff,0(a0)
                andi.w  #$3fff,2(a0)
                andi.w  #$3fff,4(a0)
                andi.w  #$3fff,6(a0)
                andi.w  #$fffc,136(a0)
                andi.w  #$fffc,138(a0)
                andi.w  #$fffc,140(a0)
                andi.w  #$fffc,142(a0)
                adda.w  #160,a0
                dbra    d0,.np_vside

                ; 6. CHUNKY 2x2 WHITE MASTHEAD: "THE RING SUN" (12 chars = 192px, x=64 -> +$20, y=11)
                lea     $70000+11*160+$20,a6
                movea.l a6,a4
                lea     str_np_mast(pc),a5
                moveq   #1,d7                   ; d7=1 -> WHITE ink (col 15) on red banner!
                bsr.w   np_print_big

                ; Sub-masthead strapline (y=30, x=24 -> +$09, small black ink)
                lea     $70000+30*160+$09,a6
                movea.l a6,a4
                lea     str_np_sub(pc),a5
                tst.w   np_is_preview
                beq.s   .np_sub_pr
                lea     str_np_sub_pre(pc),a5
.np_sub_pr:
                moveq   #0,d7                   ; d7=0 -> BLACK ink (col 0) on cream paper!
                bsr.w   np_print_small

                ; 7. CHUNKY 2x2 BOLD BLACK TABLOID HEADLINE (y=43, 2 lines!)
                move.w  G_OPP_IDX.l,d0
                cmpi.w  #4,d0
                ble.s   .np_idx_ok
                moveq   #4,d0
.np_idx_ok:
                add.w   d0,d0
                add.w   d0,d0
                tst.w   np_is_preview
                beq.s   .np_post_hl
                lea     np_pre_tbl(pc),a0
                movea.l (a0,d0.w),a5
                bra.s   .np_print_hl
.np_post_hl:
                tst.w   GAME_BASE+$3a5e.l
                beq.s   .np_loss
                lea     np_win_tbl(pc),a0
                movea.l (a0,d0.w),a5
                bra.s   .np_print_hl
.np_loss:
                lea     np_loss_tbl(pc),a0
                movea.l (a0,d0.w),a5
.np_print_hl:
                lea     $70000+43*160+$10,a6    ; x=32 (16 chars max = 256px, centered!)
                movea.l a6,a4
                moveq   #0,d7                   ; BLACK chunky bold capitals!
                bsr.w   np_print_big

                ; 8. FIGHTER PHOTOS!
                tst.w   np_is_preview
                bne.s   .np_pic_pre
                tst.w   GAME_BASE+$3a5e.l
                beq.w   .np_pic_loss
                ; Marco WON -> Left = Marco Win ($38000), Right = Opponent ($63ed0)
                lea     $38000,a0
                lea     $70000+77*160+$08,a1
                bsr.w   np_blit_photo
                lea     $63ed0,a0
                lea     $70000+77*160+$70,a1
                bsr.w   np_blit_photo
                lea     $70000+137*160+$09,a6
                movea.l a6,a4
                lea     str_np_cap_wm(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small
                lea     $70000+137*160+$71,a6
                movea.l a6,a4
                lea     str_np_cap_ko(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small
                bra.w   .np_pic_frames
.np_pic_pre:
                ; PRE-FIGHT PREVIEW -> Left = Marco ($38000), Right = Opponent ($63ed0)
                lea     $38000,a0
                lea     $70000+77*160+$08,a1
                bsr.w   np_blit_photo
                lea     $63ed0,a0
                lea     $70000+77*160+$70,a1
                bsr.w   np_blit_photo
                lea     $70000+137*160+$09,a6
                movea.l a6,a4
                lea     str_np_cap_mar(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small
                lea     $70000+137*160+$71,a6
                movea.l a6,a4
                lea     str_np_cap_opp(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small
                bra.s   .np_pic_frames
.np_pic_loss:
                ; Marco LOST -> Left = Opponent ($63ed0), Right = Marco bruised ($38050)
                lea     $63ed0,a0
                lea     $70000+77*160+$08,a1
                bsr.w   np_blit_photo
                lea     $38050,a0
                lea     $70000+77*160+$70,a1
                bsr.w   np_blit_photo
                lea     $70000+137*160+$09,a6   ; Left: "WINNER"
                movea.l a6,a4
                lea     str_np_cap_win(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small
                lea     $70000+137*160+$71,a6   ; Right: "KO MARCO"
                movea.l a6,a4
                lea     str_np_cap_lm(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small

.np_pic_frames:
                ; Draw crisp black borders around both 80x56 photo boxes
                lea     $70000+76*160+$08,a0
                bsr.w   np_frame_photo
                lea     $70000+76*160+$70,a0
                bsr.w   np_frame_photo

                ; Center Tabloid Story Column (x=112..207, y=78, small black font!)
                lea     $70000+78*160+$38,a6
                movea.l a6,a4
                tst.w   np_is_preview
                beq.s   .np_st_post
                move.w  G_OPP_IDX.l,d0
                cmpi.w  #4,d0
                ble.s   .np_sc_ok
                moveq   #4,d0
.np_sc_ok:
                add.w   d0,d0
                add.w   d0,d0
                lea     np_scout_tbl(pc),a0
                movea.l (a0,d0.w),a5
                moveq   #0,d7
                bsr.w   np_print_small
                bra.s   .np_bot_strap
.np_st_post:
                bsr.w   pick_postfight_story    ; d0.w = 0..9 dynamic story index!
                add.w   d0,d0
                add.w   d0,d0
                lea     np_dyn_story_tbl(pc),a0
                movea.l (a0,d0.w),a5
                moveq   #0,d7
                bsr.w   np_print_small

                ; Best combo line in center column (y=135, x=112 -> +$38)
                lea     $70000+135*160+$38,a6
                movea.l a6,a4
                lea     str_np_combo_lbl(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small
                move.w  p1_best_combo(pc),d0
                cmpi.w  #9,d0
                ble.s   .np_cb_ok
                moveq   #9,d0
.np_cb_ok:
                move.b  d0,str_np_combo_buf
                lea     str_np_combo_buf(pc),a5
                moveq   #0,d7
                bsr.w   np_print_small

.np_bot_strap:
                ; 10. Bottom Ringside Story Strap (y=153, x=24 -> +$09, full width small black text!)
                lea     $70000+153*160+$09,a6
                movea.l a6,a4
                tst.w   np_is_preview
                beq.s   .np_fb_post
                move.w  G_OPP_IDX.l,d0
                cmpi.w  #4,d0
                ble.s   .np_tp_ok
                moveq   #4,d0
.np_tp_ok:
                add.w   d0,d0
                add.w   d0,d0
                lea     np_tip_tbl(pc),a0
                movea.l (a0,d0.w),a5
                bra.s   .np_fb_pr
.np_fb_post:
                bsr.w   pick_postfight_story
                add.w   d0,d0
                add.w   d0,d0
                lea     np_dyn_foot_tbl(pc),a0
                movea.l (a0,d0.w),a5
.np_fb_pr:
                moveq   #0,d7
                bsr.w   np_print_small

                ; 11. White Footer Prompt inside Crimson Bar (y=182, x=72 -> +$21, dead-center!)
                lea     $70000+182*160+$21,a6
                movea.l a6,a4
                lea     str_np_foot(pc),a5
                tst.w   np_is_preview
                beq.s   .np_ft_pr
                lea     str_np_foot_pre(pc),a5
.np_ft_pr:
                moveq   #1,d7                   ; WHITE text on red footer bar!
                bsr.w   np_print_small

                ; 12. Display $70000 and load Tabloid + Fighter Palette!
                move.b  #$07,$ffff8201.w
                move.b  #$00,$ffff8203.w
                lea     $ffff8240.w,a0
                lea     np_saved_pal(pc),a1
                moveq   #7,d0
.np_spal:
                move.l  (a0)+,(a1)+
                dbra    d0,.np_spal

                lea     np_palette(pc),a0
                lea     $ffff8240.w,a1
                moveq   #7,d0
.np_lpal:
                move.l  (a0)+,(a1)+
                dbra    d0,.np_lpal

                ; 13. Wait ~0.4s debounce (20 VBLs), then wait for Fire or Space/Return
                moveq   #20-1,d2
.np_deb:
                clr.w   G_VBL_FLAG.l
.np_dw:         tst.w   G_VBL_FLAG.l
                beq.s   .np_dw
                dbra    d2,.np_deb

.np_wait_rel:
                btst.b  #7,G_JOY1.l
                bne.s   .np_wait_rel

.np_wait_go:
                btst.b  #7,G_JOY1.l
                bne.s   .np_exit
                tst.b   G_KEY_BASE+$39.l        ; Space
                bne.s   .np_exit
                tst.b   G_KEY_BASE+$1c.l        ; Return
                beq.s   .np_wait_go

.np_exit:
                lea     np_saved_pal(pc),a0
                lea     $ffff8240.w,a1
                moveq   #7,d0
.np_rpal:
                move.l  (a0)+,(a1)+
                dbra    d0,.np_rpal

                movem.l (sp)+,d0-d7/a0-a6
                rts

; Blit 80x56 fighter portrait from a0 to screen a1 (10 longs = 40 bytes per row)
np_blit_photo:
                moveq   #56-1,d1
.nbp_row:
                movea.l a0,a2
                movea.l a1,a3
                moveq   #10-1,d0
.nbp_col:
                move.l  (a2)+,(a3)+
                dbra    d0,.nbp_col
                adda.w  #160,a0
                adda.w  #160,a1
                dbra    d1,.nbp_row
                rts

; Draw 1px black border around 80x56 photo box (a0 = top border line at y-1)
np_frame_photo:
                ; Top border (40 bytes = 10 longs of 0)
                movea.l a0,a1
                moveq   #10-1,d0
.nfp_t:         clr.l   (a1)+
                dbra    d0,.nfp_t
                ; Bottom border (+57*160)
                lea     57*160(a0),a1
                moveq   #10-1,d0
.nfp_b:         clr.l   (a1)+
                dbra    d0,.nfp_b
                ; Left & right vertical edges (56 rows)
                lea     160(a0),a1
                moveq   #56-1,d0
.nfp_lr:
                andi.w  #$7fff,0(a1)
                andi.w  #$7fff,2(a1)
                andi.w  #$7fff,4(a1)
                andi.w  #$7fff,6(a1)
                andi.w  #$fffe,32(a1)
                andi.w  #$fffe,34(a1)
                andi.w  #$fffe,36(a1)
                andi.w  #$fffe,38(a1)
                adda.w  #160,a1
                dbra    d0,.nfp_lr
                rts

; Print CHUNKY 2x2 BOLD CAPITALS (16x12 px per glyph!)
; a5=string, a6=screen (word-aligned), a4=line-start, d7=0 (BLACK col 0) or 1 (WHITE col 15)
np_print_big:
                moveq   #0,d0
                move.b  (a5)+,d0
                cmpi.b  #$fe,d0
                beq.w   .npb_done
                cmpi.b  #$ff,d0
                beq.w   .npb_nl
                cmpi.b  #$0a,d0
                bge.s   .npb_alpha
                addi.b  #$1c,d0
                bra.s   .npb_glyph
.npb_alpha:
                subi.b  #$41,d0
.npb_glyph:
                lea     $2ab20,a0
                move.w  d0,d1
                lsl.w   #2,d0
                andi.l  #$f8,d0
                andi.l  #$01,d1
                or.l    d1,d0
                adda.l  d0,a0
                movea.l a6,a1
                moveq   #6-1,d5
.npb_row:
                move.b  0(a0),d2
                or.b    2(a0),d2
                or.b    4(a0),d2
                or.b    6(a0),d2
                ; Double each bit horizontally (8 bits -> 16 bits in d3.w)
                moveq   #0,d3
                moveq   #7,d4
.npb_dbl:
                add.w   d3,d3
                add.w   d3,d3
                add.b   d2,d2
                bcc.s   .npb_z
                ori.w   #3,d3
.npb_z:
                dbra    d4,.npb_dbl
                ; Chunky bold thickening (+1px right smear!)
                move.w  d3,d4
                lsr.w   #1,d4
                or.w    d4,d3
                tst.w   d7
                bne.s   .npb_white
                ; BLACK ink (col 0): AND ~d3 into all 4 planes on 2 scanlines!
                not.w   d3
                and.w   d3,0(a1)
                and.w   d3,2(a1)
                and.w   d3,4(a1)
                and.w   d3,6(a1)
                and.w   d3,160(a1)
                and.w   d3,162(a1)
                and.w   d3,164(a1)
                and.w   d3,166(a1)
                bra.s   .npb_nextr
.npb_white:
                ; WHITE ink (col 15): OR d3 into all 4 planes on 2 scanlines!
                or.w    d3,0(a1)
                or.w    d3,2(a1)
                or.w    d3,4(a1)
                or.w    d3,6(a1)
                or.w    d3,160(a1)
                or.w    d3,162(a1)
                or.w    d3,164(a1)
                or.w    d3,166(a1)
.npb_nextr:
                adda.w  #160,a0
                adda.w  #320,a1                 ; +2 scanlines (2x vertical!)
                dbra    d5,.npb_row
                addq.l  #8,a6                   ; +16 pixels horizontally!
                bra.w   np_print_big
.npb_nl:
                adda.w  #14*160,a4              ; +14 scanlines per chunky headline row
                movea.l a4,a6
                bra.w   np_print_big
.npb_done:
                rts

; Print small 8x6 text: d7=0 BLACK ink (col 0) on cream, d7=1 WHITE ink (col 15) on red!
np_print_small:
                moveq   #0,d0
                move.b  (a5)+,d0
                cmpi.b  #$fe,d0
                beq.w   .nps_done
                cmpi.b  #$ff,d0
                beq.w   .nps_nl
                cmpi.b  #$0a,d0
                bge.s   .nps_alpha
                addi.b  #$1c,d0
                bra.s   .nps_glyph
.nps_alpha:
                subi.b  #$41,d0
.nps_glyph:
                lea     $2ab20,a0
                move.w  d0,d1
                lsl.w   #2,d0
                andi.l  #$f8,d0
                andi.l  #$01,d1
                or.l    d1,d0
                adda.l  d0,a0
                movea.l a6,a1
                moveq   #6-1,d1
.nps_row:
                move.b  0(a0),d2
                or.b    2(a0),d2
                or.b    4(a0),d2
                or.b    6(a0),d2
                tst.w   d7
                bne.s   .nps_w
                not.b   d2
                and.b   d2,0(a1)
                and.b   d2,2(a1)
                and.b   d2,4(a1)
                and.b   d2,6(a1)
                bra.s   .nps_nr
.nps_w:
                or.b    d2,0(a1)
                or.b    d2,2(a1)
                or.b    d2,4(a1)
                or.b    d2,6(a1)
.nps_nr:
                adda.w  #160,a0
                adda.w  #160,a1
                dbra    d1,.nps_row
                move.l  a6,d6
                btst    #0,d6
                bne.s   .nps_odd
                addq.l  #1,d6
                bra.s   .nps_adv
.nps_odd:
                addq.l  #7,d6
.nps_adv:
                movea.l d6,a6
                bra.w   np_print_small
.nps_nl:
                adda.w  #$500,a4                ; +8 scanlines
                movea.l a4,a6
                bra.w   np_print_small
.nps_done:
                rts

; Draw 288px black horizontal rule (col 0 = all 0s) at a0
np_draw_rule:
                moveq   #18-1,d0
.ndr_lp:
                clr.l   (a0)+
                clr.l   (a0)+
                dbra    d0,.ndr_lp
                rts

; Authentic Fighter + British Red-Top Tabloid Palette:
; col 0=$000 black, col 3=$600 tabloid red, col 14=$665 cream newsprint, col 15=$777 pure white!
np_palette:     dc.w    $0000,$0210,$0030,$0600,$0151,$0423,$0750,$0333
                dc.w    $0123,$0355,$0321,$0542,$0543,$0654,$0665,$0777
np_saved_pal:   dcb.w   16,0

str_np_mast:    dc.b    'T','H','E',$5b,'R','I','N','G',$5b,'S','U','N',$fe
str_np_sub:     dc.b    'S','P','O','R','T',$5b,'S','P','E','C','I','A','L',$5b,$5b,$5b,$5b,$5b,2,0,'P',$5b,$5b,$5b,$5b,$5b,'R','I','N','G','S','I','D','E',$fe

; Chunky 2x2 ALL-CAPS Tabloid Headlines (max 16 chars per line!)
str_np_w0:      dc.b    $5b,'W','E','E','D',$5b,'W','H','A','C','K','E','D',$5c,$ff
                dc.b    $5b,'M','A','R','C','O',$5b,'K','O',$5b,'S','H','O','C','K',$5c,$fe
str_np_w1:      dc.b    $5b,'J','O','N','E','S',$5b,'F','L','O','O','R','E','D',$5c,$ff
                dc.b    $5b,'M','A','R','C','O',$5b,'O','N',$5b,'F','I','R','E',$5c,$fe
str_np_w2:      dc.b    $5b,'H','A','G','M','A','N',$5b,'H','I','T',$5c,$ff
                dc.b    $5b,'B','R','U','T','A','L',$5b,'U','P','S','E','T',$5c,$fe
str_np_w3:      dc.b    $5b,'R','O','N','C','O',$5b,'R','O','C','K','E','D',$5c,$ff
                dc.b    $5b,$5b,'T','I','T','L','E',$5b,'S','H','O','T',$5c,$fe
str_np_w4:      dc.b    $5b,$5b,'K','I','N','G',$5b,'M','A','R','C','O',$5c,$ff
                dc.b    $5b,$5b,'M','A','L','O','N','E',$5b,'K','O',$5c,$fe

str_np_l0:      dc.b    $5b,'W','E','E','D',$5b,'W','I','N','S',$5b,'I','T',$5c,$ff
                dc.b    $5b,'M','A','R','C','O',$5b,'D','E','C','K','E','D',$5c,$fe
str_np_l1:      dc.b    $5b,'J','O','N','E','S',$5b,'J','A','B','S',$5c,$ff
                dc.b    $5b,'M','A','R','C','O',$5b,'I','N',$5b,'P','A','I','N',$5c,$fe
str_np_l2:      dc.b    $5b,'H','A','G','M','A','N',$5b,'R','U','L','E','S',$5c,$ff
                dc.b    $5b,'M','A','R','C','O',$5b,'B','E','A','T','E','N',$5c,$fe
str_np_l3:      dc.b    $5b,'R','O','N','C','O',$5b,'C','R','U','S','H',$5c,$ff
                dc.b    $5b,$5b,'D','R','E','A','M',$5b,'O','V','E','R',$5c,$fe
str_np_l4:      dc.b    $5b,'C','H','A','M','P',$5b,'M','A','L','O','N','E',$5c,$ff
                dc.b    $5b,$5b,'T','O','O',$5b,'S','T','R','O','N','G',$5c,$fe

str_np_cap_wm:  dc.b    'W','I','N',$5b,'M','A','R','C','O',$fe
str_np_cap_ko:  dc.b    'K','O',$5b,'L','O','S','E','R',$fe
str_np_cap_win: dc.b    $5b,'W','I','N','N','E','R',$fe
str_np_cap_lm:  dc.b    'K','O',$5b,'M','A','R','C','O',$fe

str_np_story_w: dc.b    'W','H','A','T',$5b,'A',$5b,'B','O','U','T',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'L','A','N','D','E','D',$ff
                dc.b    'H','E','A','V','Y',$5b,'S','H','O','T','S',$ff
                dc.b    'T','O',$5b,'F','L','O','O','R',$5b,'H','I','S',$ff
                dc.b    'R','I','V','A','L',$5b,'I','N',$5b,'B','I','G',$ff
                dc.b    'S','T','Y','L','E',$5c,$fe

str_np_story_l: dc.b    'T','O','U','G','H',$5b,'N','I','G','H','T',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'T','O','O','K',$5b,'A',$ff
                dc.b    'R','E','A','L',$5b,'B','E','A','T','I','N','G',$ff
                dc.b    'A','N','D',$5b,'H','I','T',$5b,'T','H','E',$ff
                dc.b    'C','A','N','V','A','S',$5b,'H','A','R','D',$5c,$fe

str_np_combo_lbl: dc.b  'B','E','S','T',$5b,'C','O','M','B','O',$5b,$fe

str_np_foot_w:  dc.b    'F','A','N','S',$5b,'R','O','A','R','E','D',$5b,'A','S',$5b,'M','A','R','C','O',$5b,'T','O','O','K',$5b,'C','O','N','T','R','O','L',$ff
                dc.b    'O','F',$5b,'T','H','E',$5b,'R','I','N','G',$5c,$5b,'N','E','X','T',$5b,'S','T','O','P',$5b,'T','H','E',$5b,'T','I','T','L','E',$5c,$fe

str_np_foot_l:  dc.b    'T','R','A','I','N','E','R',$5b,'S','A','Y','S',$5b,'M','A','R','C','O',$5b,'M','U','S','T',$5b,'H','I','T',$5b,'T','H','E',$ff
                dc.b    'G','Y','M',$5b,'H','A','R','D',$5b,'B','E','F','O','R','E',$5b,'A','N','Y',$5b,'R','E','M','A','T','C','H',$5c,$fe

str_np_foot:    dc.b    'P','R','E','S','S',$5b,'F','I','R','E',$5b,'T','O',$5b,'C','O','N','T','I','N','U','E',$fe
str_np_foot_pre: dc.b   'P','R','E','S','S',$5b,'F','I','R','E',$5b,'T','O',$5b,'E','N','T','E','R',$5b,'R','I','N','G',$fe
str_np_sub_pre: dc.b    'F','I','G','H','T',$5b,'N','I','G','H','T',$5b,$5b,$5b,$5b,$5b,2,0,'P',$5b,$5b,$5b,$5b,$5b,$5b,$5b,$5b,'P','R','E','V','I','E','W',$fe
str_np_cap_mar: dc.b    $5b,$5b,'M','A','R','C','O',$fe
str_np_cap_opp: dc.b    $5b,'C','H','A','M','P','I','O','N',$fe

; Pre-Fight Chunky 2x2 Headlines (max 16 chars per line!)
str_np_p0:      dc.b    $5b,'M','A','R','C','O',$5b,'V','S',$5b,'W','E','E','D',$5c,$ff
                dc.b    $5b,$5b,'R','O','O','K','I','E',$5b,'B','O','U','T',$5c,$fe
str_np_p1:      dc.b    $5b,$5b,'J','O','N','E','S',$5b,'T','E','S','T',$5c,$ff
                dc.b    $5b,$5b,'P','O','W','E','R',$5b,'C','L','A','S','H',$5c,$fe
str_np_p2:      dc.b    $5b,$5b,'H','A','M','M','E','R','H','E','A','D',$5c,$ff
                dc.b    $5b,'H','E','A','D','B','U','T','T',$5b,'W','A','R',$5c,$fe
str_np_p3:      dc.b    $5b,$5b,'R','O','N','C','O',$5b,'W','A','L','L',$5c,$ff
                dc.b    $5b,$5b,'T','I','T','L','E',$5b,'E','L','I','M',$5c,$fe
str_np_p4:      dc.b    $5b,$5b,'W','O','R','L','D',$5b,'T','I','T','L','E',$5c,$ff
                dc.b    $5b,'C','H','A','M','P',$5b,'M','A','L','O','N','E',$5c,$fe

; Pre-Fight Center Column Scouting Reports (12 chars wide max!)
str_sc_0:       dc.b    'S','C','O','U','T',$5b,'R','E','P','O','R','T',$ff,$ff
                dc.b    'G','L','A','S','S',$5b,'J','A','W',$5c,$ff
                dc.b    'W','E','A','K',$5b,'U','P',$5b,'T','O','P',$5c,$ff
                dc.b    'G','O',$5b,'F','O','R',$5b,'H','E','A','D',$ff
                dc.b    'C','O','M','B','O','S',$5c,$fe
str_sc_1:       dc.b    'S','C','O','U','T',$5b,'R','E','P','O','R','T',$ff,$ff
                dc.b    'R','O','C','K',$5b,'S','O','L','I','D',$ff
                dc.b    'B','O','D','Y',$5c,$5b,'A','I','M',$ff
                dc.b    'H','I','G','H',$5b,'T','O',$5b,'T','H','E',$ff
                dc.b    'C','H','I','N',$5c,$fe
str_sc_2:       dc.b    'S','C','O','U','T',$5b,'R','E','P','O','R','T',$ff,$ff
                dc.b    'I','R','O','N',$5b,'S','K','U','L','L',$5c,$ff
                dc.b    'W','E','E','D','Y',$5b,'G','U','T',$5c,$ff
                dc.b    'R','I','P',$5b,'B','O','D','Y',$ff
                dc.b    'S','H','O','T','S',$5c,$fe
str_sc_3:       dc.b    'S','C','O','U','T',$5b,'R','E','P','O','R','T',$ff,$ff
                dc.b    'T','I','G','H','T',$5b,'G','U','A','R','D',$5c,$ff
                dc.b    'D','R','A','I','N',$5b,'H','I','S',$ff
                dc.b    'S','T','A','M','I','N','A',$5b,'T','O',$ff
                dc.b    'W','I','N',$5c,$fe
str_sc_4:       dc.b    'S','C','O','U','T',$5b,'R','E','P','O','R','T',$ff,$ff
                dc.b    'T','O','U','G','H',$5b,'C','H','A','M','P',$5c,$ff
                dc.b    'M','I','X',$5b,'H','I','G','H',$5b,'A','N','D',$ff
                dc.b    'L','O','W',$5b,'F','O','R',$5b,'A',$ff
                dc.b    'K','O',$5b,'F','I','N','I','S','H',$5c,$fe

; Pre-Fight Bottom Corner Advice (34 chars max per line!)
str_tp_0:       dc.b    'C','O','R','N','E','R',$5b,'T','I','P',$5b,'T','H','R','E','E',$5b,'H','E','A','D',$5b,'H','I','T','S',$5b,'D','A','Z','E',$5c,$ff
                dc.b    'S','E','T','S',$5b,'U','P',$5b,'A','N',$5b,'E','A','S','Y',$5b,'F','I','R','S','T',$5b,'W','I','N',$5c,$fe
str_tp_1:       dc.b    'C','O','R','N','E','R',$5b,'T','I','P',$5b,'D','O',$5b,'N','O','T',$5b,'W','A','S','T','E',$5b,'L','O','W',$5b,'J','A','B','S',$5c,$ff
                dc.b    'J','O','N','E','S',$5b,'T','A','K','E','S',$5b,'H','E','A','V','Y',$5b,'H','E','A','D',$5b,'D','A','M','A','G','E',$5c,$fe
str_tp_2:       dc.b    'C','O','R','N','E','R',$5b,'T','I','P',$5b,'H','I','S',$5b,'H','E','A','D',$5b,'I','S',$5b,'S','O','L','I','D',$5b,'R','O','C','K',$5c,$ff
                dc.b    'P','O','U','N','D',$5b,'H','I','S',$5b,'B','O','D','Y',$5b,'T','O',$5b,'F','O','L','D',$5b,'H','I','M',$5c,$fe
str_tp_3:       dc.b    'C','O','R','N','E','R',$5b,'T','I','P',$5b,'W','O','R','K',$5b,'H','I','S',$5b,'B','O','D','Y',$5b,'H','A','R','D',$5c,$ff
                dc.b    'E','M','P','T','Y',$5b,'H','I','S',$5b,'T','A','N','K',$5b,'T','H','E','N',$5b,'K','O',$5b,'H','I','M',$5c,$fe
str_tp_4:       dc.b    'C','O','R','N','E','R',$5b,'T','I','P',$5b,'S','A','V','E',$5b,'Y','O','U','R',$5b,'K','O',$5b,'U','P','P','E','R','C','U','T',$ff
                dc.b    'F','O','R',$5b,'T','H','E',$5b,'F','I','N','A','L',$5b,'B','L','O','W',$5b,'T','O',$5b,'W','I','N',$5c,$fe

str_np_combo_buf: dc.b  0,$fe
                even
np_win_tbl:     dc.l    str_np_w0, str_np_w1, str_np_w2, str_np_w3, str_np_w4
np_loss_tbl:    dc.l    str_np_l0, str_np_l1, str_np_l2, str_np_l3, str_np_l4
np_pre_tbl:     dc.l    str_np_p0, str_np_p1, str_np_p2, str_np_p3, str_np_p4
np_scout_tbl:   dc.l    str_sc_0,  str_sc_1,  str_sc_2,  str_sc_3,  str_sc_4
np_tip_tbl:     dc.l    str_tp_0,  str_tp_1,  str_tp_2,  str_tp_3,  str_tp_4

; Dynamic Ringside Reporter: classify how Marco fought into story index d0.w (0..6 Win, 7..9 Loss)
pick_postfight_story:
                tst.w   GAME_BASE+$3a5e.l
                beq.s   .pps_loss
                ; --- WIN STORIES (0..6) ---
                tst.w   ko_finisher_flag
                beq.s   .pps_w_body
                move.w  stat_body(pc),d0
                cmp.w   stat_head(pc),d0
                ble.s   .pps_w1
                moveq   #0,d0                   ; 0: Body-to-KO specialist!
                rts
.pps_w1:        moveq   #1,d0                   ; 1: KO Uppercut finisher!
                rts
.pps_w_body:
                move.w  stat_body(pc),d0
                cmpi.w  #4,d0
                blt.s   .pps_w_head
                cmp.w   stat_head(pc),d0
                ble.s   .pps_w_head
                moveq   #2,d0                   ; 2: Body Snatcher!
                rts
.pps_w_head:
                cmpi.w  #2,stat_dazes
                bge.s   .pps_w3
                move.w  stat_body(pc),d0
                add.w   d0,d0                   ; 2 * stat_body
                cmp.w   stat_head(pc),d0
                bgt.s   .pps_w_combo
                tst.w   stat_head
                beq.s   .pps_w_combo
.pps_w3:        moveq   #3,d0                   ; 3: Head-Hunter / Daze Master!
                rts
.pps_w_combo:
                cmpi.w  #4,p1_best_combo
                blt.s   .pps_w_def
                moveq   #4,d0                   ; 4: Combo Machine!
                rts
.pps_w_def:
                cmpi.w  #6,stat_blocks
                blt.s   .pps_w6
                moveq   #5,d0                   ; 5: Cool Counter-Puncher!
                rts
.pps_w6:        moveq   #6,d0                   ; 6: All-Rounder!
                rts
                ; --- LOSS STORIES (7..9) ---
.pps_loss:
                cmpi.w  #2,stat_exh
                blt.s   .pps_l_scout
                moveq   #7,d0                   ; 7: Gassed Out!
                rts
.pps_l_scout:
                ; Ignored Scout Report: head-hunted Hagman (2) OR body-hunted Jones (1)!
                cmpi.w  #2,G_OPP_IDX.l
                bne.s   .pps_l_j
                move.w  stat_head(pc),d0
                cmp.w   stat_body(pc),d0
                bgt.s   .pps_l8
                bra.s   .pps_l9
.pps_l_j:
                cmpi.w  #1,G_OPP_IDX.l
                bne.s   .pps_l9
                move.w  stat_body(pc),d0
                cmp.w   stat_head(pc),d0
                ble.s   .pps_l9
.pps_l8:        moveq   #8,d0                   ; 8: Wrong Gameplan!
                rts
.pps_l9:        moveq   #9,d0                   ; 9: Outgunned!
                rts

; Dynamic Post-Fight Center Column Stories (max 12 chars/line, 5-6 lines)
str_ds_0:       dc.b    'B','O','D','Y',$5b,'T','H','E','N',$ff
                dc.b    'B','O','O','M',$5c,$5b,'M','A','R','C','O',$ff
                dc.b    'D','R','A','I','N','E','D',$5b,'T','H','E',$ff
                dc.b    'T','A','N','K',$5b,'T','H','E','N',$ff
                dc.b    'L','A','N','D','E','D',$5b,'K','O',$5c,$fe
str_ds_1:       dc.b    'L','I','G','H','T','S',$5b,'O','U','T',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'H','I','T',$5b,'A',$ff
                dc.b    'M','A','S','S','I','V','E',$5b,'K','O',$ff
                dc.b    'U','P','P','E','R','C','U','T',$5b,'T','O',$ff
                dc.b    'E','N','D',$5b,'I','T',$5c,$fe
str_ds_2:       dc.b    'B','O','D','Y',$5b,'H','U','N','T','E','R',$ff
                dc.b    'M','A','R','C','O',$5b,'R','I','P','P','E','D',$ff
                dc.b    'T','H','E',$5b,'R','I','B','S',$5b,'T','O',$ff
                dc.b    'G','A','S',$5b,'H','I','S',$5b,'F','O','E',$ff
                dc.b    'C','O','M','P','L','E','T','E','L','Y',$5c,$fe
str_ds_3:       dc.b    'H','E','A','D',$5b,'H','U','N','T','E','R',$ff
                dc.b    'M','A','R','C','O',$5b,'R','O','C','K','E','D',$ff
                dc.b    'H','I','S',$5b,'R','I','V','A','L',$5b,'I','N',$ff
                dc.b    'A',$5b,'D','A','Z','I','N','G',$ff
                dc.b    'B','L','I','T','Z',$5c,$fe
str_ds_4:       dc.b    'C','O','M','B','O',$5b,'K','I','N','G',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'L','A','N','D','E','D',$ff
                dc.b    'B','R','U','T','A','L',$5b,'H','I','T',$ff
                dc.b    'C','H','A','I','N','S',$5b,'T','O',$ff
                dc.b    'W','I','N',$5b,'B','I','G',$5c,$fe
str_ds_5:       dc.b    'C','O','O','L',$5b,'G','U','A','R','D',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'S','O','A','K','E','D',$ff
                dc.b    'U','P',$5b,'T','H','E',$5b,'S','T','O','R','M',$ff
                dc.b    'A','N','D',$5b,'P','I','C','K','E','D',$ff
                dc.b    'H','I','S',$5b,'S','H','O','T','S',$5c,$fe
str_ds_6:       dc.b    'T','O','T','A','L',$5b,'C','L','A','S','S',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'M','I','X','E','D',$ff
                dc.b    'H','E','A','D',$5b,'A','N','D',$ff
                dc.b    'B','O','D','Y',$5b,'F','O','R',$5b,'A',$ff
                dc.b    'C','L','E','A','N',$5b,'W','I','N',$5c,$fe
str_ds_7:       dc.b    'O','U','T',$5b,'O','F',$5b,'G','A','S',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'S','W','U','N','G',$ff
                dc.b    'W','I','L','D',$5b,'A','N','D',$ff
                dc.b    'E','M','P','T','I','E','D',$5b,'H','I','S',$ff
                dc.b    'O','W','N',$5b,'T','A','N','K',$5c,$fe
str_ds_8:       dc.b    'W','R','O','N','G',$5b,'P','L','A','N',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'P','L','A','Y','E','D',$ff
                dc.b    'I','N','T','O',$5b,'H','I','S',$ff
                dc.b    'R','I','V','A','L','S',$5b,'O','W','N',$ff
                dc.b    'S','T','R','E','N','G','T','H',$5c,$fe
str_ds_9:       dc.b    'T','O','U','G','H',$5b,'N','I','G','H','T',$5c,$ff
                dc.b    'M','A','R','C','O',$5b,'T','O','O','K',$5b,'A',$ff
                dc.b    'R','E','A','L',$5b,'B','E','A','T','I','N','G',$ff
                dc.b    'A','N','D',$5b,'H','I','T',$5b,'T','H','E',$ff
                dc.b    'C','A','N','V','A','S',$5b,'H','A','R','D',$5c,$fe

; Dynamic Post-Fight Bottom Straps (max 34 chars/line, 2 lines)
str_df_0:       dc.b    'W','O','R','K','E','D',$5b,'T','H','E',$5b,'R','I','B','S',$5b,'A','L','L',$5b,'F','I','G','H','T',$5b,'B','E','F','O','R','E',$ff
                dc.b    'S','E','A','L','I','N','G',$5b,'I','T',$5b,'W','I','T','H',$5b,'A',$5b,'H','U','G','E',$5b,'U','P','P','E','R','C','U','T',$5c,$fe
str_df_1:       dc.b    'T','H','E',$5b,'C','R','O','W','D',$5b,'E','R','U','P','T','E','D',$5b,'A','S',$5b,'T','H','E',$5b,'F','I','N','A','L',$ff
                dc.b    'K','O',$5b,'U','P','P','E','R','C','U','T',$5b,'S','E','N','T',$5b,'H','I','S',$5b,'F','O','E',$5b,'F','L','Y','I','N','G',$5c,$fe
str_df_2:       dc.b    'R','E','L','E','N','T','L','E','S','S',$5b,'B','O','D','Y',$5b,'W','O','R','K',$5b,'L','E','F','T',$5b,'H','I','S',$ff
                dc.b    'O','P','P','O','N','E','N','T',$5b,'T','O','O',$5b,'T','I','R','E','D',$5b,'T','O',$5b,'G','E','T',$5b,'U','P',$5c,$fe
str_df_3:       dc.b    'D','A','Z','E','D',$5b,'A','N','D',$5b,'C','O','N','F','U','S','E','D',$5c,$5b,'H','I','S',$5b,'R','I','V','A','L',$ff
                dc.b    'H','A','D',$5b,'N','O',$5b,'A','N','S','W','E','R',$5b,'T','O',$5b,'T','H','E',$5b,'H','E','A','D',$5b,'S','H','O','T','S',$5c,$fe
str_df_4:       dc.b    'P','U','N','D','I','T','S',$5b,'P','R','A','I','S','E','D',$5b,'M','A','R','C','O','S',$5b,'N','O','N','S','T','O','P',$ff
                dc.b    'C','O','M','B','I','N','A','T','I','O','N',$5b,'P','U','N','C','H','I','N','G',$5b,'T','O','N','I','G','H','T',$5c,$fe
str_df_5:       dc.b    'T','E','X','T','B','O','O','K',$5b,'G','U','A','R','D',$5b,'W','O','R','K',$5b,'F','R','U','S','T','R','A','T','E','D',$ff
                dc.b    'H','I','S',$5b,'R','I','V','A','L',$5b,'A','L','L',$5b,'N','I','G','H','T',$5b,'L','O','N','G',$5c,$fe
str_df_6:       dc.b    'F','A','N','S',$5b,'R','O','A','R','E','D',$5b,'A','S',$5b,'M','A','R','C','O',$5b,'T','O','O','K',$5b,'C','O','N','T','R','O','L',$ff
                dc.b    'O','F',$5b,'T','H','E',$5b,'R','I','N','G',$5c,$5b,'N','E','X','T',$5b,'S','T','O','P',$5b,'T','H','E',$5b,'T','I','T','L','E',$5c,$fe
str_df_7:       dc.b    'C','O','R','N','E','R',$5b,'S','A','Y','S',$5b,'M','A','R','C','O',$5b,'M','U','S','T',$5b,'P','A','C','E',$5b,'H','I','S',$ff
                dc.b    'P','U','N','C','H','E','S',$5b,'A','N','D',$5b,'W','A','T','C','H',$5b,'H','I','S',$5b,'S','T','A','M','I','N','A',$5c,$fe
str_df_8:       dc.b    'S','H','O','U','L','D',$5b,'H','A','V','E',$5b,'R','E','A','D',$5b,'T','H','E',$5b,'S','C','O','U','T',$5b,'R','E','P','O','R','T',$5c,$ff
                dc.b    'W','R','O','N','G',$5b,'T','A','C','T','I','C','S',$5b,'C','O','S','T',$5b,'M','A','R','C','O',$5b,'D','E','A','R',$5c,$fe
str_df_9:       dc.b    'T','R','A','I','N','E','R',$5b,'S','A','Y','S',$5b,'M','A','R','C','O',$5b,'M','U','S','T',$5b,'H','I','T',$5b,'T','H','E',$ff
                dc.b    'G','Y','M',$5b,'H','A','R','D',$5b,'B','E','F','O','R','E',$5b,'A','N','Y',$5b,'R','E','M','A','T','C','H',$5c,$fe

                even
np_dyn_story_tbl:
                dc.l    str_ds_0, str_ds_1, str_ds_2, str_ds_3, str_ds_4
                dc.l    str_ds_5, str_ds_6, str_ds_7, str_ds_8, str_ds_9
np_dyn_foot_tbl:
                dc.l    str_df_0, str_df_1, str_df_2, str_df_3, str_df_4
                dc.l    str_df_5, str_df_6, str_df_7, str_df_8, str_df_9

; =============================================================================
; 13. 2-PLAYER TUG-OF-WAR KO GAUGE WITH DUAL KO GLOVES ($2262 & $2b8e)
; =============================================================================
hook_ko_draw:
                tst.w   cfg_2p_mode
                bne.w   draw_2p_tug_of_war
                ; 1P Career: clean inline copy of original $2262..$22d2 (avoids $22ce->2266 loop target!)
                moveq   #9,d0
.hkd_1p_lp:
                lea     $71758,a0
                lea     $79758,a1
                moveq   #9,d2
                sub.w   d0,d2
                lsl.w   #3,d2
                adda.w  d2,a0
                adda.w  d2,a1
                cmp.w   G_P1_KO_GAUGE.l,d0
                bgt.s   .hkd_1p_off
                lea     $2c740,a2
                bra.s   .hkd_1p_draw
.hkd_1p_off:
                lea     $2c748,a2
.hkd_1p_draw:
                moveq   #$0e-1,d2
.hkd_1p_row:
                move.l  (a2),(a0)
                move.l  4(a2),4(a0)
                move.l  (a2),(a1)
                move.l  4(a2),4(a1)
                adda.w  #$a0,a0
                adda.w  #$a0,a1
                adda.w  #$a0,a2
                dbra    d2,.hkd_1p_row
                subq.w  #1,d0
                bne.s   .hkd_1p_lp
                rts

hook_p1_ko_inc:
                tst.w   cfg_2p_mode
                bne.s   .hpki_2p
                ; 1P Career: original $2b8e untouched
                cmpi.w  #9,G_P1_KO_GAUGE.l
                jmp     GAME_BASE+$2b96
.hpki_2p:
                ; 2P Mode: P1 landing a clean punch pulls Tug-of-War LEFT (-1, min -3)!
                cmpi.w  #-3,tow_val
                ble.s   .hpki_draw
                subq.w  #1,tow_val
.hpki_draw:
                bsr.s   sync_2p_tow
                rts

; Sync G_P1_KO_GAUGE with tow_val (gameplay only — NOT during $3406 intro sweep!) & redraw HUD
sync_2p_tow:
                clr.w   G_P1_KO_GAUGE.l
                cmpi.w  #-3,tow_val
                bgt.s   draw_2p_tug_of_war
                move.w  #9,G_P1_KO_GAUGE.l

; Draw Dual KO Gloves (Left=P1 at $712e0, Right=P2 at $71328) + 6 Tug-of-War Triangles (<<< >>>)
draw_2p_tug_of_war:
                movem.l d0-d7/a0-a4,-(sp)

.tow_lglove:
                ; 1. Left KO Glove (P1, x=64..111, y=30..57): Big ($28fa0) if tow_val <= -3 else Small ($28fb8)
                lea     $28fb8,a0
                cmpi.w  #-3,tow_val
                bgt.s   .tow_lg_go
                lea     $28fa0,a0
.tow_lg_go:
                lea     $712e0,a1
                lea     $792e0,a2
                bsr.w   tow_blit_glove

                ; 2. Right KO Glove (P2, x=208..255, y=30..57): Big ($28fa0) if tow_val >= +3 else Small ($28fb8)
                lea     $28fb8,a0
                cmpi.w  #3,tow_val
                blt.s   .tow_rg_go
                lea     $28fa0,a0
.tow_rg_go:
                lea     $71328,a1
                lea     $79328,a2
                bsr.w   tow_blit_glove

                ; 3. Left 3 Triangles pointing LEFT (<<<) at $71758, $71760, $71768
                ; Slot 0 lit if tow_val <= -3, Slot 1 if <= -2, Slot 2 if <= -1
                moveq   #-3,d5                  ; threshold: -3, -2, -1
                lea     $71758,a3
                lea     $79758,a4
                moveq   #3-1,d6
.tow_left_lp:
                lea     $2c748,a0               ; unlit cyan triangle
                cmp.w   tow_val(pc),d5          ; if d5 >= tow_val (i.e. tow_val <= d5) -> LIT!
                blt.s   .tow_l_go
                lea     $2c740,a0               ; lit gold triangle!
.tow_l_go:
                movea.l a3,a1
                movea.l a4,a2
                bsr.w   tow_blit_tri_l
                addq.w  #1,d5
                addq.l  #8,a3
                addq.l  #8,a4
                dbra    d6,.tow_left_lp

                ; 4. Right 3 Triangles bit-mirrored pointing RIGHT (>>>) at $71770, $71778, $71780
                ; Slot 3 lit if tow_val >= +1, Slot 4 if >= +2, Slot 5 if >= +3
                moveq   #1,d5                   ; threshold: +1, +2, +3
                moveq   #3-1,d6
.tow_right_lp:
                lea     $2c748,a0               ; unlit cyan triangle
                cmp.w   tow_val(pc),d5          ; if d5 <= tow_val (i.e. tow_val >= d5) -> LIT!
                bgt.s   .tow_r_go
                lea     $2c740,a0               ; lit gold triangle!
.tow_r_go:
                movea.l a3,a1
                movea.l a4,a2
                bsr.w   tow_blit_tri_r
                addq.w  #1,d5
                addq.l  #8,a3
                addq.l  #8,a4
                dbra    d6,.tow_right_lp

                movem.l (sp)+,d0-d7/a0-a4
                rts

; Blit 48x28 KO glove (3 chunks = 24 bytes) from a0 to BOTH a1 ($70000) & a2 ($78000)
tow_blit_glove:
                moveq   #28-1,d2
.tbg_lp:
                move.l  0(a0),0(a1)
                move.l  4(a0),4(a1)
                move.l  8(a0),8(a1)
                move.l  12(a0),12(a1)
                move.l  16(a0),16(a1)
                move.l  20(a0),20(a1)
                move.l  0(a0),0(a2)
                move.l  4(a0),4(a2)
                move.l  8(a0),8(a2)
                move.l  12(a0),12(a2)
                move.l  16(a0),16(a2)
                move.l  20(a0),20(a2)
                adda.w  #160,a0
                adda.w  #160,a1
                adda.w  #160,a2
                dbra    d2,.tbg_lp
                rts

; Blit 16x15 left-pointing triangle from a0 to BOTH a1 & a2
tow_blit_tri_l:
                moveq   #15-1,d2
.tbtl_lp:
                move.l  0(a0),0(a1)
                move.l  4(a0),4(a1)
                move.l  0(a0),0(a2)
                move.l  4(a0),4(a2)
                adda.w  #160,a0
                adda.w  #160,a1
                adda.w  #160,a2
                dbra    d2,.tbtl_lp
                rts

; Blit 16x15 horizontally bit-mirrored (right-pointing!) triangle from a0 to BOTH a1 & a2
tow_blit_tri_r:
                moveq   #15-1,d2
.tbtr_row:
                moveq   #4-1,d3                 ; 4 bitplane words
                moveq   #0,d7                   ; plane byte offset (0, 2, 4, 6)
.tbtr_pl:
                move.w  0(a0,d7.w),d0
                moveq   #0,d1
                moveq   #15,d4
.tbtr_rev:
                lsr.w   #1,d0
                roxl.w  #1,d1
                dbra    d4,.tbtr_rev
                move.w  d1,0(a1,d7.w)
                move.w  d1,0(a2,d7.w)
                addq.w  #2,d7
                dbra    d3,.tbtr_pl
                adda.w  #160,a0
                adda.w  #160,a1
                adda.w  #160,a2
                dbra    d2,.tbtr_row
                rts

; Skip Trainer mini-game in 2P Versus mode & give P1 symmetric +5 HP (+1 at $488 = +6, matching P2!)
hook_trainer_2p:
                tst.w   cfg_2p_mode
                bne.s   .ht2p_skip
                jmp     GAME_BASE+$4c98         ; 1P Career: normal trainer
.ht2p_skip:
                addq.w  #5,G_P1_HP.l
                cmpi.w  #63,G_P1_HP.l
                ble.s   .ht2p_done
                move.w  #63,G_P1_HP.l
.ht2p_done:
                rts

; Low stamina -> longer referee count on the floor (higher KO risk!)
; Input: d0.w = current referee count (0..9). Compare d0 vs (base_getup + stamina_penalty)!
hook_p2_kd_cnt:
                move.w  GAME_BASE+$3a62.l,d1    ; base opponent get-up count
                move.w  p2_stamina(pc),d2
                bsr.s   add_stam_kd_pen
                cmp.w   d1,d0                   ; sets flags identically to `cmp.w $3a62.l, d0`
                jmp     GAME_BASE+$2f74

hook_p1_kd_cnt:
                move.w  GAME_BASE+$3be8.l,d1    ; base player get-up count
                move.w  p1_stamina(pc),d2
                bsr.s   add_stam_kd_pen
                cmp.w   d1,d0                   ; sets flags identically to `cmp.w $3be8.l, d0`
                jmp     GAME_BASE+$3a7a

; Add floor-count penalty to d1.w based on boxer's stamina in d2.w + KO Super finisher bonus!
;   Stamina: <10 -> +4, <24 -> +2, <40 -> +1, >=40 -> +0
;   KO Super Finisher: +3 extra counts!
add_stam_kd_pen:
                tst.w   ko_finisher_flag
                beq.s   .ask_stam
                addq.w  #3,d1
.ask_stam:
                cmpi.w  #10,d2
                bge.s   .ask_24
                addq.w  #4,d1
                rts
.ask_24:
                cmpi.w  #24,d2
                bge.s   .ask_40
                addq.w  #2,d1
                rts
.ask_40:
                cmpi.w  #40,d2
                bge.s   .ask_done
                addq.w  #1,d1
.ask_done:
                rts

; =============================================================================
; Local variables
; =============================================================================
tow_val:        dc.w    0
p2_guard_stance: dc.w   0
ikbd_joy0_pend: dc.w    0
raw_joy1:       dc.b    0, 0
p1_reg_div:     dc.w    0
p2_reg_div:     dc.w    0
opp_picked_f3:  dc.w    0
opp_loaded_fire: dc.w   0
cpu_resting:    dc.w    0
ko_finisher_flag: dc.w  0
np_is_preview:  dc.w    0
stat_head:      dc.w    0
stat_body:      dc.w    0
stat_dazes:     dc.w    0
stat_blocks:    dc.w    0
stat_exh:       dc.w    0
p1_max_stamina: dc.w    63
p2_max_stamina: dc.w    63
p1_combo:       dc.w    0
p2_combo:       dc.w    0
p1_combo_tmr:   dc.w    0
p2_combo_tmr:   dc.w    0
p1_best_combo:  dc.w    0
p1_head_streak: dc.w    0
p2_head_streak: dc.w    0
p1_daze_tmr:    dc.w    0
p2_daze_tmr:    dc.w    0
bar_lost_cnt:   dc.w    0
cpu_nchunks:    dc.w    0
cpu_rows:       dc.w    0
cpu_p01_hi:     dc.l    0
cpu_p23_hi:     dc.l    0

vbl_accum:      dc.w    0
need_first_tick: dc.w   0
logic_tick_cnt: dc.w    0
p1_prev_x:      dc.w    0
p2_prev_x:      dc.w    0
dl_recording:   dc.w    0
dl_bg_full:     dc.w    0
dl_cur_owner:   dc.w    0
dl_count:       dc.w    0
dl_entries:     dcb.b   16*12,0

; Dirty-strip BG restore state (2 double buffers)
buf_dirty_ok:   dc.w    0, 0
buf_x0_bytes:   dc.w    0, 0
buf_x1_bytes:   dc.w    160, 160
cur_min_xb:     dc.w    0
cur_max_xb:     dc.w    160
cur_only_partial: dc.w  0

; Stamina & Combat state
p1_stamina:     dc.w    63
p2_stamina:     dc.w    63
p1_exhausted:   dc.w    0
p2_exhausted:   dc.w    0
p1_stam_drawn:  dc.w    $ffff
p2_stam_drawn:  dc.w    $ffff
p2_spec_cd:     dc.w    0

; Title key debounce
key_f1_held:    dc.w    0
key_f2_held:    dc.w    0
key_f3_held:    dc.w    0
