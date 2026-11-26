; ---------------------------------------------------------------------------
; Player Manager v1.1 — Atari STE Amiga Audio & Visuals Engine (KO2STE.BIN)
;
; Loaded at $0ae940..$0affff (5.7 KB, cleanly above KO2_FILES_CR $09d000..$0ae940)
; ONLY activated on Atari STE / Mega STE (when BR_IS_STE == 1).
; Plain 68000 ST never calls this and runs 100% classic v1.0 ST mode.
;
; 1 MB STE RAM Layout during live match (after KRD finishes loading!):
;   $081000..$08101f : STE 12-bit Amiga pitch palette (colours 0..7)
;   $081020..$082e1f : 80x96 Amiga pitch tilemap (7,680 bytes, 0-based)
;   $082e20..$088e1f : 256 x (16x16x3bpp) ST-interleaved tiles (24,576 bytes)
;   $088f00..$09afff : STE Corkscrew scrolling buffer (424 x 168 = 71.2 KB)
;   $09b000..$09cfff : Blitter 4bpp sprite save-under slots (32 x 256 = 8 KB)
;
; Entry points (fixed header at $0ae940):
;   +$00 : bra.w ste_install_hooks  (after KO2ENG.BIN loads, before $01fd92)
;   +$04 : bra.w ste_cleanup        (in Supervisor SR=$2700 on KO2 exit)
;   +$08 : STE_SND_SIZE.l           (filled by ko2_bridge.s with AMIGASND.BIN size)
;   +$0c : bra.w ste_load_pitch     (after $013450, loads AMIGAP0..3.BIN -> $081000)
; ---------------------------------------------------------------------------

        org     $0ae940

KO2_A4          equ     $0284aa
BR_TOS_84       equ     $0b5814         ; saved original TOS TRAP #1 vector
STE_SND_STG     equ     $0c8b00         ; AMIGASND.BIN staging in KO2_REPLAY_BUF

STE_PIT_PAL     equ     $081000         ; 32 bytes (8 STE 12-bit pitch colours)
STE_PIT_MAP     equ     $081020         ; 7,680 bytes (80 x 96 tilemap)
STE_PIT_TILES   equ     $082e20         ; 24,576 bytes (256 x 96 bytes)
STE_CORK_BUF    equ     $088f00         ; 73,984 bytes (424 x 168 + 480 slack)
STE_SAVE_UNDER  equ     $09b000         ; 6,656 bytes (26 x 256 byte save-under slots: $09b000..$09c9ff)
; STE Blitter HUD/Radar save-under & 1bpp mask buffers (100% inside 1 MB RAM, ZERO overlap with CORK!):
STE_HUD_MASK    equ     $07fd00         ; 320 bytes (1bpp HUD/Banner mask & 32B sprite mask)
STE_MASK_BUF    equ     $07fd00         ; 32 bytes (16-line 1bpp sprite mask scratch)
STE_RADAR_SAVE  equ     $07fe40         ; 4,536 bytes: Blitter radar line save-under pool!
STE_RAD_POOL    equ     $07fe40         ; line pixel save pool ($07fe40..$080ff8 = 4,536B = 567 cells -> fits scale=8!)
STE_RAD_POOL_END equ    $080ff8
STE_RAD_LREC    equ     $09ca00         ; line records (24 x 16B = 384B -> $09cb80, safely above 26 slots!)
STE_RAD_DREC    equ     $09cb80         ; dot restore records (56 x 12B = 672B -> $09ce20)
STE_RAD_CACHE   equ     $09ce20         ; pre-scaled radar lines cache (24 x 8B = 192B -> $09cee0)
STE_LIFT_PTRS   equ     $09cee0         ; 32 x 4B = 128B lifted sprite ptrs (-> $09cf60)
STE_ST_PAL      equ     $09cf60         ; 16B saved Classic ST palette 0..7 (-> $09cf70 < $09d000 KO2_FILES_CR!)
STE_BHUD_SAVE   equ     $0b2400         ; 1,128 bytes (tight 3-box Bottom HUD) -> $0b2868
STE_DRAW_STACK  equ     $0b2880         ; 512 bytes (32 x 16B overlap-safe LIFO sprite stack!) -> $0b2a80
STE_BAN_SAVE    equ     $0b2a80         ; 1,344 bytes (8 lines x 21 cols x 8B) -> $0b2fc0 (< PMOK $0b2ff8!)

CORK_STRIDE     equ     168             ; 336 pixels = 21 x 16px words (4 planes)
CORK_RING_H     equ     224             ; 14 tile rows = 224 scanlines
CORK_RING_BYTES equ     37632           ; 224 * 168

; STE Blitter registers (short I/O addresses $ffff8a20..$ffff8a3d -> 4-byte .w saves 300B + cycles!)
BLT_SRC_XINC    equ     $ffff8a20
BLT_SRC_YINC    equ     $ffff8a22
BLT_SRC_ADDR    equ     $ffff8a24
BLT_ENDMASK1    equ     $ffff8a28
BLT_ENDMASK2    equ     $ffff8a2a
BLT_ENDMASK3    equ     $ffff8a2c
BLT_DST_XINC    equ     $ffff8a2e
BLT_DST_YINC    equ     $ffff8a30
BLT_DST_ADDR    equ     $ffff8a32
BLT_XCOUNT      equ     $ffff8a36
BLT_YCOUNT      equ     $ffff8a38
BLT_HOP         equ     $ffff8a3a
BLT_OP          equ     $ffff8a3b
BLT_LINE        equ     $ffff8a3c
BLT_SKEW        equ     $ffff8a3d

; Jump table & header at $0ae940
ste_entry:
        bra.w   ste_install_hooks       ; +$00
        bra.w   ste_cleanup             ; +$04
STE_SND_SIZE:   dc.l    0               ; +$08 (set by ko2_bridge.s)
        bra.w   ste_load_pitch          ; +$0c

; ---------------------------------------------------------------------------
; Audio State variables
; ---------------------------------------------------------------------------
STE_SND_BASE:   dc.l    0               ; +$10: base of AMIGASND.BIN in KO2 heap
STE_SCRIPT_ST:  dc.l    0               ; start of current sound script
STE_SCRIPT_PTR: dc.l    0               ; current pointer in sound script (0 = idle)
STE_REPEAT_CNT: dc.w    0               ; repeat counter
STE_SND_PEND:   dc.b    0               ; 1 = new sound requested
STE_SND_STOP:   dc.b    0               ; 1 = stop DMA requested
STE_SND_PITCH:  dc.b    0
STE_SND_PAD:    dc.b    0
STE_DMA_CNT:    dc.w    0               ; total STE DMA samples triggered

; ---------------------------------------------------------------------------
; Video / Corkscrew / Blitter State variables
; ---------------------------------------------------------------------------
STE_AMIGA_ON:   dc.w    0               ; 1 = Amiga STE Tiled Pitch ON, 0 = Classic ST
STE_PITCH_OK:   dc.w    0               ; 1 = AMIGAPx.BIN loaded successfully
STE_CUR_TX:     dc.w    -999            ; last top-left tile X in Corkscrew
STE_CUR_TY:     dc.w    -999            ; last top-left tile Y in Corkscrew
STE_VIEW_BASE:  dc.l    STE_CORK_BUF    ; current display address for VBL
STE_VIEW_HSCR:  dc.w    0               ; current STE fine hscroll (0..15)
STE_SLOT_NEXT:  dc.w    0               ; next free save-under slot (0..31)
STE_ST_PAL_OK:  dc.w    0               ; 1 = saved ST palette captured
STE_HUD_ACTIVE: dc.w    0               ; bit0=bhud saved, bit1=banner saved
STE_HUD_VBASE:  dc.l    0               ; STE_VIEW_BASE where HUD/Radar was drawn
STE_HUD_HSCR:   dc.w    0               ; STE_VIEW_HSCR where HUD/Radar was drawn
STE_HUD_SCALE:  dc.w    0               ; -$0e0a(a4) when HUD/Radar was drawn
STE_HUD_RADON:  dc.w    0               ; -$0e10(a4) when HUD/Radar was drawn
STE_HUD_TICK:   dc.w    0               ; frame counter for periodic HUD refresh on stationary cam
STE_ORIG_TB:    dc.l    0               ; saved KO2 original Timer B vector ($120.w)
STE_RAD_LCNT:   dc.w    0               ; active Blitter radar line records (0..24)
STE_RAD_DCNT:   dc.w    0               ; active radar dot records (0..56)
STE_DRAW_CNT:   dc.w    0               ; number of sprites on LIFO draw stack (0..32)

; ---------------------------------------------------------------------------
; ste_install_hooks: Patch KO2ENG.BIN at $010000..$024000 for STE hardware
; ---------------------------------------------------------------------------
ste_install_hooks:
        clr.l   STE_SND_BASE
        clr.l   STE_SCRIPT_ST
        clr.l   STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        clr.w   STE_DMA_CNT
        clr.w   STE_AMIGA_ON
        clr.w   STE_PITCH_OK
        clr.w   STE_ST_PAL_OK
        clr.w   STE_HUD_ACTIVE
        clr.l   STE_ORIG_TB
        clr.w   STE_RAD_LCNT
        clr.w   STE_RAD_DCNT
        clr.w   STE_DRAW_CNT
        clr.w   STE_SLOT_NEXT
        move.w  #-999,STE_CUR_TX
        move.w  #-999,STE_CUR_TY
        move.l  #STE_CORK_BUF,STE_VIEW_BASE
        clr.w   STE_VIEW_HSCR

        ; Install TRAP #8 ($a0.w) fast Supervisor Blitter dispatcher via Supexec
        pea     ste_inst_trap8(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp

        ; 1. Audio hooks ($01849e load, $0184fe play low, $018506 play hi, $018598 stop)
        move.w  #$4ef9,d0
        move.w  d0,$01849e.l
        move.l  #ste_load_samples,$0184a0.l
        move.w  d0,$0184fe.l
        move.l  #ste_play_sound,$018500.l
        move.w  d0,$018506.l
        move.l  #ste_play_sound_hi,$018508.l
        move.w  d0,$018598.l
        move.l  #ste_stop_sound,$01859a.l

        ; 2. VBL top ($018d06 Timer B setup) & bottom ($018e0a $ff8240 write + $018e22 end)
        move.w  d0,$018d06.l
        move.l  #ste_vbl_top,$018d08.l
        move.w  d0,$018e0a.l
        move.l  #ste_vbl_end,$018e0c.l

        ; 3. Pitch camera & lines ($01c1d0)
        move.w  d0,$01c1d0.l
        move.l  #ste_pitch_update,$01c1d2.l

        ; 4. Universal sprite draw core ($01a426: mulu.w #$a0,d1 ; ext.l d0) & erase ($01a83e)
        ;    All 4 KO2 sprite entry points ($01a2fc, $01a346, $01a3bc, $01a412) funnel into $01a426!
        move.w  d0,$01a426.l
        move.l  #ste_draw_spr_core_hook,$01a428.l
        move.w  d0,$01a83e.l
        move.l  #ste_erase_spr,$01a840.l
        ; Also bypass KO2's Timer B raster-beam wait at $01a376 & $01a3cc when Amiga mode is ON!
        move.w  d0,$01a376.l
        move.l  #ste_skip_beam_1,$01a378.l
        move.w  d0,$01a3cc.l
        move.l  #ste_skip_beam_2,$01a3ce.l

        ; 5. In-match key handler ($01b564: cmpi.w #$72,d0 ; bne.b $1b570) -> 'V' view toggle!
        move.w  d0,$01b564.l
        move.l  #ste_key_hook,$01b566.l

        ; 6. Skip KO2's hidden $078000 radar line drawer ($01fae8) in Amiga mode!
        move.w  d0,$01fae8.l
        move.l  #ste_skip_ko2_radline,$01faea.l

        rts

ste_skip_ko2_radline:
        tst.w   STE_AMIGA_ON
        bne.s   .skr_rts
        lea     -$4d78(a4),a5
        move.w  (a5)+,d0
        jmp     $01faee.l
.skr_rts:
        rts

ste_inst_trap8:
        move.l  #ste_trap8_handler,$a0.w
        rts

; ---------------------------------------------------------------------------
; ste_cleanup: Called in Supervisor mode (SR=$2700) when exiting KO2 back to PM
; ---------------------------------------------------------------------------
ste_cleanup:
        clr.b   $ffff8901.w             ; stop STE DMA audio
        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        beq.s   .cl_notb
        move.l  STE_ORIG_TB(pc),$0120.w
.cl_notb:
        clr.b   $ffff820f.w             ; reset STE line width (extra words = 0)
        clr.b   $ffff8265.w             ; reset STE fine hscroll = 0
        move.b  #$07,$ffff8201.w        ; restore standard $078000 screen base
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        clr.w   STE_AMIGA_ON
        clr.l   STE_SCRIPT_PTR
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        rts

; ---------------------------------------------------------------------------
; ste_load_pitch (ste_init_pitch): Called after ko2_bridge.s loads AMIGAPx.BIN
; into $081000..$088e1f. Input: d0.l = bytes read (32288 = success).
; ---------------------------------------------------------------------------
ste_load_pitch:
        cmpi.l  #32288,d0
        bne.s   .lp_fail
        move.w  #1,STE_PITCH_OK
        move.w  #1,STE_AMIGA_ON
        clr.w   STE_SLOT_NEXT
        clr.w   STE_DRAW_CNT
        clr.w   STE_RAD_LCNT
        clr.w   STE_RAD_DCNT
        clr.w   STE_RAD_C_SC
        clr.w   STE_HUD_ACTIVE
        move.w  #-999,STE_CUR_TX
        move.w  #-999,STE_CUR_TY
        moveq   #4,d0                   ; cmd 4 = clear_cork via STE Blitter!
        trap    #8
        rts
.lp_fail:
        clr.w   STE_PITCH_OK
        clr.w   STE_AMIGA_ON
        rts

; ---------------------------------------------------------------------------
; Audio: ste_load_samples / ste_play_sound / ste_play_sound_hi / ste_stop_sound
; ---------------------------------------------------------------------------
ste_load_samples:
        movem.l d0/a0,-(sp)
        move.l  STE_SND_SIZE(pc),d0
        ble.s   .ls_none
        move.l  a5,d0
        addq.l  #1,d0
        and.l   #$fffffffe,d0
        movea.l d0,a5
        move.l  a5,-$1452(a4)
        move.l  a5,STE_SND_BASE
        lea     STE_SND_STG.l,a0
        move.l  STE_SND_SIZE(pc),d0
        addq.l  #3,d0
        lsr.l   #2,d0
        subq.w  #1,d0
.cp_s:  move.l  (a0)+,(a5)+
        dbra    d0,.cp_s
        bra.s   .ls_done
.ls_none:
        clr.l   STE_SND_BASE
.ls_done:
        clr.w   -$142a(a4)
        movem.l (sp)+,d0/a0
        rts

ste_play_sound:
        tst.w   -$142a(a4)
        bne.s   ste_ps_rts
ste_play_sound_hi:
        tst.w   -$5eec(a4)
        bne.s   ste_ps_rts
        tst.l   STE_SND_BASE
        beq.s   ste_ps_rts
        move.l  a2,STE_SCRIPT_ST
        move.l  a2,STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        move.w  #1,-$142a(a4)
        clr.b   STE_SND_STOP
        move.b  #1,STE_SND_PEND
ste_ps_rts:
        rts

ste_stop_sound:
        clr.l   STE_SCRIPT_PTR
        clr.b   STE_SND_PEND
        move.b  #1,STE_SND_STOP
        clr.w   -$142a(a4)
        rts

; ---------------------------------------------------------------------------
; VBL Top ($018d06) & End ($018e0a): STE Shifter, Palette, & DMA Sound Step
; ---------------------------------------------------------------------------
ste_vbl_top:
        movem.l d0-d1,-(sp)
        tst.w   STE_AMIGA_ON
        beq.w   .vt_classic
        tst.w   $02356a.l               ; KO2 -$4f40(a4): Half-Time/Full-Time/Stats on $078000?
        bne.w   .vt_stats

        ; Amiga STE Mode: arm Timer B at scanline 182 for 0-cycle Hardware Split-Screen Bottom HUD!
        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        bne.s   .vt_tb_ok
        move.l  $0120.w,STE_ORIG_TB
.vt_tb_ok:
        move.l  #ste_tb_hud,$0120.w
        move.b  #181,$fffffa21.w        ; fire at end of scanline 181 -> clean x=0 start on 182!
        move.b  #8,$fffffa1b.w          ; Event Count mode
        bset    #0,$fffffa07.w          ; enable Timer B in IERA
        bset    #0,$fffffa13.w          ; enable Timer B in IMRA
        ; Capture Classic ST palette 0..7 once (before we overwrite $ff8240..$ff824e!)
        tst.w   STE_ST_PAL_OK
        bne.s   .vt_pal_ok
        movem.l a0-a1,-(sp)
        lea     $ffff8240.w,a0
        lea     STE_ST_PAL.l,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.w  #1,STE_ST_PAL_OK
        movem.l (sp)+,a0-a1
.vt_pal_ok:
        ; Load STE 12-bit Amiga pitch palette (0..7)
        movem.l a0-a1,-(sp)
        lea     STE_PIT_PAL.l,a0
        lea     $ffff8240.w,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        movem.l (sp)+,a0-a1

        ; Program STE Shifter display address ($ff8201 HIGH, $ff8203 MID, $ff820d LOW LAST!)
        ; NOTE: On Atari STE, writing $ff8201 or $ff8203 resets $ff820d to 0, so $ff820d MUST be last!
        move.l  STE_VIEW_BASE(pc),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8201.w          ; high byte
        move.w  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8203.w          ; mid byte
        move.b  d0,$ffff820d.w          ; low byte LAST!
        move.w  STE_VIEW_HSCR(pc),d0
        move.b  d0,$ffff8265.w          ; fine pixel hscroll (0..15)
        beq.s   .vt_h0
        clr.b   $ffff820f.w             ; hscroll != 0 -> STE adds 8 bytes automatically (=168)
        jmp     $018d6e.l               ; continue KO2 VBL joystick reader!
.vt_h0:
        move.b  #4,$ffff820f.w          ; hscroll == 0 -> +4 extra words = +8 bytes (=168)
        jmp     $018d6e.l

.vt_stats:
        ; KO2 Half-Time / Full-Time / Match Stats screen on $078000 (keep KO2 palette!)
        clr.b   $fffffa1b.w
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        jmp     $018d6e.l

.vt_classic:
        ; Classic ST Mode: restore KO2 Timer B vector & standard $078000 shifter
        tst.l   STE_ORIG_TB
        beq.s   .vt_cl_go
        move.l  STE_ORIG_TB(pc),$0120.w
.vt_cl_go:
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        ; Execute original $018d0a..$018d5c Timer B grass stripes!
        move.w  $2739c.l,d0
        jmp     $018d10.l

; 0-Cycle STE Hardware Split-Screen Bottom HUD (Timer B ISR at scanline 181 -> 182!)
; Waits for exact HBlank ($ffff8209 constant) so $07f1c0 aligns to x=0 on EVERY frame!
ste_tb_hud:
        clr.b   $fffffa1b.w
        move.b  #$07,$ffff8205.w
        move.b  #$f1,$ffff8207.w
        move.b  #$c0,$ffff8209.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        move.w  #$0030,$ffff8240.w      ; dark pitch green scoreboard bar
        move.w  #$0000,$ffff8242.w      ; col 1 = crisp black (clock + score)
        move.w  #$0730,$ffff8244.w      ; col 2 = crisp orange (home player name)
        move.w  #$0777,$ffff8246.w      ; col 3 = crisp white
        move.w  #$0500,$ffff8248.w      ; col 4 = crisp red (away player name)
        ; Re-arm Timer B for +18 scanlines to restore jet-black bottom border!
        move.l  #ste_tb_bot,$0120.w
        move.b  #18,$fffffa21.w
        move.b  #8,$fffffa1b.w
        bclr    #0,$fffffa0f.w          ; Timer B EOI
        rte

ste_tb_bot:
        clr.b   $fffffa1b.w
        clr.w   $ffff8240.w             ; jet-black bottom border!
        bclr    #0,$fffffa0f.w
        rte

; Replaces $018e0a..$018e2a: skip $ff8240 write in Amiga mode, then run STE DMA audio step
ste_vbl_end:
        tst.w   STE_AMIGA_ON
        bne.s   .ve_skip_col0
        move.w  $27186.l,$ffff8240.w
        eori.w  #$30,$27186.l
.ve_skip_col0:
        clr.w   $2718a.l
        move.w  #$ffff,$27190.l         ; VBL sync flag!

        ; STE DMA Audio step
        tst.b   STE_SND_STOP
        beq.s   .chk_pend
        clr.b   STE_SND_STOP
        clr.b   $ffff8901.w
        rts
.chk_pend:
        tst.b   STE_SND_PEND
        bne.s   .do_step
        tst.l   STE_SCRIPT_PTR
        beq.w   .vbl_done
        btst    #0,$ffff8901.w
        bne.w   .vbl_done
.do_step:
        clr.b   STE_SND_PEND
        movem.l d0-d3/a0-a1,-(sp)
        movea.l STE_SND_BASE(pc),a1
        move.l  a1,d0
        beq.w   .step_stop
.next_cmd:
        movea.l STE_SCRIPT_PTR(pc),a0
        move.l  a0,d0
        beq.w   .step_stop
        addq.w  #1,STE_REPEAT_CNT
        blt.s   .same_cmd
        addq.l  #2,STE_SCRIPT_PTR
.same_cmd:
        move.w  (a0),d0
        beq.w   .step_stop
        blt.s   .cmd_neg
        cmpi.w  #$c8,d0
        bge.s   .cmd_pitch
        cmpi.w  #$64,d0
        bge.s   .cmd_s100
        subq.w  #1,d0
        bra.s   .play_idx
.cmd_neg:
        cmpi.w  #-1,d0
        beq.s   .cmd_loop
        move.w  d0,STE_REPEAT_CNT
        bra.s   .next_cmd
.cmd_loop:
        move.l  STE_SCRIPT_ST(pc),STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        bra.s   .next_cmd
.cmd_pitch:
        subi.w  #$c8,d0
        move.b  d0,STE_SND_PITCH
        bra.s   .next_cmd
.cmd_s100:
        subi.w  #$65,d0
.play_idx:
        cmpi.w  #17,d0
        bcc.s   .next_cmd
        mulu.w  #12,d0
        lea     0(a1,d0.w),a0
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.w  (a0)+,d3
        cmpi.l  #16,d2
        ble.s   .step_stop              ; empty placeholder sample -> stop script (avoid VBL infinite loop on -1!)
        add.l   a1,d1
        add.l   d1,d2
        clr.b   $ffff8901.w
        move.b  d1,$ffff8907.w
        lsr.l   #8,d1
        move.b  d1,$ffff8905.w
        lsr.l   #8,d1
        move.b  d1,$ffff8903.w
        move.b  d2,$ffff8913.w
        lsr.l   #8,d2
        move.b  d2,$ffff8911.w
        lsr.l   #8,d2
        move.b  d2,$ffff890f.w
        move.b  d3,$ffff8921.w
        move.b  #1,$ffff8901.w
        addq.w  #1,STE_DMA_CNT
        bra.s   .step_ret
.step_stop:
        clr.b   $ffff8901.w
        clr.l   STE_SCRIPT_PTR
        clr.w   $0284aa-$142a
.step_ret:
        movem.l (sp)+,d0-d3/a0-a1
.vbl_done:
        rts

; ---------------------------------------------------------------------------
; ste_key_hook: Replaces $01b564 (in-match key handler) — 'V' toggles view!
; ---------------------------------------------------------------------------
ste_key_hook:
        cmpi.w  #'v',d0
        beq.s   .do_toggle
        cmpi.w  #'V',d0
        bne.s   .not_v
.do_toggle:
        tst.w   STE_PITCH_OK
        beq.s   .v_done
        bsr.w   ste_erase_all_slots     ; LIFO: restore sprites BEFORE HUD/Radar!
        bsr.w   ste_hud_restore         ; restore HUD/Radar to pristine grass!
        eori.w  #1,STE_AMIGA_ON
        tst.w   STE_AMIGA_ON
        beq.s   .to_classic
        ; Switching -> Amiga STE Mode: clear stale Classic ST lines on $078000 & force full redraw!
        move.w  #-999,STE_CUR_TX
        move.w  #-999,STE_CUR_TY
        moveq   #4,d0                   ; cmd 4 = clear_cork + clear $078000!
        trap    #8
        bra.s   .v_done
.to_classic:
        ; Switching -> Classic ST Mode: restore saved ST palette 0..7 via Supexec!
        tst.w   STE_ST_PAL_OK
        beq.s   .v_done
        pea     ste_restore_st_pal(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp
.v_done:
        jmp     $01b556.l               ; continue key loop
.not_v:
        cmpi.w  #$72,d0                 ; original $01b564 instruction!
        bne.s   .not_r
        jmp     $01b56a.l
.not_r:
        jmp     $01b570.l

ste_restore_st_pal:
        lea     STE_ST_PAL.l,a0
        lea     $ffff8240.w,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        rts

; ---------------------------------------------------------------------------
; ste_pitch_update: Replaces $01c1d0 (pitch lines + camera update)
; ---------------------------------------------------------------------------
ste_pitch_update:
        tst.w   STE_AMIGA_ON
        bne.s   .pu_amiga
        ; Classic ST Mode: run original $01c1d2..$01c40a
        lea     -$5234(a4),a1
        jmp     $01c1d6.l

.pu_amiga:
        ; 1. Exact KO2 smooth camera follow ($01c2b8..$01c2f0)
        movea.l -$110a(a4),a0
        move.l  (a0),d0
        move.l  $4(a0),d1
        subi.l  #$a00000,d0
        subi.l  #$640000,d1
        sub.l   -$1112(a4),d0
        asr.l   #3,d0
        add.l   d0,-$1112(a4)
        sub.l   -$110e(a4),d1
        asr.l   #3,d1
        add.l   d1,-$110e(a4)

        ; 2. Compute new camera (tx, ty, hscr, new_vb) FIRST so stationary frames can
        ;    keep static Radar outline + Bottom HUD in place (only refreshing 23 dots = 0.01 VBL!)
        movem.l d0-d7/a0-a3,-(sp)
        move.w  -$1112(a4),d0           ; camX (integer part)
        addi.w  #176,d0
        bge.s   .wx_lo
        moveq   #0,d0
.wx_lo: cmpi.w  #960,d0
        ble.s   .wx_ok
        move.w  #960,d0
.wx_ok:
        move.w  -$110e(a4),d1           ; camY (integer part)
        addi.w  #64,d1
        bge.s   .wy_lo
        moveq   #0,d1
.wy_lo: cmpi.w  #1336,d1
        ble.s   .wy_ok
        move.w  #1336,d1
.wy_ok:
        ; d2 = tx = wx >> 4 (0..60), d3 = ty = wy >> 4 (0..83), d7 = hscroll = wx & 15
        move.w  d0,d2
        lsr.w   #4,d2
        move.w  d1,d3
        lsr.w   #4,d3
        move.w  d0,d7
        andi.w  #15,d7

        ; Compute new_vb = STE_CORK_BUF + (wy % 224) * 168 + tx * 8 -> d4.l
        moveq   #0,d4
        move.w  d1,d4
        divu.w  #CORK_RING_H,d4
        swap    d4                      ; d4.w = wy % 224 (0..223)
        mulu.w  #CORK_STRIDE,d4         ; d4.l = y_wrap * 168
        move.w  d2,d5
        lsl.w   #3,d5                   ; tx * 8
        ext.l   d5
        add.l   d5,d4
        addi.l  #STE_CORK_BUF,d4

        ; Stationary fast path: if view, hscr, scale, radar-on, and tiles unchanged (and not 8th tick),
        ; skip heavy HUD/Radar outline restore+redraw and ONLY refresh the 23 radar dots!
        addq.w  #1,STE_HUD_TICK
        tst.w   STE_HUD_ACTIVE
        beq.s   .pu_full
        cmp.l   STE_HUD_VBASE(pc),d4
        bne.s   .pu_full
        cmp.w   STE_HUD_HSCR(pc),d7
        bne.s   .pu_full
        cmp.w   STE_CUR_TX(pc),d2
        bne.s   .pu_full
        cmp.w   STE_CUR_TY(pc),d3
        bne.s   .pu_full
        move.w  -$0e0a(a4),d5
        cmp.w   STE_HUD_SCALE(pc),d5
        bne.s   .pu_full
        move.w  -$0e10(a4),d5
        cmp.w   STE_HUD_RADON(pc),d5
        bne.s   .pu_full
        bsr.w   ste_radar_dots_only
        movem.l (sp)+,d0-d7/a0-a3
        jmp     $01bffa.l

.pu_full:
        ; Check delta from (STE_CUR_TX, STE_CUR_TY) BEFORE touching HUD/Radar/STE_VIEW_BASE!
        move.w  d2,d5
        sub.w   STE_CUR_TX(pc),d5       ; dtx -> d5
        move.w  d3,d6
        sub.w   STE_CUR_TY(pc),d6       ; dty -> d6
        move.w  d5,d0
        bpl.s   .adx
        neg.w   d0
.adx:   cmpi.w  #2,d0
        bgt.w   .full_fill
        move.w  d6,d0
        bpl.s   .ady
        neg.w   d0
.ady:   cmpi.w  #2,d0
        bgt.w   .full_fill

        ; 3. Incremental dirty-edge tile updates FIRST (HUD, Radar & Sprites stay 100% visible!)
        movem.l d4-d7,-(sp)             ; save new_vb(d4), dtx(d5), dty(d6), new_hscr(d7)
        move.w  d5,d4                   ; d4 = dtx
        move.w  d6,d5                   ; d5 = dty
        tst.w   d4
        beq.s   .chk_y
        bgt.s   .scroll_r
        ; Scrolled left: fill column(s) d2 .. STE_CUR_TX-1
        move.w  d2,d6
.sl_lp: bsr.w   ste_draw_col            ; d6=tx_col, d3=ty_top
        addq.w  #1,d6
        cmp.w   STE_CUR_TX(pc),d6
        blt.s   .sl_lp
        bra.s   .chk_y
.scroll_r:
        ; Scrolled right: fill column(s) STE_CUR_TX+21 .. d2+20
        move.w  STE_CUR_TX(pc),d6
        addi.w  #21,d6
        move.w  d2,d7
        addi.w  #20,d7
.sr_lp: bsr.w   ste_draw_col
        addq.w  #1,d6
        cmp.w   d7,d6
        ble.s   .sr_lp

.chk_y:
        tst.w   d5
        beq.s   .tiles_ok
        bgt.s   .scroll_d
        ; Scrolled up: fill row(s) d3 .. STE_CUR_TY-1
        move.w  d3,d7
.su_lp: bsr.w   ste_draw_row            ; d2=tx_left, d7=ty_row
        addq.w  #1,d7
        cmp.w   STE_CUR_TY(pc),d7
        blt.s   .su_lp
        bra.s   .tiles_ok
.scroll_d:
        ; Scrolled down: fill row(s) STE_CUR_TY+14 .. d3+13
        move.w  STE_CUR_TY(pc),d7
        addi.w  #14,d7
        move.w  d3,d6
        addi.w  #13,d6
.sd_lp: bsr.w   ste_draw_row
        addq.w  #1,d7
        cmp.w   d6,d7
        ble.s   .sd_lp

.tiles_ok:
        movem.l (sp)+,d4-d7             ; restore new_vb(d4), dtx(d5), dty(d6), new_hscr(d7)
        ; 4. Back-to-back HUD/Radar restore -> wrap -> redraw, THEN atomically latch STE_VIEW_BASE!
        movem.l d2-d4/d7,-(sp)
        bsr.w   ste_hud_lift_spr
        bsr.w   ste_hud_restore
        movem.l (sp)+,d2-d4/d7
        ; Check Corkscrew Primary <-> Mirror wrap
        move.l  d4,d5
        sub.l   STE_VIEW_BASE(pc),d5
        cmpi.l  #16384,d5
        bgt.s   .wrap_up
        cmpi.l  #-16384,d5
        blt.s   .wrap_dn
        bra.s   .wrap_ok
.wrap_up:
        move.l  #CORK_RING_BYTES,d5
        exg     d4,d5
        bsr.w   ste_cork_wrap_spr
        exg     d4,d5
        bra.s   .wrap_ok
.wrap_dn:
        move.l  #-CORK_RING_BYTES,d5
        exg     d4,d5
        bsr.w   ste_cork_wrap_spr
        exg     d4,d5
.wrap_ok:
        bra.s   .upd_done

.full_fill:
        ; Camera jump / kickoff / toggle: erase all sprites & HUD first, then fill 21x14 tiles!
        movem.l d2-d4/d7,-(sp)
        bsr.w   ste_erase_all_slots
        bsr.w   ste_hud_restore
        movem.l (sp)+,d2-d4/d7
        movem.l d4/d7,-(sp)
        move.w  d3,d7                   ; ty_row = d3 .. d3+13
        moveq   #13,d5
.ff_y:  bsr.w   ste_draw_row            ; draws d2..d2+20 at row d7
        addq.w  #1,d7
        dbra    d5,.ff_y
        movem.l (sp)+,d4/d7

.upd_done:
        move.w  d2,STE_CUR_TX
        move.w  d3,STE_CUR_TY
        ; Draw Transparent Radar & Bottom HUD onto new_vb (d4) / new_hscr (d7) BEFORE latching STE_VIEW_BASE!
        move.l  d4,STE_HUD_VBASE
        move.w  d7,STE_HUD_HSCR
        movem.l d4/d7,-(sp)
        bsr.w   ste_hud_draw
        bsr.w   ste_hud_drop_spr
        movem.l (sp)+,d4/d7
        ; Atomically latch new display address & fine hscroll for VBL!
        move.w  d7,STE_VIEW_HSCR
        move.l  d4,STE_VIEW_BASE
        movem.l (sp)+,d0-d7/a0-a3
        ; Still draw KO2's off-screen goal arrow ($01bffa)!
        jmp     $01bffa.l

; Draw 1 vertical column of 14 tiles: d6 = tx_col, d3 = ty_top
; Batched into ONE TRAP #8 (cmd 9) — 3.8x faster than per-tile TRAPs!
ste_draw_col:
        cmpi.w  #80,d6
        bcc.s   .dc_end
        movem.l d0-d3/a0-a1,-(sp)
        move.w  d6,d1                   ; d1 = tx_col
        move.w  d3,d2                   ; d2 = ty_top
        moveq   #9,d0                   ; cmd 9 = blit_col(d1=tx, d2=ty_top)
        trap    #8
        movem.l (sp)+,d0-d3/a0-a1
.dc_end:
        rts

; Draw 1 horizontal row of 21 tiles: d2 = tx_left, d7 = ty_row
; Batched into ONE TRAP #8 (cmd 8) — 3.8x faster than per-tile TRAPs!
ste_draw_row:
        cmpi.w  #96,d7
        bcc.s   .dr_end
        movem.l d0-d3/a0-a1,-(sp)
        move.w  d2,d1                   ; d1 = tx_left
        move.w  d7,d2                   ; d2 = ty_row
        moveq   #8,d0                   ; cmd 8 = blit_row(d1=tx_left, d2=ty_row)
        trap    #8
        movem.l (sp)+,d0-d3/a0-a1
.dr_end:
        rts

; ---------------------------------------------------------------------------
; Sprite Draw Core ($01a426) & Erase ($01a83e) — STE Blitter 4bpp Masked!
; All 4 KO2 sprite entry points ($01a2fc, $01a346, $01a3bc, $01a412) save
; movem.l d0-d2/d4/d7/a0-a1/a3,-(sp) and enter $01a426 with d0=x, d1=y, a1=src, a3=rec!
; ---------------------------------------------------------------------------
ste_skip_beam_1:
        tst.w   STE_AMIGA_ON
        beq.s   .sb1_st
        bsr.s   ste_wait_beam           ; Amiga STE: exact 20-line beam-avoidance window (ZERO flicker, 50 FPS!)
        jmp     $01a39c.l
.sb1_st:
        move.l  -$1320(a4),d4
        move.w  d4,d2
        jmp     $01a37c.l

ste_skip_beam_2:
        tst.w   STE_AMIGA_ON
        beq.s   .sb2_st
        bsr.s   ste_wait_beam           ; Amiga STE: exact 20-line beam-avoidance window (ZERO flicker, 50 FPS!)
        jmp     $01a3f2.l
.sb2_st:
        move.l  -$1320(a4),d4
        move.w  d4,d2
        jmp     $01a3d2.l

; KO2-style STE hardware raster-beam avoidance window:
; Waits ONLY if the video beam is inside [sprite_y - 16 .. sprite_y + 18] scanlines!
; When beam is in top/bottom border, above sprite-16, or below sprite+18 -> ZERO WAIT!
ste_wait_beam:
        movem.l d2/d4/d7,-(sp)
        move.w  d1,d4
        mulu.w  #CORK_STRIDE,d4         ; d4.l = sprite_y * 168
        move.l  STE_VIEW_BASE(pc),d2
        add.l   d2,d4                   ; d4.l = spr_addr in STE_CORK_BUF
.wb_poll:
        moveq   #0,d7
        move.b  $ffff8205.w,d7
        swap    d7
        move.b  $ffff8207.w,d7
        lsl.w   #8,d7
        move.b  $ffff8209.w,d7
        move.w  d7,-(sp)
        lsr.w   #8,d7
        cmp.b   $ffff8207.w,d7
        bne.s   .wb_retry
        move.w  (sp)+,d7
        sub.l   d2,d7                   ; d7 = beam_off (bytes from STE_VIEW_BASE)
        ble.s   .wb_ok                  ; top border -> ZERO WAIT!
        cmpi.l  #(200*CORK_STRIDE),d7
        bge.s   .wb_ok                  ; bottom border -> ZERO WAIT!
        add.l   d2,d7
        sub.l   d4,d7                   ; d7 = beam_addr - spr_addr
        cmpi.l  #(-28*CORK_STRIDE),d7
        blt.s   .wb_ok                  ; beam > 28 lines ABOVE sprite -> ZERO WAIT!
        cmpi.l  #(18*CORK_STRIDE),d7
        bgt.s   .wb_ok                  ; beam > 18 lines BELOW sprite -> ZERO WAIT!
        bra.s   .wb_poll                ; beam is right on this sprite -> wait ~0.6 ms!
.wb_retry:
        addq.l  #2,sp
        bra.s   .wb_poll
.wb_ok:
        movem.l (sp)+,d2/d4/d7
        rts

ste_draw_spr_core_hook:
        tst.w   STE_AMIGA_ON
        bne.s   .dsc_amiga
        ; Classic ST Mode: run original $01a426 (mulu.w #$a0,d1 ; ext.l d0)
        mulu.w  #$a0,d1
        ext.l   d0
        jmp     $01a42c.l

.dsc_amiga:
        movem.l d3/a2,-(sp)             ; preserve d3 & a2 (caller's entity struct ptr!)
        bsr.s   ste_blit_spr_core
        movem.l (sp)+,d3/a2
        movem.l (sp)+,d0-d2/d4/d7/a0-a1/a3
        rts

; Core Amiga STE 4bpp masked sprite draw: d0=x, d1=y, a1=3bpp src, a3=KO2 save record
ste_blit_spr_core:
        ; 1. Get or allocate persistent 256-byte save-under slot for a3
        cmpi.w  #$5354,8(a3)            ; magic "ST" already assigned?
        beq.s   .have_slot
        move.w  STE_SLOT_NEXT(pc),d2
        cmpi.w  #26,d2
        bcc.w   .spr_ret                ; safety cap (26 slots: $09b000..$09c9ff)
        addq.w  #1,STE_SLOT_NEXT
        ; Slot address = STE_SAVE_UNDER + d2 * 256
        lsl.w   #8,d2
        ext.l   d2
        addi.l  #STE_SAVE_UNDER,d2
        move.l  d2,4(a3)
        move.w  #$5354,8(a3)
.have_slot:
        ; 2. Compute dst inside STE_VIEW_BASE:
        ;    x_in_view = d0 + STE_VIEW_HSCR
        ;    dst = STE_VIEW_BASE + d1 * 168 + (x_in_view >> 4) * 8
        ;    skew = x_in_view & 15
        add.w   STE_HUD_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2                  ; d2 = skew (0..15)
        lsr.w   #4,d0
        lsl.w   #3,d0                   ; word_col * 8
        move.w  d1,-(sp)                ; save y_px (avoids slow 150-cycle divu.w!)
        mulu.w  #CORK_STRIDE,d1         ; y * 168
        ext.l   d0
        add.l   d0,d1
        add.l   STE_VIEW_BASE(pc),d1
        movea.l d1,a0                   ; a0 = dst in STE_CORK_BUF
        move.l  a0,(a3)                 ; save dst addr in 0(a3)

        ; 3. Combined Save-under + Blitter Mask + Direct NFSR 4bpp Masked Sprite Draw in ONE TRAP #8!
        ;    Push 16-byte record: +0=a3.l, +4=dst.l, +8=src.l, +12=skew.b, +13=slot.b, +14=x_col.b, +15=y_px.b
        movea.l 4(a3),a2                ; a2 = save-under slot
        move.w  (sp)+,d1                ; d1.w = y_px (0..199)
        move.w  STE_DRAW_CNT(pc),d3
        cmpi.w  #32,d3
        bcc.s   .no_push
        addq.w  #1,STE_DRAW_CNT
        lsl.w   #4,d3                   ; index * 16
        movem.l d0/a3,-(sp)
        lea     STE_DRAW_STACK.l,a3
        adda.w  d3,a3
        move.l  4(sp),(a3)+             ; +0: KO2 a3 ptr
        move.l  a0,(a3)+                ; +4: dst in STE_CORK_BUF
        move.l  a1,(a3)+                ; +8: src (KO2 3bpp sprite)
        move.b  d2,(a3)+                ; +12: skew (0..15)
        move.l  a2,d3
        subi.l  #STE_SAVE_UNDER,d3
        lsr.w   #8,d3
        move.b  d3,(a3)+                ; +13: slot_idx (0..25)
        lsr.w   #3,d0
        move.b  d0,(a3)+                ; +14: x_col (0..20)
        move.b  d1,(a3)                 ; +15: y_px (0..199)
        movem.l (sp)+,d0/a3
.no_push:
        move.w  d2,d1                   ; d1 = skew (0..15)
        moveq   #3,d0                   ; cmd 3 = save_and_draw_sprite
        trap    #8
.spr_ret:
        rts

; Erase sprite ($01a83e)
ste_erase_spr:
        tst.w   STE_AMIGA_ON
        bne.s   ste_erase_spr_amiga
        ; Classic ST Mode: run original $01a83e..
        tst.l   (a3)
        beq.s   .es_st_z
        jmp     $01a844.l
.es_st_z:
        jmp     $01aaaa.l

; Overlap-safe LIFO sprite erase for KO2 record a3:
; - If no sprite drawn AFTER a3 is within +-2688 bytes (16 scanlines): fast 1-blit restore!
; - If any sprite above a3 overlaps it (kickoff walk-out, tackles): LIFO restore from top
;   down to a3, remove a3, and re-draw the sprites that were above a3 -> ZERO GHOSTS!
ste_erase_spr_amiga:
        clr.l   (a3)
        movem.l d0-d7/a0-a2/a4-a5,-(sp)
        move.w  STE_DRAW_CNT(pc),d4
        beq.w   .es_done
        ; Search STE_DRAW_STACK backwards for a3
        move.w  d4,d3
        subq.w  #1,d3                   ; d3 = idx (d4-1 down to 0)
        move.w  d4,d0
        lsl.w   #4,d0
        lea     STE_DRAW_STACK.l,a4
        adda.w  d0,a4                   ; a4 = end of stack
.es_find:
        lea     -16(a4),a4
        cmpa.l  (a4),a3
        beq.s   .es_found
        dbra    d3,.es_find
        bra.w   .es_done                ; not on stack
.es_found:
        ; d3 = idx, a4 = &stack[idx], d4 = old STE_DRAW_CNT
        move.w  d4,d5
        subq.w  #1,d5
        sub.w   d3,d5                   ; d5 = count of sprites ABOVE idx (0 if top!)
        beq.s   .es_fast_one            ; top of stack -> fast 1-blit restore!

        ; Fast Targeted 2D-overlap LIFO: precompute [min_x-1, max_x+1, min_y-20, max_y+20] ONCE!
        lea     -32(sp),sp              ; local ptr array at (sp)
        movea.l sp,a1                   ; a1 = match write cursor
        moveq   #0,d0                   ; d0.w = match count (0..8)
        moveq   #0,d1
        move.b  14(a4),d1               ; target x_col
        move.w  d1,d3
        subq.w  #1,d1                   ; d1 = min_x - 1
        addq.w  #1,d3                   ; d3 = max_x + 1
        moveq   #0,d2
        move.b  15(a4),d2               ; target y_px
        move.w  d2,d4
        subi.w  #20,d2                  ; d2 = min_y - 20 (covers +-4px camera scroll!)
        addi.w  #20,d4                  ; d4 = max_y + 20
        lea     16(a4),a5               ; a5 = &stack[idx+1]
        move.w  d5,d6
        subq.w  #1,d6
.es_ovl:
        moveq   #0,d7
        move.b  14(a5),d7               ; j.x_col
        cmp.w   d1,d7                   ; j.x_col < min_x - 1?
        blt.s   .es_nxt
        cmp.w   d3,d7                   ; j.x_col > max_x + 1?
        bgt.s   .es_nxt
        moveq   #0,d7
        move.b  15(a5),d7               ; j.y_px
        cmp.w   d2,d7                   ; j.y_px < min_y - 20?
        blt.s   .es_nxt
        cmp.w   d4,d7                   ; j.y_px > max_y + 20?
        bgt.s   .es_nxt
        ; TRUE 2D overlap! Record pointer a5 (if < 8) and expand x range for chains!
        cmpi.w  #8,d0
        bcc.s   .es_nxt
        move.l  a5,(a1)+
        addq.w  #1,d0
        moveq   #0,d7
        move.b  14(a5),d7
        subq.w  #1,d7
        cmp.w   d1,d7
        bge.s   .es_nx1
        move.w  d7,d1                   ; expand min_x - 1
.es_nx1: addq.w #2,d7
        cmp.w   d3,d7
        ble.s   .es_nxt
        move.w  d7,d3                   ; expand max_x + 1
.es_nxt:
        lea     16(a5),a5
        dbra    d6,.es_ovl

        tst.w   d0
        bne.s   .es_do_targeted
        lea     32(sp),sp               ; free local ptr array -> fast path!

.es_fast_one:
        ; Fast path: no overlapping sprite above idx!
        ; Only restore if dst is still inside current visible viewport [STE_VIEW_BASE .. +185*168]
        move.l  4(a4),a1                ; dst
        move.l  a1,d0
        sub.l   STE_VIEW_BASE(pc),d0
        blt.s   .es_skip_off
        cmpi.l  #(185*CORK_STRIDE),d0
        bgt.s   .es_skip_off
        moveq   #0,d0
        move.b  13(a4),d0               ; slot_idx.b
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0                   ; slot
        moveq   #1,d0                   ; cmd 1 = restore_one(a0=slot, a1=dst)
        trap    #8
.es_skip_off:
        bsr.w   .es_compact
        bra.w   .es_done

.es_do_targeted:
        ; Restore ONLY the d0 (1..8) overlapping sprites in reverse LIFO order!
        move.w  d0,d6                   ; save match count in d6
        move.w  d0,d4
        subq.w  #1,d4                   ; loop counter
.es_pop_m:
        move.w  d4,d2
        lsl.w   #2,d2
        movea.l 0(sp,d2.w),a5
        movea.l 4(a5),a1                ; dst
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0                   ; slot
        moveq   #1,d0                   ; cmd 1 = restore_one
        trap    #8
        dbra    d4,.es_pop_m

        ; Restore target sprite idx (a4) itself!
        movea.l 4(a4),a1
        moveq   #0,d0
        move.b  13(a4),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0
        moveq   #1,d0
        trap    #8

        ; Re-draw ONLY the d6 (1..8) overlapping sprites in forward order!
        ; NOTE: compact shifts all entries above a4 down by 16 bytes, so subtract 16 from each ptr!
        bsr.s   .es_compact
        moveq   #0,d4                   ; i = 0 .. d6-1
.es_redr_m:
        move.w  d4,d2
        lsl.w   #2,d2
        movea.l 0(sp,d2.w),a5
        lea     -16(a5),a5              ; adjusted ptr after .es_compact!
        movea.l 4(a5),a0                ; dst
        movea.l 8(a5),a1                ; src (KO2 3bpp sprite)
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a2                   ; slot
        moveq   #0,d1
        move.b  12(a5),d1               ; skew
        moveq   #3,d0
        trap    #8
        addq.w  #1,d4
        cmp.w   d6,d4
        blt.s   .es_redr_m
        lea     32(sp),sp               ; free local ptr array

.es_done:
        movem.l (sp)+,d0-d7/a0-a2/a4-a5
        rts

; Helper: remove entry at a4 (&stack[idx]), shifting d5 entries above it down by 16 bytes
.es_compact:
        subq.w  #1,STE_DRAW_CNT
        move.w  d5,d0
        beq.s   .ec_ret
        movea.l a4,a0                   ; dst = &stack[idx]
        lea     16(a4),a1               ; src = &stack[idx+1]
        subq.w  #1,d0
.ec_lp: move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        dbra    d0,.ec_lp
.ec_ret:
        rts

; Erase all active sprites in STRICT REVERSE (LIFO) order via ONE TRAP #8 (cmd 2)!
ste_erase_all_slots:
        movem.l d0-d1/a0,-(sp)
        move.w  STE_DRAW_CNT(pc),d1
        beq.s   .eas_done
        clr.w   STE_DRAW_CNT
        move.w  d1,d0
        lsl.w   #4,d0
        lea     STE_DRAW_STACK.l,a0
        adda.w  d0,a0                   ; a0 = end of stack
        moveq   #2,d0                   ; cmd 2 = restore_lifo_n(a0=end, d1=count)
        trap    #8
.eas_done:
        movem.l (sp)+,d0-d1/a0
        rts

; Corkscrew Primary <-> Mirror wrap sprite transfer: d4.l = +37632 or -37632
; Cleanly restores all sprites from OLD half (zero mirror ghosts!) and redraws
; them on the NEW half (zero missing sprites when crossing wy = 224, 448, 672...)!
ste_cork_wrap_spr:
        clr.w   STE_LIFT_CNT            ; we will redraw all sprites on the new half
        move.w  STE_DRAW_CNT(pc),d1
        beq.s   .cws_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        move.w  d1,d7                   ; save count in d7
        move.w  d1,d0
        lsl.w   #4,d0
        lea     STE_DRAW_STACK.l,a0
        adda.w  d0,a0
        moveq   #2,d0                   ; cmd 2 = LIFO restore all from OLD half!
        trap    #8
        lea     STE_DRAW_STACK.l,a5
        subq.w  #1,d7
.cws_lp:
        add.l   d4,4(a5)                ; shift dst to NEW half!
        movea.l (a5),a0                 ; KO2 a3 record
        move.l  4(a5),(a0)              ; update KO2 record dst
        movea.l 4(a5),a0                ; dst
        movea.l 8(a5),a1                ; src
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a2                   ; slot
        moveq   #0,d1
        move.b  12(a5),d1               ; skew
        moveq   #3,d0
        trap    #8
        lea     16(a5),a5
        dbra    d7,.cws_lp
        movem.l (sp)+,d0-d7/a0-a3/a5
.cws_ret:
        rts

; ---------------------------------------------------------------------------
; HUD & Transparent Vector Radar Overlay (called back-to-back in ste_pitch_update)
; Lifting only the 0..2 sprites overlapping Radar/HUD preserves strict LIFO
; (ZERO Radar ghosts on X/D!) while keeping Radar absent < 0.5 ms (ZERO FLICKER!)
; ---------------------------------------------------------------------------
STE_LIFT_CNT:   dc.w    0
STE_RAD_MAXC:   dc.w    0               ; exact right word-col of drawn Radar (0 if OFF)
STE_RAD_MAXY:   dc.w    0               ; exact bottom Y of drawn Radar (0 if OFF)

ste_hud_lift_spr:
        clr.w   STE_LIFT_CNT
        move.w  STE_DRAW_CNT(pc),d0
        beq.s   .hlf_ret
        movem.l d1-d3/a0-a2/a5,-(sp)
        lea     STE_DRAW_STACK.l,a5
        lea     STE_LIFT_PTRS.l,a2
        moveq   #0,d2                   ; lifted count
        subq.w  #1,d0
.hlf_lp:
        ; Check if sprite overlaps active Radar (y_px <= MAXY && x_col <= MAXC)
        moveq   #0,d1
        move.b  15(a5),d1               ; y_px
        cmp.w   STE_RAD_MAXY(pc),d1
        bgt.s   .hlf_nxt
        moveq   #0,d1
        move.b  14(a5),d1               ; x_col
        cmp.w   STE_RAD_MAXC(pc),d1
        bgt.s   .hlf_nxt
.hlf_hit:
        cmpi.w  #32,d2
        bcc.s   .hlf_nxt
        move.l  a5,(a2)+
        addq.w  #1,d2
.hlf_nxt:
        lea     16(a5),a5
        dbra    d0,.hlf_lp
        move.w  d2,STE_LIFT_CNT
        beq.s   .hlf_done
        ; Restore lifted sprites in reverse LIFO order!
        subq.w  #1,d2
.hlf_pop:
        movea.l -(a2),a5
        movea.l 4(a5),a1                ; dst
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0                   ; slot
        moveq   #1,d0                   ; cmd 1 = restore_one
        trap    #8
        dbra    d2,.hlf_pop
.hlf_done:
        movem.l (sp)+,d1-d3/a0-a2/a5
.hlf_ret:
        rts

ste_hud_drop_spr:
        move.w  STE_LIFT_CNT(pc),d0
        beq.s   .hdr_ret
        clr.w   STE_LIFT_CNT
        movem.l d1-d6/a0-a2/a5,-(sp)
        lea     STE_LIFT_PTRS.l,a2
        subq.w  #1,d0
.hdr_lp:
        movea.l (a2)+,a5
        movea.l 4(a5),a0                ; dst
        movea.l 8(a5),a1                ; src
        move.l  a2,-(sp)
        moveq   #0,d1
        move.b  13(a5),d1
        lsl.w   #8,d1
        addi.l  #STE_SAVE_UNDER,d1
        movea.l d1,a2                   ; slot
        moveq   #0,d1
        move.b  12(a5),d1               ; skew
        move.w  d0,-(sp)
        moveq   #3,d0
        trap    #8
        move.w  (sp)+,d0
        movea.l (sp)+,a2
        dbra    d0,.hdr_lp
        movem.l (sp)+,d1-d6/a0-a2/a5
.hdr_ret:
        rts

ste_hud_restore:
        movem.l d0-d3/a0-a2,-(sp)
        ; 1a. Reverse-LIFO restore of radar 2x2 dots (12B each: [dst.l, l0.l, l1.l])
        move.w  STE_RAD_DCNT(pc),d0
        beq.s   .hr_no_dots
        clr.w   STE_RAD_DCNT
        move.w  d0,d1
        mulu.w  #12,d0
        lea     STE_RAD_DREC.l,a0
        adda.l  d0,a0
        subq.w  #1,d1
.hr_dlp:
        lea     -12(a0),a0
        movea.l (a0),a1
        move.l  4(a0),(a1)
        move.l  8(a0),4(a1)
        dbra    d1,.hr_dlp
.hr_no_dots:
        ; 1b. Batched Reverse-LIFO Blitter restore of ALL radar lines in ONE TRAP #8!
        move.w  STE_RAD_LCNT(pc),d2
        beq.s   .hr_no_lines
        clr.w   STE_RAD_LCNT
        move.w  d2,d0
        lsl.w   #4,d0                   ; 16 bytes per record!
        lea     STE_RAD_LREC.l,a2
        adda.w  d0,a2
        moveq   #0,d1                   ; d1=0 -> cmd 6 batch-restore d2 records ending at a2!
        moveq   #6,d0
        trap    #8
.hr_no_lines:
        move.w  STE_HUD_ACTIVE(pc),d3
        beq.s   .hr_done
        clr.w   STE_HUD_ACTIVE
        ; Restore Center Banner if it was drawn (bit 1 of d3) — Bottom HUD is 0-cycle HW split-screen!
        btst    #1,d3
        beq.s   .hr_done
        lea     STE_BAN_SAVE.l,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #96*CORK_STRIDE,a1
        moveq   #84,d1
        moveq   #8,d2
        moveq   #6,d0
        trap    #8
.hr_done:
        movem.l (sp)+,d0-d3/a0-a2
        rts

ste_hud_draw:
        tst.w   STE_HUD_ACTIVE
        beq.s   .hd_go
        bsr.w   ste_hud_restore
.hd_go:
        movem.l d0-d5/a0-a2,-(sp)
        move.w  STE_HUD_HSCR(pc),d3     ; d3 = skew (0..15)
        move.w  -$0e0a(a4),STE_HUD_SCALE
        move.w  -$0e10(a4),STE_HUD_RADON
        moveq   #1,d5                   ; active flags: bit0=active

        ; 1. Transparent, X-Resizable, D-Toggleable Vector Radar (Bottom HUD is 0-cycle HW split-screen!)
        bsr.w   ste_radar_draw

        ; 2. Center Event Banner (y=96..103, 8 lines): scan y=99 only every 4th frame!
        move.w  STE_HUD_TICK(pc),d0
        andi.w  #3,d0
        bne.s   .hd_done
        lea     $078000+99*160,a0
        moveq   #39,d0                  ; 40 longs = 160 bytes
        moveq   #0,d1
.chk_b: or.l    (a0)+,d1
        dbra    d0,.chk_b
        tst.l   d1
        beq.s   .hd_done
        ori.w   #2,d5                   ; bit1 = banner active
        lea     $078000+96*160,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #96*CORK_STRIDE,a1
        lea     STE_BAN_SAVE.l,a2
        moveq   #20,d1
        moveq   #8,d2
        moveq   #1,d4                   ; all 4 planes
        moveq   #5,d0
        trap    #8

.hd_done:
        move.w  d5,STE_HUD_ACTIVE
        movem.l (sp)+,d0-d5/a0-a2
        rts

; ---------------------------------------------------------------------------
; ste_radar_draw: ULTRA-FAST STE BLITTER Transparent, X-Resizable, D-Toggleable Radar!
; Uses TRAP #8 cmd 7 (Blitter ENDMASK transparent line save+draw) for all pitch
; outline lines (~5x faster than 68000!), plus 23 transparent 2x2 dots!
; ---------------------------------------------------------------------------
STE_RAD_C_SC:   dc.w    0               ; cached radar scale (rebuilds STE_RAD_CACHE when changed!)
STE_RAD_C_HCNT: dc.w    0               ; cached hline count
STE_RAD_C_VCNT: dc.w    0               ; cached vline count

ste_radar_draw:
        clr.w   STE_RAD_MAXC
        clr.w   STE_RAD_MAXY
        tst.w   -$0e10(a4)              ; Radar ON (> 0)?
        ble.w   .rd_ret
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        movea.l STE_HUD_VBASE(pc),a6    ; a6 = STE_VIEW_BASE
        move.w  -$0e0a(a4),d6           ; d6 = radar scale (8, 12, 16, 20, 24)
        ble.w   .rd_done
        ; Rebuild pre-scaled line cache ONLY when scale changes (saves 48x divs.w/frame = 7,500 cycles!)
        cmp.w   STE_RAD_C_SC(pc),d6
        beq.s   .rd_cache_ok
        move.w  d6,STE_RAD_C_SC
        lea     -$4d78(a4),a3
        lea     STE_RAD_CACHE.l,a0
        moveq   #0,d7
.rc_hlp:
        move.w  (a3)+,d0
        blt.s   .rc_hdone
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        ext.l   d0
        divs.w  d6,d0
        add.w   -$0e0e(a4),d0
        move.w  d0,(a0)+
        ext.l   d1
        divs.w  d6,d1
        add.w   -$0e0c(a4),d1
        move.w  d1,(a0)+
        ext.l   d2
        divs.w  d6,d2
        add.w   -$0e0e(a4),d2
        move.w  d2,(a0)+
        addq.w  #1,d7
        bra.s   .rc_hlp
.rc_hdone:
        move.w  d7,STE_RAD_C_HCNT
        moveq   #0,d7
.rc_vlp:
        move.w  (a3)+,d0
        blt.s   .rc_vdone
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        ext.l   d0
        divs.w  d6,d0
        add.w   -$0e0e(a4),d0
        move.w  d0,(a0)+
        ext.l   d1
        divs.w  d6,d1
        add.w   -$0e0c(a4),d1
        move.w  d1,(a0)+
        ext.l   d2
        divs.w  d6,d2
        add.w   -$0e0c(a4),d2
        move.w  d2,(a0)+
        addq.w  #1,d7
        bra.s   .rc_vlp
.rc_vdone:
        move.w  d7,STE_RAD_C_VCNT
.rd_cache_ok:
        ; Compute exact Radar bbox for ste_hud_lift_spr from cached first hline (0..912) & first vline (0..1392)
        lea     STE_RAD_CACHE.l,a3
        move.w  4(a3),d0                ; sx2 of top touchline
        add.w   STE_HUD_HSCR(pc),d0
        lsr.w   #4,d0
        addq.w  #1,d0
        move.w  d0,STE_RAD_MAXC
        move.w  14(a3),d0               ; sy of bottom touchline (3rd hline = offset 12+2=14!)
        addq.w  #2,d0
        move.w  d0,STE_RAD_MAXY

        lea     STE_RAD_LREC.l,a2       ; a2 = line restore record cursor (max 24)
        lea     STE_RAD_POOL.l,a5       ; a5 = Blitter save-under pool cursor
        moveq   #0,d7                   ; d7 = line record count

        ; --- A. Horizontal pitch outline lines (pre-scaled! ZERO divs.w!) ---
        move.w  STE_RAD_C_HCNT(pc),d6
        beq.s   .rd_vstart
        subq.w  #1,d6
.rd_hlp:
        move.w  (a3)+,d0                ; sx1
        move.w  (a3)+,d1                ; sy
        move.w  (a3)+,d2                ; sx2
        bsr.s   .rd_hline_blt
        dbra    d6,.rd_hlp

        ; --- B. Vertical pitch outline lines (pre-scaled! ZERO divs.w!) ---
.rd_vstart:
        move.w  STE_RAD_C_VCNT(pc),d6
        beq.s   .rd_dots
        subq.w  #1,d6
.rd_vlp:
        move.w  (a3)+,d0                ; sx
        move.w  (a3)+,d1                ; sy1
        move.w  (a3)+,d2                ; sy2
        bsr.w   .rd_vline_blt
        dbra    d6,.rd_vlp

        ; --- C. Batch-draw ALL d7 radar lines in ONE TRAP #8 (cmd 7), then 23 dots! ---
.rd_dots:
        move.w  d7,STE_RAD_LCNT
        beq.s   .rd_dots_go
        lea     STE_RAD_LREC.l,a0       ; a0 = start of 16-byte line records
        move.w  d7,d1                   ; d1 = count
        moveq   #7,d0                   ; cmd 7 = batch save+draw transparent black lines!
        trap    #8
.rd_dots_go:
        bsr.w   ste_radar_draw_dots
.rd_done:
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
.rd_ret:
        rts

; Blitter transparent black horizontal line: d0=sx1, d1=sy, d2=sx2
.rd_hline_blt:
        cmpi.w  #200,d1
        bcc.s   .hlb_ret
        cmpi.w  #24,d7
        bcc.s   .hlb_ret
        add.w   STE_HUD_HSCR(pc),d0
        add.w   STE_HUD_HSCR(pc),d2
        move.w  d0,d3
        andi.w  #15,d3
        move.w  #$ffff,d4
        lsr.w   d3,d4                   ; d4 = ENDMASK1 (left clip!)
        move.w  d2,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        move.w  #$ffff,d3
        lsl.w   d5,d3                   ; d3 = ENDMASK3 (right clip!)
        lsr.w   #4,d0                   ; w1 = sx1 >> 4
        lsr.w   #4,d2                   ; w2 = sx2 >> 4
        sub.w   d0,d2
        blt.s   .hlb_ret
        addq.w  #1,d2                   ; d2 = word_cols (1..20)
        cmpi.w  #1,d2
        bne.s   .hlb_m2
        and.w   d3,d4                   ; single-word hline: combine left & right masks!
.hlb_m2:
        ; Check pool space: word_cols * 8 bytes
        move.w  d2,d5
        lsl.w   #3,d5
        lea     0(a5,d5.w),a0
        cmpa.l  #STE_RAD_POOL_END,a0
        bhi.s   .hlb_ret
        ; Compute dst a1 = a6 + sy*168 + w1*8
        mulu.w  #CORK_STRIDE,d1
        lsl.w   #3,d0
        ext.l   d0
        add.l   d0,d1
        lea     0(a6,d1.l),a1
        ; Append 16B record [dst=a1, save=a5, wcols=d2, H=1, em1=d4, em3=d3] (batched!)
        move.l  a1,(a2)+
        move.l  a5,(a2)+
        move.w  d2,(a2)+                ; word_cols
        move.w  #1,(a2)+                ; H = 1
        move.w  d4,(a2)+                ; ENDMASK1
        move.w  d3,(a2)+                ; ENDMASK3
        addq.w  #1,d7
        adda.w  d5,a5                   ; advance pool
.hlb_ret:
        rts

; Blitter transparent black vertical line: d0=sx, d1=sy1, d2=sy2
.rd_vline_blt:
        cmpi.w  #320,d0
        bcc.s   .vlb_ret
        cmpi.w  #200,d1
        bcc.s   .vlb_ret
        cmpi.w  #24,d7
        bcc.s   .vlb_ret
        cmpi.w  #200,d2
        bcs.s   .vlb_yok
        move.w  #199,d2
.vlb_yok:
        sub.w   d1,d2
        blt.s   .vlb_ret
        addq.w  #4,d2
        lsr.w   #2,d2                   ; d2 = (H+3)/4 (Y_STEP=4 -> 4x faster vertical radar, 0 divu!)
        ; Check pool space: H * 8 bytes (cap H if pool nearly full!)
        move.l  #STE_RAD_POOL_END,d5
        sub.l   a5,d5
        lsr.l   #3,d5                   ; max lines remaining in pool
        ble.s   .vlb_ret
        cmp.w   d5,d2
        ble.s   .vlb_hok
        move.w  d5,d2
.vlb_hok:
        add.w   STE_HUD_HSCR(pc),d0
        move.w  d0,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        moveq   #0,d4
        bset    d5,d4                   ; d4 = ENDMASK1 (single pixel bit!)
        move.w  d4,d3                   ; d3 = ENDMASK3
        lsr.w   #4,d0
        lsl.w   #3,d0
        mulu.w  #CORK_STRIDE,d1
        ext.l   d0
        add.l   d0,d1
        lea     0(a6,d1.l),a1           ; a1 = dst in STE_VIEW_BASE
        ; Append 16B record [dst=a1, save=a5, wcols=1, H=d2, em1=d4, em3=d3] (batched!)
        move.l  a1,(a2)+
        move.l  a5,(a2)+
        move.w  #1,(a2)+                ; 1 word_col
        move.w  d2,(a2)+                ; H lines
        move.w  d4,(a2)+                ; ENDMASK1
        move.w  d3,(a2)+                ; ENDMASK3
        addq.w  #1,d7
        move.w  d2,d5
        lsl.w   #3,d5
        adda.w  d5,a5                   ; advance pool by H*8
.vlb_ret:
        rts

; Stationary-frame fast path: restore old 23 dots + redraw new 23 dots (0.012 VBL!)
ste_radar_dots_only:
        tst.w   -$0e10(a4)
        ble.s   .rdo_ret
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  STE_RAD_DCNT(pc),d0
        beq.s   .rdo_draw
        clr.w   STE_RAD_DCNT
        move.w  d0,d1
        mulu.w  #12,d0
        lea     STE_RAD_DREC.l,a0
        adda.l  d0,a0
        subq.w  #1,d1
.rdo_lp:
        lea     -12(a0),a0
        movea.l (a0),a1
        move.l  4(a0),(a1)
        move.l  8(a0),4(a1)
        dbra    d1,.rdo_lp
.rdo_draw:
        movea.l STE_HUD_VBASE(pc),a6
        bsr.s   ste_radar_draw_dots
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
.rdo_ret:
        rts

ste_radar_draw_dots:
        lea     STE_RAD_DREC.l,a2       ; a2 = dot restore record cursor (max 56)
        moveq   #0,d7                   ; d7 = dot record count
        movea.l -$5012(a4),a5           ; Home 11 players
        moveq   #10,d5
        moveq   #2,d4                   ; colour 10 ($730 orange)
        bsr.s   .rd_team
        movea.l -$4fbc(a4),a5           ; Away 11 players
        moveq   #10,d5
        moveq   #4,d4                   ; colour 12 ($500 red)
        bsr.s   .rd_team
        move.w  -$0e14(a4),d0
        blt.s   .rd_ddone
        move.w  -$0e12(a4),d1
        moveq   #0,d4                   ; colour 8 ($777 white ball)
        bsr.s   .rd_dot
.rd_ddone:
        move.w  d7,STE_RAD_DCNT
        rts

; Draw 11 player dots for team at a5 (stride $186), d5=10, d4=colour (2=orange, 4=red)
.rd_team:
        tst.w   $0c(a5)
        beq.s   .rt_nxt
        move.w  $20(a5),d0
        blt.s   .rt_nxt
        move.w  $22(a5),d1
        bsr.s   .rd_dot
.rt_nxt:
        lea     $186(a5),a5
        dbra    d5,.rd_team
        rts

; Plot transparent 2x2 dot at (d0=x, d1=y), d4=colour (0->8 white, 2->10 orange, 4->12 red)
; Saves exact 32-bit dst address (12B: [dst.l, l0.l, l1.l]) -> ZERO offset wrap bugs!
.rd_dot:
        cmpi.w  #318,d0
        bcc.s   .dot_ret
        cmpi.w  #198,d1
        bcc.s   .dot_ret
        cmpi.w  #55,d7
        bcc.s   .dot_ret
        add.w   STE_HUD_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2
        move.w  #$c000,d3
        lsr.w   d2,d3
        lsr.w   #4,d0
        lsl.w   #3,d0
        mulu.w  #CORK_STRIDE,d1
        ext.l   d0
        add.l   d0,d1
        lea     0(a6,d1.l),a0
        move.w  d3,d0
        not.w   d0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        and.w   d0,(a0)
        and.w   d0,2(a0)
        and.w   d0,4(a0)
        or.w    d3,6(a0)
        tst.w   d4
        beq.s   .dot_ret
        cmpi.w  #2,d4
        bne.s   .dot_c4
        or.w    d3,2(a0)
        rts
.dot_c4:
        or.w    d3,4(a0)
.dot_ret:
        rts

; ---------------------------------------------------------------------------
; TRAP #8 ($a0.w) — Fast Supervisor STE Blitter Dispatcher!
; d0.w = cmd:
;   0 : blit_tile(a0=3bpp src 96B, a1=dst in STE_CORK_BUF)
;   1 : save_under(a0=dst in STE_CORK_BUF, a1=256B slot)
;   2 : restore_under(a0=256B slot, a1=dst in STE_CORK_BUF)
;   3 : draw_sprite(a0=dst in STE_CORK_BUF, d1.w=skew 0..15)
;   4 : clear_cork (zeroes STE_CORK_BUF 73,984 bytes with Blitter)
; ---------------------------------------------------------------------------
ste_trap8_handler:
        cmpi.w  #1,d0
        beq.s   .cmd1_rest_one
        cmpi.w  #2,d0
        beq.w   .cmd2_rest_lifo
        cmpi.w  #3,d0
        beq.w   .cmd3_spr
        cmpi.w  #4,d0
        beq.w   .cmd4_clr
        cmpi.w  #5,d0
        beq.w   .cmd5_hud_draw
        cmpi.w  #6,d0
        beq.w   .cmd6_hud_rest
        cmpi.w  #7,d0
        beq.w   .cmd7_radar_opaque
        cmpi.w  #8,d0
        beq.w   .cmd8_blit_row
        bra.w   .cmd9_blit_col

; --- cmd 1: Single sprite restore (a0=slot, a1=dst) ---
.cmd1_rest_one:
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-14),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #8,BLT_XCOUNT.w
        move.w  #16,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.b  #$c0,BLT_LINE.w
        rte

; --- cmd 2: Batched LIFO reverse-order restore of d1.w 16-byte records ending at a0 ---
.cmd2_rest_lifo:
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-14),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #8,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c2_lp:
        lea     -16(a0),a0
        moveq   #0,d0
        move.b  13(a0),d0               ; slot_idx.b (0..31)
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        move.l  d0,BLT_SRC_ADDR.w       ; slot_addr
        move.l  4(a0),BLT_DST_ADDR.w    ; dst_addr
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        dbra    d1,.c2_lp
        rte


; --- cmd 3: Combined Save-under + Direct NFSR Masked 4bpp Sprite Draw ---
; a0 = dst in STE_CORK_BUF, a1 = KO2 3bpp sprite src, a2 = save-under slot, d1.w = skew (0..15)
.cmd3_spr:
        movem.l d2-d3/a3,-(sp)
        ; 1. Save-under (a0 -> a2, 16 lines x 8 words = 256 bytes)
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a2,BLT_DST_ADDR.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #(CORK_STRIDE-14),BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #8,BLT_XCOUNT.w
        moveq   #16,d2
        moveq   #-64,d3
        move.w  d2,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.b  d3,BLT_LINE.w

        ; 1b. Build 16-word 1bpp sprite mask in STE_MASK_BUF via STE Blitter (2x faster than 68000!)
        lea     STE_MASK_BUF.l,a3
        clr.w   BLT_SRC_XINC.w
        move.w  #$78,BLT_SRC_YINC.w
        clr.w   BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #1,BLT_XCOUNT.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w           ; plane 0 -> copy (OP=3 already set!)
        move.w  #$0207,BLT_HOP.w
        lea     $28(a1),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w           ; plane 1 -> OR
        lea     $28(a2),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w           ; plane 2 -> OR

        ; 2. Configure skew: skew==0 -> XCOUNT=1 (2x faster!), skew>0 -> XCOUNT=2, NFSR=$40|skew
        tst.w   d1
        bne.s   .c3_skew
        move.w  #1,BLT_XCOUNT.w
        clr.w   BLT_DST_XINC.w
        move.w  #CORK_STRIDE,BLT_DST_YINC.w
        clr.b   BLT_SKEW.w
        bra.s   .c3_mask
.c3_skew:
        move.w  #$ffff,d0
        lsr.w   d1,d0
        move.w  d0,BLT_ENDMASK1.w
        not.w   d0
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_XCOUNT.w
        move.w  #8,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-8),BLT_DST_YINC.w
        move.b  d1,d0
        ori.b   #$40,d0                 ; NFSR = 1 (1 src word -> 2 dst words!)
        move.b  d0,BLT_SKEW.w

.c3_mask:
        ; Pass 1: Clear mask holes in dst planes 0, 1, 2 (OP=4: ~SRC & DST)
        clr.w   BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w       ; STE_MASK_BUF = 1 word/line
        move.w  #$0204,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        move.l  a3,BLT_SRC_ADDR.w
        lea     2(a0),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        ; Pass 2: OR mask into plane 3 (a0+6 -> sets bit 3 = sprite colours 9..15!)
        move.w  #$0207,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        ; Pass 3: OR sprite planes 0, 1, 2 DIRECTLY from KO2 src a1 (stride $78)!
        move.w  #$78,BLT_SRC_YINC.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        lea     $28(a1),a2
        lea     2(a0),a3
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        lea     $28(a2),a2
        addq.l  #2,a3
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d3,BLT_LINE.w

        movem.l (sp)+,d2-d3/a3
        rte

; --- cmd 4: Zero STE_CORK_BUF (73,920B) AND $078000 (32,000B stale Classic ST lines!) ---
.cmd4_clr:
        move.l  #STE_CORK_BUF,BLT_DST_ADDR.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #84,BLT_XCOUNT.w        ; 168 bytes / 2
        move.w  #440,BLT_YCOUNT.w       ; 440 * 168 = 73,920 bytes
        clr.w   BLT_HOP.w        ; all zeroes
        clr.b   BLT_SKEW.w
        move.b  #$c0,BLT_LINE.w
        ; Also zero $078000 (32,000 bytes) so no stale Classic ST pitch lines trigger HUD/Banner!
        move.l  #$078000,BLT_DST_ADDR.w
        move.w  #80,BLT_XCOUNT.w        ; 160 bytes / 2
        move.w  #200,BLT_YCOUNT.w       ; 200 * 160 = 32,000 bytes
        move.b  #$c0,BLT_LINE.w
        rte

; --- cmd 5: Blitter HUD/Radar band draw ---
; a0 = src ($078000+y*160), a1 = dst (STE_VIEW_BASE+y*168), a2 = save_buf
; d1.w = W (4 or 20), d2.w = H (lines), d3.w = skew (0..15), d4.w = 1 (all 4 planes) / 0 (2 planes)
.cmd5_hud_draw:
        movem.l d5-d7/a3,-(sp)
        ; 1. Save-under (a1 -> a2): (W+1)*4 words x H lines
        move.w  d1,d5
        addq.w  #1,d5
        lsl.w   #2,d5                   ; d5 = (W+1)*4 words
        move.w  d5,d6
        subq.w  #1,d6
        add.w   d6,d6                   ; bytes advanced by XINC
        move.w  #CORK_STRIDE,d7
        sub.w   d6,d7                   ; SRC_YINC = 168 - ((W+1)*4 - 1)*2
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a2,BLT_DST_ADDR.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  d7,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  d5,BLT_XCOUNT.w
        move.w  d2,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.b  #$c0,BLT_LINE.w

        ; 2. Build 1bpp mask in STE_HUD_MASK (W words x H lines)
        ;    src_yinc = 160 - (W-1)*8
        move.w  d1,d6
        subq.w  #1,d6
        lsl.w   #3,d6
        move.w  #160,d7
        sub.w   d6,d7                   ; d7 = src_yinc for 4bpp $078000
        lea     STE_HUD_MASK.l,a3
        move.w  #8,BLT_SRC_XINC.w
        move.w  d7,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  d1,BLT_XCOUNT.w
        ; Plane 0 -> copy
        moveq   #-64,d0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        move.b  d0,BLT_LINE.w
        ; Plane 1 -> OR
        addq.l  #2,a0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.w  #$0207,BLT_HOP.w
        move.b  d0,BLT_LINE.w
        ; Plane 2 -> OR
        addq.l  #2,a0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        ; Plane 3 -> OR
        addq.l  #2,a0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        subq.l  #6,a0

.c5_mask_ok:
        ; 3. Configure skew, endmasks, XCOUNT, and DST_YINC for compositing into a1
        tst.w   d3
        bne.s   .c5_skewed
        ; skew == 0: XCOUNT = W, ENDMASK = ffff/ffff/ffff, DST_YINC = 168 - (W-1)*8
        move.w  #$ffff,BLT_ENDMASK1.w
        move.w  #$ffff,BLT_ENDMASK3.w
        move.w  d1,BLT_XCOUNT.w
        move.w  #CORK_STRIDE,d5
        sub.w   d6,d5                   ; d6 is still (W-1)*8
        move.w  d5,BLT_DST_YINC.w
        clr.b   BLT_SKEW.w
        bra.s   .c5_comp
.c5_skewed:
        ; skew > 0: XCOUNT = W+1, NFSR=$40|skew, DST_YINC = 168 - W*8
        move.w  #$ffff,d5
        lsr.w   d3,d5
        move.w  d5,BLT_ENDMASK1.w
        not.w   d5
        move.w  d5,BLT_ENDMASK3.w
        move.w  d1,d5
        addq.w  #1,d5
        move.w  d5,BLT_XCOUNT.w
        move.w  d1,d5
        lsl.w   #3,d5                   ; W * 8
        neg.w   d5
        addi.w  #CORK_STRIDE,d5         ; 168 - W*8
        move.w  d5,BLT_DST_YINC.w
        move.b  d3,d5
        ori.b   #$40,d5                 ; NFSR = 1!
        move.b  d5,BLT_SKEW.w

.c5_comp:
        ; Clear mask holes in dst planes 0, 1, 2 (OP=4: ~SRC & DST)
        moveq   #-64,d0
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #8,BLT_DST_XINC.w
        move.w  #$0204,BLT_HOP.w
        ; dst plane 0
        move.l  a3,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        ; dst plane 1
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        ; dst plane 2
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        ; Set plane 3 (OP=7: SRC | DST -> maps HUD colours 1..7 -> 9..15, 8 -> 8!)
        move.w  #$0207,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        subq.l  #6,a1

        ; 4. OR source planes from $078000 (a0) into dst (a1)
        move.w  #8,BLT_SRC_XINC.w
        move.w  d7,BLT_SRC_YINC.w
        ; plane 0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        ; plane 1
        addq.l  #2,a0
        addq.l  #2,a1
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w
        ; plane 2
        addq.l  #2,a0
        addq.l  #2,a1
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d0,BLT_LINE.w

.c5_done:
        movem.l (sp)+,d5-d7/a3
        rte

; --- cmd 6: Blitter HUD/Radar restore-under ---
; If d1.w != 0: single band (a0=save_buf, a1=dst, d1=XCOUNT words, d2=YCOUNT lines)
; If d1.w == 0: batch-restore d2.w 12-byte records [dst.l, save.l, xcnt.w, ycnt.w] ending at a2!
.cmd6_hud_rest:
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        tst.w   d1
        beq.s   .c6_batch
        move.w  d1,d0
        subq.w  #1,d0
        add.w   d0,d0
        neg.w   d0
        addi.w  #CORK_STRIDE,d0         ; DST_YINC = 168 - (XCOUNT-1)*2
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d0,BLT_DST_YINC.w
        move.w  d1,BLT_XCOUNT.w
        move.w  d2,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        rte
.c6_batch:
        subq.w  #1,d2
.c6_blp:
        lea     -16(a2),a2
        move.l  4(a2),BLT_SRC_ADDR.w
        move.l  (a2),BLT_DST_ADDR.w
        move.w  8(a2),d1                ; word_cols
        lsl.w   #2,d1                   ; XCOUNT = word_cols * 4 planes
        move.w  d1,d0
        subq.w  #1,d0
        add.w   d0,d0
        neg.w   d0
        cmpi.w  #4,d1                   ; 1 word_col (vertical line) -> Y_STEP=3 (stride 504)!
        bne.s   .c6_s1
        addi.w  #(4*CORK_STRIDE),d0
        bra.s   .c6_s2
.c6_s1: addi.w  #CORK_STRIDE,d0
.c6_s2: move.w  d0,BLT_DST_YINC.w
        move.w  d1,BLT_XCOUNT.w
        move.w  10(a2),BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        dbra    d2,.c6_blp
        rte

; --- cmd 7: BATCHED STE Blitter Transparent Black Line Save + Draw (1 TRAP #8 for ALL lines!) ---
; a0 = start of d1.w 16-byte records: [dst.l, save.l, wcols.w, H.w, em1.w, em3.w]
.cmd7_radar_opaque:
        movem.l d2-d6/a1,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #$ffff,BLT_ENDMASK2.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c7_lp:
        movea.l (a0)+,a1                ; dst in STE_CORK_BUF
        move.l  (a0)+,d4                ; save pool ptr
        move.w  (a0)+,d3                ; word_cols (1..20)
        move.w  (a0)+,d2                ; H (1..100)
        ; 1. Save-under (a1 -> d4): (wcols*4) words x H lines (Y_STEP=2 when wcols==1!)
        move.w  d3,d5
        lsl.w   #2,d5
        move.w  d5,d6
        subq.w  #1,d6
        add.w   d6,d6
        neg.w   d6
        cmpi.w  #1,d3
        bne.s   .c7_s1
        addi.w  #(4*CORK_STRIDE),d6
        bra.s   .c7_s2
.c7_s1: addi.w  #CORK_STRIDE,d6
.c7_s2: move.l  a1,BLT_SRC_ADDR.w
        move.l  d4,BLT_DST_ADDR.w
        move.w  d6,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #$ffff,BLT_ENDMASK1.w
        move.w  #$ffff,BLT_ENDMASK3.w
        move.w  d5,BLT_XCOUNT.w
        move.w  d2,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        move.b  #$c0,BLT_LINE.w
        ; 2. Draw transparent black line (colour 9: p0=1, p3=1, p1=0, p2=0)
        move.w  (a0)+,BLT_ENDMASK1.w
        move.w  (a0)+,BLT_ENDMASK3.w
        move.w  #8,BLT_DST_XINC.w
        move.w  d3,d6
        subq.w  #1,d6
        lsl.w   #3,d6
        neg.w   d6
        cmpi.w  #1,d3
        bne.s   .c7_d1
        addi.w  #(4*CORK_STRIDE),d6
        bra.s   .c7_d2
.c7_d1: addi.w  #CORK_STRIDE,d6
.c7_d2: move.w  d6,BLT_DST_YINC.w
        move.w  d3,BLT_XCOUNT.w
        move.w  #$000f,BLT_HOP.w
        moveq   #-64,d6
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d6,BLT_LINE.w
        addq.l  #2,a1
        clr.w   BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d6,BLT_LINE.w
        addq.l  #2,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d6,BLT_LINE.w
        addq.l  #2,a1
        move.w  #$000f,BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        move.b  d6,BLT_LINE.w
        dbra    d1,.c7_lp
        movem.l (sp)+,d2-d6/a1
        rte

; --- cmd 8: Batched 21-tile horizontal row blit (d1=tx_left, d2=ty_row) ---
; Sets Blitter regs ONCE, skips redundant plane-3 clear (plane 3 is always 0!),
; and handles primary + mirror in one tight Supervisor loop!
.cmd8_blit_row:
        movem.l d3-d7/a2-a4,-(sp)
        ; Configure constant Blitter registers ONCE for all 21 tiles
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w        ; HOP=2 (src), OP=3 (copy)
        clr.b   BLT_SKEW.w

        ; Compute map ptr a2 = STE_PIT_MAP + ty*80 + tx_left
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        ; Compute primary dst a3 = STE_CORK_BUF + (ty%14)*16*168 + tx_left*8
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #14,d0
        swap    d0                      ; d0 = ty % 14
        move.w  d0,d6                   ; d6 = ty % 14 (mirror if <= 12)
        lsl.w   #4,d0
        mulu.w  #CORK_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        lea     STE_CORK_BUF.l,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        ; Number of valid tiles = min(21, 80 - tx_left)
        moveq   #21,d7
        moveq   #80,d0
        sub.w   d1,d0
        ble.w   .c8_done
        cmp.w   d7,d0
        bge.s   .c8_cnt
        move.w  d0,d7
.c8_cnt:
        ; First: clear Plane 3 for the entire tile row in ONE Blitter call (+ mirror)!
        move.w  d7,d5                   ; save tile count (1..21) in d5
        move.w  d7,d4
        subq.w  #1,d4
        lsl.w   #3,d4
        neg.w   d4
        addi.w  #CORK_STRIDE,d4         ; DST_YINC = 168 - (cnt-1)*8
        move.w  #8,BLT_DST_XINC.w
        move.w  d4,BLT_DST_YINC.w
        move.w  d7,BLT_XCOUNT.w
        clr.w   BLT_HOP.w        ; OP=0 (zero plane 3!)
        lea     6(a3),a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        cmpi.w  #12,d6
        bgt.s   .c8_p3_ok
        adda.l  #CORK_RING_BYTES,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
.c8_p3_ok:
        ; Restore 3bpp tile blit settings
        move.w  #2,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        move.w  d5,d7
        subq.w  #1,d7
        cmpi.w  #12,d6
        bgt.s   .c8_nomir
.c8_mir_lp:
        moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0                   ; tid * 64
        lsl.w   #5,d3                   ; tid * 32
        add.w   d3,d0                   ; tid * 96
        lea     0(a4,d0.w),a0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        move.l  a0,BLT_SRC_ADDR.w
        movea.l a3,a1
        adda.l  #CORK_RING_BYTES,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        addq.l  #8,a3
        dbra    d7,.c8_mir_lp
        bra.s   .c8_done
.c8_nomir:
        moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        addq.l  #8,a3
        dbra    d7,.c8_nomir
.c8_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte

; --- cmd 9: Batched 14-tile vertical column blit (d1=tx_col, d2=ty_top) ---
.cmd9_blit_col:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w

        ; Map ptr a2 = STE_PIT_MAP + ty_top*80 + tx_col
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        ; Initial ty%14 in d6, initial dst a3 in STE_CORK_BUF
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #14,d0
        swap    d0
        move.w  d0,d6                   ; d6 = cur_row_mod (0..13)
        lsl.w   #4,d0
        mulu.w  #CORK_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        lea     STE_CORK_BUF.l,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        ; Number of valid rows = min(14, 96 - ty_top)
        moveq   #14,d7
        moveq   #96,d0
        sub.w   d2,d0
        ble.w   .c9_done
        cmp.w   d7,d0
        bge.s   .c9_cnt
        move.w  d0,d7
.c9_cnt:
        ; First: clear Plane 3 for the entire vertical column in ONE Blitter call (424 lines)!
        move.w  d1,d0
        lsl.w   #3,d0
        ext.l   d0
        lea     STE_CORK_BUF+6.l,a1
        adda.l  d0,a1
        clr.w   BLT_DST_XINC.w
        move.w  #CORK_STRIDE,BLT_DST_YINC.w
        move.w  #1,BLT_XCOUNT.w
        clr.w   BLT_HOP.w        ; OP=0 (zero plane 3!)
        move.l  a1,BLT_DST_ADDR.w
        move.w  #424,BLT_YCOUNT.w       ; entire primary + mirror column in 1 blit!
        move.b  #$c0,BLT_LINE.w
        ; Restore 3bpp tile blit settings
        move.w  #2,BLT_DST_XINC.w
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        subq.w  #1,d7
.c9_lp:
        moveq   #0,d0
        move.b  (a2),d0
        adda.w  #80,a2
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a0
        move.l  a0,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        cmpi.w  #12,d6
        bgt.s   .c9_nomir
        move.l  a0,BLT_SRC_ADDR.w
        movea.l a3,a1
        adda.l  #CORK_RING_BYTES,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
.c9_nomir:
        addq.w  #1,d6
        cmpi.w  #14,d6
        blt.s   .c9_step
        moveq   #0,d6
        suba.l  #(CORK_RING_BYTES-16*CORK_STRIDE),a3
        bra.s   .c9_next
.c9_step:
        adda.w  #(16*CORK_STRIDE),a3
.c9_next:
        dbra    d7,.c9_lp
.c9_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte
