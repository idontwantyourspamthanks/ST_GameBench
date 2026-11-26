; ---------------------------------------------------------------------------
; Player Manager v1.1 — Atari STE True Double-Buffered Amiga Engine (KO2STE.BIN)
;
; Loaded at $0ae940..$0b02ff (max 6,592 bytes) ONLY on Atari STE / Mega STE
; (when BR_IS_STE == 1). Plain 68000 ST never loads/calls this and keeps
; 100% classic v1.0 ST mode automatically.
;
; True Double-Buffered 1 MB STE RAM Layout during live match:
;   $078000..$079fff : Buffer B sprite save-under (32 x 256B = 8 KB; KO2 radar $01fae8/$01fbb4 stubbed!)
;   $07f1c0..$07fcff : KO2 Bottom HUD (untouched; 0-cycle HBlank-locked split screen!)
;   $07fd00..$0804ff : Buffer A radar line save pool (2 KB, outside $078000..$07fcff!)
;   $080500..$080cff : Buffer B radar line save pool (2 KB, outside $078000..$07fcff!)
;   $080d00..$080fff : Zeroed black line buffer for bottom border (lines 197..199)
;   $081000..$088e1f : Active Amiga pitch (AMIGAP0..3.BIN: pal + 80x96 map + 256 tiles)
;   $088f00..$0919ff : Ring Buffer A (208 lines x 168B + 640B slack = 35,584B)
;   $091a00..$09a4ff : Ring Buffer B (208 lines x 168B + 640B slack = 35,584B)
;   $09a500..$09af5f : Double-buffer stacks, radar records, mask & active sprite list
;   $09b000..$09cfff : Buffer A sprite save-under (32 x 256B = 8 KB)
;   $0b2880..$0b2cff : Double-buffer radar dot restore records (below PMOK @ $0b2ff8)
;
; Entry points (fixed header at $0ae940):
;   +$00 : bra.w ste_install_hooks  (after KO2ENG.BIN loads, before $01fd92)
;   +$04 : bra.w ste_cleanup        (in Supervisor SR=$2700 on KO2 exit)
;   +$08 : STE_SND_SIZE.l           (filled by ko2_bridge.s with AMIGASND.BIN size)
;   +$0c : bra.w ste_load_pitch     (after $013450, loads AMIGAP0..3.BIN -> $081000)
; ---------------------------------------------------------------------------

        org     $0ae940

KO2_A4          equ     $0284aa
STE_SND_STG     equ     $0c8b00         ; AMIGASND.BIN staging in KO2_REPLAY_BUF

; Amiga pitch data ($081000..$088e1f)
STE_PIT_PAL     equ     $081000         ; 32 bytes (8 STE 12-bit pitch colours)
STE_PIT_MAP     equ     $081020         ; 7,680 bytes (80 x 96 tilemap)
STE_PIT_TILES   equ     $082e20         ; 24,576 bytes (256 x 96 bytes 3bpp tiles)

; Double-buffered 208-line x 168B Ring Buffers (13 tile rows x 21 tiles, unmirrored!)
; ALL metadata (stacks, records, sprite list) lives OUTSIDE $078000..$07fcff so KO2's
; center banners ("KICK OFF" / "GOAL") at $07bc00..$07c800 can NEVER corrupt pointers!
STE_RING_A      equ     $088ee0         ; $088ee0..$0919ef (209*168 + 488B slack = 35,600B)
STE_RING_B      equ     $0919f0         ; $0919f0..$09a4ff (209*168 + 488B slack = 35,600B)
STE_SAV_A       equ     $09b000         ; $09b000..$09cfff (32 x 256B = 8 KB)
STE_SAV_B       equ     $078000         ; $078000..$079fff (8 KB: y=0..51, KO2 radar $01fae8/$01fbb4 stubbed!)
STE_RPOOL_A     equ     $07fd00         ; $07fd00..$0804ff (2 KB, cleanly above $07fcff screen!)
STE_RPOOL_B     equ     $080500         ; $080500..$080cff (2 KB, cleanly above $07fcff screen!)
STE_BLACK_LINE  equ     $080d00         ; $080d00..$080fff (768B zeroes -> lines 197..199!)

; Double-buffer metadata in 100% KO2-untouched RAM ($09a500..$09af60 & $0b2880..$0b2d00!)
STE_STK_A       equ     $09a500         ; 32 x 16B = 512B -> $09a700
STE_STK_B       equ     $09a700         ; 32 x 16B = 512B -> $09a900
STE_RLR_A       equ     $09a900         ; 28 x 16B = 448B -> $09aac0
STE_RLR_B       equ     $09aac0         ; 28 x 16B = 448B -> $09ac80
STE_SPR_LIST    equ     $09ac80         ; 32 x 16B = 512B -> $09ae80
STE_RAD_CACHE   equ     $09ae80         ; 24 x 8B  = 192B -> $09af40
STE_MASK_BUF    equ     $09af40         ; 32B             -> $09af60 (< $09b000!)
STE_RDR_A       equ     $0b2880         ; 48 x 12B = 576B -> $0b2ac0
STE_RDR_B       equ     $0b2ac0         ; 48 x 12B = 576B -> $0b2d00 (< PMOK $0b2ff8!)

RING_STRIDE     equ     168             ; 336 pixels = 21 x 16px words (4bpp)
RING_H          equ     208             ; 13 tile rows = 208 scanlines (covers 181px @ any wy%16!)
RING_ROWS       equ     13              ; 208 / 16
RING_BYTES      equ     34944           ; 208 * 168
PITCH_VIS_H     equ     181             ; scanlines 0..180 pitch, 181..196 bottom HUD

; Buffer descriptor offsets (48 bytes per buffer: DB_A at 0, DB_B at 48)
DB_RING         equ     0               ; .l ring base ($088f00 / $091a00)
DB_SAV          equ     4               ; .l save-under base ($09b000 / $078000)
DB_STK          equ     8               ; .l sprite restore stack base
DB_RPOOL        equ     12              ; .l radar line save pool base (4 KB)
DB_RLR          equ     16              ; .l radar line record base (28 x 16B)
DB_RDR          equ     20              ; .l radar dot record base (48 x 12B)
DB_TX           equ     24              ; .w last tile X drawn into this ring
DB_TY           equ     26              ; .w last tile Y drawn into this ring
DB_SCNT         equ     28              ; .w sprites drawn onto this ring (0..32)
DB_RLCNT        equ     30              ; .w radar lines drawn onto this ring (0..28)
DB_RDCNT        equ     32              ; .w radar dots drawn onto this ring (0..48)
DB_PAD          equ     34              ; .w
DB_START        equ     36              ; .l display start addr (RING + y0*168 + tx*8)
DB_WRAP         equ     40              ; .l display wrap addr  (RING + tx*8)
DB_WRAPY        equ     44              ; .w wrap scanline (208 - y0, 1..208)
DB_HSCR         equ     46              ; .w fine hscroll (0..15)
DB_SIZE         equ     48

; STE Blitter registers (short I/O addresses $ffff8a20..$ffff8a3d)
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
STE_SCRIPT_ST:  dc.l    0
STE_SCRIPT_PTR: dc.l    0
STE_REPEAT_CNT: dc.w    0
STE_SND_PEND:   dc.b    0
STE_SND_STOP:   dc.b    0
STE_SND_PITCH:  dc.b    0
STE_SND_PAD:    dc.b    0
STE_DMA_CNT:    dc.w    0

; ---------------------------------------------------------------------------
; Double-Buffered Video State
; ---------------------------------------------------------------------------
STE_PITCH_OK:   dc.w    0               ; 1 = AMIGAPx.BIN loaded
STE_SHOW_IDX:   dc.w    0               ; 0 = Buffer A displayed, 1 = Buffer B displayed (ATOMIC!)
STE_STATS_DIRTY: dc.w   0               ; 1 = returning from Half-Time/Stats ($078000 was overwritten)
STE_ORIG_TB:    dc.l    0               ; saved KO2 original Timer B vector ($120.w)
STE_CUR_WX:     dc.w    176             ; current camera world X (pixels) for sprite world coords
STE_CUR_WY:     dc.w    64              ; current camera world Y (pixels)
STE_SPR_CNT:    dc.w    0               ; active sprites in STE_SPR_LIST (0..32)
STE_TB_WRAP_A:  dc.l    STE_RING_A      ; latched wrap address for active frame's Timer B
STE_TB_WRAP_Y:  dc.w    208             ; latched wrap scanline for active frame's Timer B
STE_RAD_C_SC:   dc.w    0               ; cached radar scale
STE_RAD_C_HCNT: dc.w    0
STE_RAD_C_VCNT: dc.w    0
STE_BK_HSCR:    dc.w    0               ; temp backbuffer hscr during draw
STE_BK_Y0:      dc.w    0               ; temp backbuffer y0 (0..207) during draw
STE_BK_TX8:     dc.l    0               ; temp backbuffer tx*8 during draw
STE_BK_REND:    dc.l    0               ; temp backbuffer radar pool end during draw

DB_A:
        dc.l    STE_RING_A, STE_SAV_A, STE_STK_A, STE_RPOOL_A, STE_RLR_A, STE_RDR_A
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    STE_RING_A, STE_RING_A
        dc.w    208, 0
DB_B:
        dc.l    STE_RING_B, STE_SAV_B, STE_STK_B, STE_RPOOL_B, STE_RLR_B, STE_RDR_B
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    STE_RING_B, STE_RING_B
        dc.w    208, 0

; ---------------------------------------------------------------------------
; ste_install_hooks: Patch KO2ENG.BIN at $010000..$024000 for pure STE mode
; ---------------------------------------------------------------------------
ste_install_hooks:
        clr.l   STE_SND_BASE
        clr.l   STE_SCRIPT_ST
        clr.l   STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        clr.w   STE_DMA_CNT
        clr.w   STE_PITCH_OK
        clr.w   STE_SHOW_IDX
        clr.w   STE_STATS_DIRTY
        clr.l   STE_ORIG_TB
        clr.w   STE_SPR_CNT
        clr.w   STE_RAD_C_SC

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

        ; 2. VBL top ($018d06) & bottom ($018e0a)
        move.w  d0,$018d06.l
        move.l  #ste_vbl_top,$018d08.l
        move.w  d0,$018e0a.l
        move.l  #ste_vbl_end,$018e0c.l

        ; 3. Pitch camera & double-buffered frame render ($01c1d0)
        move.w  d0,$01c1d0.l
        move.l  #ste_pitch_update,$01c1d2.l

        ; 4. Sprite draw core ($01a426) & erase ($01a83e) -> ZERO-blit list updates!
        move.w  d0,$01a426.l
        move.l  #ste_draw_spr_core,$01a428.l
        move.w  d0,$01a83e.l
        move.l  #ste_erase_spr,$01a840.l
        ; Bypass KO2's Classic ST Timer B raster-beam waits ($01a376 & $01a3cc) -> ZERO wait!
        move.w  d0,$01a376.l
        move.l  #$01a39c,$01a378.l
        move.w  d0,$01a3cc.l
        move.l  #$01a3f2,$01a3ce.l

        ; 5. Skip KO2's hidden $078000 radar line ($01fae8) & dot ($01fbb4) drawers!
        move.w  #$4e75,$01fae8.l        ; rts!
        move.w  #$4e75,$01fbb4.l        ; rts! (keeps KO2's $20(a5)/$22(a5) coord updates intact!)
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
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        clr.w   STE_PITCH_OK
        clr.l   STE_SCRIPT_PTR
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        rts

; ---------------------------------------------------------------------------
; ste_load_pitch: Called after ko2_bridge.s loads AMIGAPx.BIN -> $081000
; ---------------------------------------------------------------------------
ste_load_pitch:
        cmpi.l  #32288,d0
        bne.s   .lp_fail
        clr.w   STE_SHOW_IDX
        clr.w   STE_SPR_CNT
        clr.w   STE_RAD_C_SC
        clr.w   STE_STATS_DIRTY
        bsr.s   ste_reset_bufs
        moveq   #4,d0                   ; cmd 4 = clear rings & blank line buffer
        trap    #8
        move.w  #1,STE_PITCH_OK
        rts
.lp_fail:
        clr.w   STE_PITCH_OK
        rts

ste_reset_bufs:
        lea     DB_A(pc),a0
        move.w  #-999,DB_TX(a0)
        move.w  #-999,DB_TY(a0)
        clr.w   DB_SCNT(a0)
        clr.w   DB_RLCNT(a0)
        clr.w   DB_RDCNT(a0)
        move.l  #STE_RING_A,DB_START(a0)
        move.l  #STE_RING_A,DB_WRAP(a0)
        move.w  #208,DB_WRAPY(a0)
        clr.w   DB_HSCR(a0)
        lea     DB_B(pc),a0
        move.w  #-999,DB_TX(a0)
        move.w  #-999,DB_TY(a0)
        clr.w   DB_SCNT(a0)
        clr.w   DB_RLCNT(a0)
        clr.w   DB_RDCNT(a0)
        move.l  #STE_RING_B,DB_START(a0)
        move.l  #STE_RING_B,DB_WRAP(a0)
        move.w  #208,DB_WRAPY(a0)
        clr.w   DB_HSCR(a0)
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
; VBL Top ($018d06): Atomic Front-Buffer Display + Exact HBlank-Locked Timer B!
; Writes SHOW_START to BOTH $8201/$03/$0d AND $8205/$07/$09 so screen base and
; $8265 fine hscroll ALWAYS take effect on the EXACT SAME FRAME (ZERO +16px judder!)
; ---------------------------------------------------------------------------
ste_vbl_top:
        movem.l d0-d1/a0-a1,-(sp)
        tst.w   STE_PITCH_OK
        beq.w   .vt_stats
        tst.w   $02356a.l               ; KO2 -$4f40(a4): Half-Time/Full-Time/Stats on $078000?
        bne.w   .vt_stats_mark

        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        bne.s   .vt_tb_ok
        move.l  $0120.w,STE_ORIG_TB
.vt_tb_ok:
        ; Load STE 12-bit Amiga pitch palette (0..7)
        lea     STE_PIT_PAL.l,a0
        lea     $ffff8240.w,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+

        ; Select active Front buffer descriptor (DB_A or DB_B)
        lea     DB_A(pc),a0
        tst.w   STE_SHOW_IDX
        beq.s   .vt_buf
        lea     DB_B(pc),a0
.vt_buf:
        ; Program BOTH Video Base ($8201/$03/$0d) AND live Video Counter ($8205/$07/$09)
        ; -> Takes effect THIS frame alongside $8265/$820f -> ZERO +16px judder!
        move.l  DB_START(a0),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8201.w
        move.b  d1,$ffff8205.w
        move.w  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8203.w
        move.b  d1,$ffff8207.w
        move.b  d0,$ffff820d.w
        move.b  d0,$ffff8209.w

        move.w  DB_HSCR(a0),d0
        move.b  d0,$ffff8265.w          ; fine pixel hscroll (0..15)
        beq.s   .vt_h0
        clr.b   $ffff820f.w             ; hscroll != 0 -> STE adds +8B auto = 168B!
        bra.s   .vt_arm_tb
.vt_h0:
        move.b  #4,$ffff820f.w          ; hscroll == 0 -> +4 extra words (+8B) = 168B!

.vt_arm_tb:
        ; Arm Timer B: if DB_WRAPY < 181, arm ring-wrap split first, else bottom HUD directly!
        move.l  DB_WRAP(a0),STE_TB_WRAP_A
        move.w  DB_WRAPY(a0),d0
        move.w  d0,STE_TB_WRAP_Y
        cmpi.w  #PITCH_VIS_H,d0         ; wrap_y >= 181 -> no vertical wrap needed!
        bge.s   .vt_hud_only
        ; DB_WRAPY is ALWAYS in 2..180 (y0=207 mirrors row 0->208 and sets wrap_y=2)!
        ; Arm 1 scanline early (wrap_y - 1 >= 1) so ste_tb_wrap locks onto EXACT HBlank!
        subq.w  #1,d0
        move.l  #ste_tb_wrap,$0120.w
        move.b  d0,$fffffa21.w
        bra.s   .vt_tb_go
.vt_hud_only:
        ; Arm 1 scanline early (180 -> locks onto HBlank of line 180 -> HUD starts on 181!)
        move.l  #ste_tb_hud,$0120.w
        move.b  #180,$fffffa21.w
.vt_tb_go:
        move.b  #8,$fffffa1b.w          ; Event Count mode
        bset    #0,$fffffa07.w          ; enable Timer B in IERA
        bset    #0,$fffffa13.w          ; enable Timer B in IMRA
        movem.l (sp)+,d0-d1/a0-a1
        movem.l d0-d1,-(sp)             ; $018d6e expects d0-d1 on stack (original $018d06)!
        jmp     $018d6e.l

.vt_stats_mark:
        move.w  #1,STE_STATS_DIRTY
.vt_stats:
        clr.b   $fffffa1b.w
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        move.b  #$07,$ffff8205.w
        move.b  #$80,$ffff8207.w
        clr.b   $ffff8209.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        movem.l (sp)+,d0-d1/a0-a1
        movem.l d0-d1,-(sp)
        jmp     $018d6e.l

; ---------------------------------------------------------------------------
; Exact HBlank-Locked Timer B ISRs (Blitter-Paused -> ZERO bus-steal jitter!):
;   ste_tb_wrap  : Mid-screen 208-line Ring Buffer vertical wrap (ZERO glitch!)
;   ste_tb_hud   : Bottom HUD split at scanline 181 -> $07f1c0 (ZERO shift/color swap!)
;   ste_tb_bot   : Jet-black bottom border at scanline 197 -> STE_BLACK_LINE!
; ---------------------------------------------------------------------------
ste_tb_wrap:
        clr.b   $fffffa1b.w
        movem.l d0-d4/a0,-(sp)
        bclr    #7,BLT_LINE.w           ; pause active $80 Shared-Bus Blitter (0 jitter!)
        sne     d4                      ; d4.b = $ff if Blitter was running
        ; Pre-split STE_TB_WRAP_A into HIGH(d1), MID(d2), LOW(d3) BEFORE HBlank -> 36-cycle write!
        move.l  STE_TB_WRAP_A(pc),d3
        move.l  d3,d1
        swap    d1                      ; d1.b = HIGH ($8205)
        move.w  d3,d2
        lsr.w   #8,d2                   ; d2.b = MID  ($8207); d3.b = LOW ($8209)
        lea     $ffff8205.w,a0
        ; 1-line-early exact HBlank lock (tolerates up to 50 us interrupt latency!):
        ; Step 1: if in HBlank of line (wrap_y-2), wait for DE=1 of line (wrap_y-1)
.tw_de: move.b  4(a0),d0
        cmp.b   4(a0),d0
        beq.s   .tw_de
        ; Step 2: wait for DE=0 of line (wrap_y-1) = EXACT start of HBlank!
.tw_hb: move.b  4(a0),d0
        cmp.b   4(a0),d0
        bne.s   .tw_hb

ste_tb_wrap_do:
        nop
        nop
        ; Reload live video counter HIGH->MID->LOW in 36 cycles (4.5 us, dead-center in HBlank!)
        move.b  d1,(a0)                 ; $ffff8205 HIGH
        move.b  d2,2(a0)                ; $ffff8207 MID
        move.b  d3,4(a0)                ; $ffff8209 LOW

        ; Schedule ste_tb_hud for scanline 180 (1 line before 181)!
        move.w  #180,d0
        sub.w   STE_TB_WRAP_Y(pc),d0
        ble.s   ste_tb_hud_wait         ; wrap_y == 180 -> stay Blitter-paused, wait line 180 -> HUD!
        move.l  #ste_tb_hud,$0120.w
        move.b  d0,$fffffa21.w
        move.b  #8,$fffffa1b.w
        tst.b   d4
        beq.s   .tw_no_res
        bset    #7,BLT_LINE.w           ; resume paused Blitter seamlessly!
.tw_no_res:
        movem.l (sp)+,d0-d4/a0
        bclr    #0,$fffffa0f.w
        rte

ste_tb_hud:
        clr.b   $fffffa1b.w
        movem.l d0-d4/a0,-(sp)
        bclr    #7,BLT_LINE.w           ; pause active $80 Shared-Bus Blitter (0 jitter!)
        sne     d4                      ; d4.b = $ff if Blitter was running
        lea     $ffff8205.w,a0
ste_tb_hud_wait:
        ; Step 1: if in HBlank of line 179, wait for DE=1 of line 180
.th_de: move.b  4(a0),d0
        cmp.b   4(a0),d0
        beq.s   .th_de
        ; Step 2: wait for DE=0 of line 180 = EXACT start of HBlank before HUD line 181!
.th_hb: move.b  4(a0),d0
        cmp.b   4(a0),d0
        bne.s   .th_hb
        nop
        nop
        ; Step 3: Write HUD address, linewidth=0, hscroll=0, and HUD palette dead-center in HBlank!
        move.b  #$07,(a0)               ; $8205 = $07
        move.b  #$f1,2(a0)              ; $8207 = $f1
        move.b  #$c0,4(a0)              ; $8209 = $c0
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        move.w  #$0030,$ffff8240.w      ; dark pitch green scoreboard bar
        move.w  #$0000,$ffff8242.w      ; col 1 = crisp black (clock + score)
        move.w  #$0730,$ffff8244.w      ; col 2 = crisp orange (home player name)
        move.w  #$0777,$ffff8246.w      ; col 3 = crisp white
        move.w  #$0500,$ffff8248.w      ; col 4 = crisp red (away player name)
        ; Re-arm Timer B for +15 scanlines (1 line early = end of line 195 -> razor-clean HSync cut before 197!)
        move.l  #ste_tb_bot,$0120.w
        move.b  #15,$fffffa21.w
        move.b  #8,$fffffa1b.w
        tst.b   d4
        beq.s   .th_nr
        bset    #7,BLT_LINE.w
.th_nr: movem.l (sp)+,d0-d4/a0
        bclr    #0,$fffffa0f.w
        rte

ste_tb_bot:
        clr.b   $fffffa1b.w
        movem.l d0-d1/a0,-(sp)
        bclr    #7,BLT_LINE.w           ; pause Blitter so line 196->197 border cut is 100% jitter-free!
        sne     d1
        lea     $ffff8205.w,a0
        ; 1-line-early exact HBlank lock on line 196 (4 scanlines before line 199 -> NEVER blocks VBL!)
.tb_de: move.b  4(a0),d0
        cmp.b   4(a0),d0
        beq.s   .tb_de
.tb_hb: move.b  4(a0),d0
        cmp.b   4(a0),d0
        bne.s   .tb_hb
        nop
        nop
        move.b  #$08,(a0)               ; point lines 197..199 to zeroed STE_BLACK_LINE ($080d00) FIRST!
        move.b  #$0d,2(a0)
        clr.b   4(a0)
        clr.l   $ffff8240.w             ; jet-black bottom border right in HSync before line 197!
        clr.l   $ffff8244.w
        clr.l   $ffff8248.w
        clr.l   $ffff824c.w
        tst.b   d1
        beq.s   .tb_nr
        bset    #7,BLT_LINE.w
.tb_nr: movem.l (sp)+,d0-d1/a0
        bclr    #0,$fffffa0f.w
        rte

; ---------------------------------------------------------------------------
; VBL End ($018e0a): Skip ST $ff8240 stripe write, set VBL flag, step DMA Audio
; ---------------------------------------------------------------------------
ste_vbl_end:
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
        cmpi.w  #32,STE_REPEAT_CNT
        bgt.w   .step_stop
        move.b  (a0)+,d0
        move.l  a0,STE_SCRIPT_PTR
        cmpi.b  #-1,d0
        beq.s   .cmd_loop
        cmpi.b  #-2,d0
        beq.w   .step_stop
        cmpi.b  #-3,d0
        beq.s   .cmd_pitch
        cmpi.b  #-4,d0
        beq.s   .cmd_pitch
        cmpi.b  #-5,d0
        beq.w   .step_stop
        cmpi.b  #-6,d0
        beq.s   .cmd_wait
        bra.s   .cmd_sample
.cmd_loop:
        move.l  STE_SCRIPT_ST(pc),STE_SCRIPT_PTR
        bra.s   .next_cmd
.cmd_pitch:
        move.b  (a0)+,STE_SND_PITCH
        move.l  a0,STE_SCRIPT_PTR
        bra.s   .next_cmd
.cmd_wait:
        addq.l  #1,STE_SCRIPT_PTR
        bra.s   .next_cmd
.cmd_sample:
        andi.w  #$00ff,d0
        cmpi.w  #17,d0
        bcc.s   .next_cmd
        mulu.w  #12,d0
        lea     0(a1,d0.w),a0
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.w  (a0)+,d3
        cmpi.l  #16,d2
        ble.s   .step_stop
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
; ZERO-Blit Sprite List Hooks ($01a426 draw, $01a83e erase)
; Records world-space (a3, src, wx, wy) into STE_SPR_LIST; all actual Blitter
; rendering happens invisibly on the Backbuffer inside ste_pitch_update!
; ---------------------------------------------------------------------------
ste_draw_spr_core:
        ; Input: d0.w = x_scr, d1.w = y_scr, a1 = KO2 3bpp src, a3 = KO2 save record
        ; Caller pushed movem.l d0-d2/d4/d7/a0-a1/a3,-(sp)
        move.l  #1,(a3)                 ; mark entity active for KO2
        add.w   STE_CUR_WX(pc),d0       ; world_x (0..1279)
        add.w   STE_CUR_WY(pc),d1       ; world_y (0..1535)
        lea     STE_SPR_LIST.l,a0
        move.w  STE_SPR_CNT(pc),d2
        beq.s   .dsc_add
        subq.w  #1,d2
.dsc_fnd:
        cmpa.l  (a0),a3
        beq.s   .dsc_upd
        lea     16(a0),a0
        dbra    d2,.dsc_fnd
.dsc_add:
        move.w  STE_SPR_CNT(pc),d2
        cmpi.w  #32,d2
        bcc.s   .dsc_ret
        addq.w  #1,STE_SPR_CNT
        move.l  a3,(a0)
.dsc_upd:
        move.l  a1,4(a0)
        move.w  d0,8(a0)                ; world_x
        move.w  d1,10(a0)               ; world_y
.dsc_ret:
        movem.l (sp)+,d0-d2/d4/d7/a0-a1/a3
        rts

ste_erase_spr:
        ; Input: a3 = KO2 save record
        clr.l   (a3)
        movem.l d0-d1/a0-a1,-(sp)
        move.w  STE_SPR_CNT(pc),d0
        beq.s   .es_ret
        lea     STE_SPR_LIST.l,a0
        move.w  d0,d1
        subq.w  #1,d1
.es_fnd:
        cmpa.l  (a0),a3
        beq.s   .es_rm
        lea     16(a0),a0
        dbra    d1,.es_fnd
        bra.s   .es_ret
.es_rm:
        ; O(1) swap-with-last removal!
        subq.w  #1,d0
        move.w  d0,STE_SPR_CNT
        lsl.w   #4,d0
        lea     STE_SPR_LIST.l,a1
        adda.w  d0,a1                   ; a1 = last valid entry
        cmpa.l  a0,a1
        beq.s   .es_ret
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
.es_ret:
        movem.l (sp)+,d0-d1/a0-a1
        rts

; ---------------------------------------------------------------------------
; ste_pitch_update ($01c1d0): True Double-Buffered Frame Render + Atomic Swap!
; ---------------------------------------------------------------------------
ste_pitch_update:
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

        ; 2. Compute clamped world camera (wx, wy) and store for KO2's goal arrow + sprites
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  -$1112(a4),d0
        addi.w  #176,d0
        bge.s   .wx_lo
        moveq   #0,d0
.wx_lo: cmpi.w  #960,d0
        ble.s   .wx_ok
        move.w  #960,d0
.wx_ok:
        move.w  -$110e(a4),d1
        addi.w  #64,d1
        bge.s   .wy_lo
        moveq   #0,d1
.wy_lo: cmpi.w  #1336,d1
        ble.s   .wy_ok
        move.w  #1336,d1
.wy_ok:
        move.w  d0,STE_CUR_WX
        move.w  d1,STE_CUR_WY

        ; Call KO2's off-screen goal arrow updater ($01bffa) BEFORE drawing Backbuffer!
        movem.l d0-d1,-(sp)
        jsr     $01bffa.l
        movem.l (sp)+,d0-d1

        ; If returning from Half-Time/Stats screen ($078000 was overwritten), reset cleanly!
        tst.w   STE_STATS_DIRTY
        beq.s   .pu_clean
        clr.w   STE_STATS_DIRTY
        bsr.w   ste_reset_bufs
        moveq   #4,d0
        trap    #8
        move.w  STE_CUR_WX(pc),d0
        move.w  STE_CUR_WY(pc),d1
.pu_clean:
        ; d2 = tx = wx >> 4 (0..60), d3 = ty = wy >> 4 (0..83), d7 = hscr = wx & 15
        move.w  d0,d2
        lsr.w   #4,d2
        move.w  d1,d3
        lsr.w   #4,d3
        move.w  d0,d7
        andi.w  #15,d7
        move.w  d7,STE_BK_HSCR

        ; Compute y0 = wy % 208 -> d4.w
        moveq   #0,d4
        move.w  d1,d4
        divu.w  #RING_H,d4
        swap    d4                      ; d4.w = y0 (0..207)
        move.w  d4,STE_BK_Y0
        move.w  d2,d5
        lsl.w   #3,d5
        ext.l   d5
        move.l  d5,STE_BK_TX8

        ; Select INVISIBLE Backbuffer descriptor a6 = (STE_SHOW_IDX == 0) ? DB_B : DB_A
        lea     DB_B(pc),a6
        tst.w   STE_SHOW_IDX
        beq.s   .pu_got_bk
        lea     DB_A(pc),a6
.pu_got_bk:
        ; === STEP A: Strict Reverse-LIFO Erase of Backbuffer's old Sprites + Radar ===
        bsr.w   ste_bk_erase_spr
        bsr.w   ste_bk_erase_rad

        ; === STEP B: Update Backbuffer's Dirty Edge Tiles (13 rows x 21 cols, UNMIRRORED!) ===
        move.w  d2,d5
        sub.w   DB_TX(a6),d5            ; dtx
        move.w  d3,d6
        sub.w   DB_TY(a6),d6            ; dty
        move.w  d5,d0
        bpl.s   .adx
        neg.w   d0
.adx:   cmpi.w  #3,d0
        bgt.w   .bk_full
        move.w  d6,d0
        bpl.s   .ady
        neg.w   d0
.ady:   cmpi.w  #3,d0
        bgt.w   .bk_full

        ; Incremental dirty-edge columns & rows on Backbuffer (a6 = DB_*)
        tst.w   d5
        beq.s   .bk_chky
        bgt.s   .bk_sr
        ; Scrolled left: fill columns d2 .. DB_TX-1
        move.w  d2,d0
.bk_sl: bsr.w   ste_bk_draw_col         ; d0=tx_col, d3=ty_top, a6=DB
        addq.w  #1,d0
        cmp.w   DB_TX(a6),d0
        blt.s   .bk_sl
        bra.s   .bk_chky
.bk_sr:
        ; Scrolled right: fill columns DB_TX+21 .. d2+20
        move.w  DB_TX(a6),d0
        addi.w  #21,d0
        move.w  d2,d1
        addi.w  #20,d1
.bk_srl: bsr.w  ste_bk_draw_col
        addq.w  #1,d0
        cmp.w   d1,d0
        ble.s   .bk_srl

.bk_chky:
        tst.w   d6
        beq.s   .bk_tiles_ok
        bgt.s   .bk_sd
        ; Scrolled up: fill rows d3 .. DB_TY-1
        move.w  d3,d0
.bk_su: bsr.w   ste_bk_draw_row         ; d2=tx_left, d0=ty_row, a6=DB
        addq.w  #1,d0
        cmp.w   DB_TY(a6),d0
        blt.s   .bk_su
        bra.s   .bk_tiles_ok
.bk_sd:
        ; Scrolled down: fill rows DB_TY+13 .. d3+12 (13 rows covers 181px @ any wy%16!)
        move.w  DB_TY(a6),d0
        addi.w  #13,d0
        move.w  d3,d1
        addi.w  #12,d1
.bk_sdl: bsr.w  ste_bk_draw_row
        addq.w  #1,d0
        cmp.w   d1,d0
        ble.s   .bk_sdl
        bra.s   .bk_tiles_ok

.bk_full:
        ; Full 21x13 tile fill onto Backbuffer
        move.w  d3,d0
        moveq   #12,d1
.bk_fy: bsr.w   ste_bk_draw_row
        addq.w  #1,d0
        dbra    d1,.bk_fy

.bk_tiles_ok:
        move.w  d2,DB_TX(a6)
        move.w  d3,DB_TY(a6)

        ; === STEP C: Draw Transparent Vector Radar + 23 Dots onto Backbuffer ===
        bsr.w   ste_bk_draw_rad

        ; === STEP D: Draw ALL Active Sprites from STE_SPR_LIST onto Backbuffer ===
        bsr.w   ste_bk_draw_spr

        ; === STEP E: Compute Display Params & Atomically Swap Front <-> Back! ===
        move.l  DB_RING(a6),d0
        add.l   STE_BK_TX8(pc),d0       ; d0 = RING + tx*8 (row 0)
        move.l  d0,DB_WRAP(a6)          ; wrap_addr = RING + tx*8
        move.w  STE_BK_Y0(pc),d1
        move.w  d1,d4
        mulu.w  #RING_STRIDE,d1
        add.l   d0,d1
        move.l  d1,DB_START(a6)         ; start_addr = RING + y0*168 + tx*8
        move.w  #RING_H,d1
        sub.w   d4,d1                   ; wrap_y = 208 - y0 (1..208)
        cmpi.w  #1,d1
        bne.s   .pu_wyok
        ; y0 == 207 (wrap_y == 1): mirror visible row 0 -> row 208 so wrap_y = 2 (full 1-line TB margin!)
        movea.l d0,a0                   ; src = RING + tx*8 (row 0)
        movea.l d0,a1
        adda.l  #RING_BYTES,a1          ; dst = RING + 208*168 + tx*8 (row 208)
        moveq   #41,d2                  ; 42 longs = 168 bytes (1 full scanline)
.pu_m0: move.l  (a0)+,(a1)+
        dbra    d2,.pu_m0
        addi.l  #RING_STRIDE,d0         ; wrap_addr = RING + 168 + tx*8 (row 1)
        move.l  d0,DB_WRAP(a6)
        moveq   #2,d1                   ; wrap_y = 2!
.pu_wyok:
        move.w  d1,DB_WRAPY(a6)
        move.w  STE_BK_HSCR(pc),DB_HSCR(a6)

        ; ATOMIC 1-instruction Front <-> Back buffer flip!
        eori.w  #1,STE_SHOW_IDX

        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; Helpers: draw 1 row (d2=tx_left, d0=ty_row, a6=DB) or 1 col (d0=tx_col, d3=ty_top, a6=DB)
ste_bk_draw_row:
        cmpi.w  #96,d0
        bcc.s   .bdr_ret
        movem.l d0-d2/a0,-(sp)
        move.w  d2,d1                   ; d1 = tx_left
        move.w  d0,d2                   ; d2 = ty_row
        movea.l DB_RING(a6),a0          ; a0 = RING_BASE
        moveq   #8,d0                   ; cmd 8 = unmirrored 21-tile row blit
        trap    #8
        movem.l (sp)+,d0-d2/a0
.bdr_ret:
        rts

ste_bk_draw_col:
        cmpi.w  #80,d0
        bcc.s   .bdc_ret
        movem.l d0-d2/a0,-(sp)
        move.w  d0,d1                   ; d1 = tx_col
        move.w  d3,d2                   ; d2 = ty_top
        movea.l DB_RING(a6),a0          ; a0 = RING_BASE
        moveq   #9,d0                   ; cmd 9 = unmirrored 13-tile col blit
        trap    #8
        movem.l (sp)+,d0-d2/a0
.bdc_ret:
        rts

; ---------------------------------------------------------------------------
; Step A: Reverse-LIFO Erase of Backbuffer's old Sprites & Radar (ZERO overlap checks!)
; ---------------------------------------------------------------------------
ste_bk_erase_spr:
        move.w  DB_SCNT(a6),d1
        beq.s   .bes_ret
        clr.w   DB_SCNT(a6)
        movem.l d0-d1/a0-a1,-(sp)
        move.w  d1,d0
        lsl.w   #4,d0
        movea.l DB_STK(a6),a0
        adda.w  d0,a0                   ; a0 = end of Backbuffer's sprite restore stack
        movea.l DB_SAV(a6),a1           ; a1 = Backbuffer's save-under bank base
        moveq   #2,d0                   ; cmd 2 = reverse-LIFO restore of d1 records
        trap    #8
        movem.l (sp)+,d0-d1/a0-a1
.bes_ret:
        rts

ste_bk_erase_rad:
        movem.l d0-d2/a0-a2,-(sp)
        ; 1. Restore Backbuffer's old radar dots (reverse LIFO)
        move.w  DB_RDCNT(a6),d0
        beq.s   .ber_nod
        clr.w   DB_RDCNT(a6)
        move.w  d0,d1
        mulu.w  #12,d0
        movea.l DB_RDR(a6),a0
        adda.l  d0,a0
        subq.w  #1,d1
.ber_dl:
        lea     -12(a0),a0
        movea.l (a0),a1
        move.l  4(a0),(a1)
        move.l  8(a0),4(a1)
        dbra    d1,.ber_dl
.ber_nod:
        ; 2. Restore Backbuffer's old radar lines (batched cmd 6)
        move.w  DB_RLCNT(a6),d2
        beq.s   .ber_ret
        clr.w   DB_RLCNT(a6)
        move.w  d2,d0
        lsl.w   #4,d0
        movea.l DB_RLR(a6),a2
        adda.w  d0,a2
        moveq   #6,d0                   ; cmd 6 = batch-restore d2 line records ending at a2
        trap    #8
.ber_ret:
        movem.l (sp)+,d0-d2/a0-a2
        rts

; ---------------------------------------------------------------------------
; Step C: Draw Transparent Vector Radar + 23 Dots onto Backbuffer (ring-wrap aware!)
; ---------------------------------------------------------------------------
ste_bk_draw_rad:
        tst.w   -$0e10(a4)              ; Radar ON (> 0)?
        ble.w   .bdr_done_ret
        move.w  -$0e0a(a4),d6           ; Radar scale (8, 12, 16, 20, 24)
        ble.w   .bdr_done_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        ; Rebuild pre-scaled line cache ONLY when scale changes!
        cmp.w   STE_RAD_C_SC(pc),d6
        beq.s   .rc_ok
        move.w  d6,STE_RAD_C_SC
        lea     -$4d78(a4),a3
        lea     STE_RAD_CACHE.l,a0
        moveq   #0,d7
.rc_hl: move.w  (a3)+,d0
        blt.s   .rc_hd
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
        bra.s   .rc_hl
.rc_hd: move.w  d7,STE_RAD_C_HCNT
        moveq   #0,d7
.rc_vl: move.w  (a3)+,d0
        blt.s   .rc_vd
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
        bra.s   .rc_vl
.rc_vd: move.w  d7,STE_RAD_C_VCNT
.rc_ok:
        lea     STE_RAD_CACHE.l,a3
        movea.l DB_RLR(a6),a2           ; line restore record cursor (max 28)
        movea.l DB_RPOOL(a6),a5         ; radar save pool cursor (2,048B safe for both A & B!)
        move.l  a5,d0
        addi.l  #2040,d0
        move.l  d0,STE_BK_REND
        moveq   #0,d7                   ; line record count

        ; Horizontal radar lines
        move.w  STE_RAD_C_HCNT(pc),d6
        beq.s   .br_vs
        subq.w  #1,d6
.br_hl: move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        bsr.s   .br_hline
        dbra    d6,.br_hl

        ; Vertical radar lines (ring-wrap aware!)
.br_vs: move.w  STE_RAD_C_VCNT(pc),d6
        beq.s   .br_blt
        subq.w  #1,d6
.br_vl: move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        bsr.w   .br_vline
        dbra    d6,.br_vl

.br_blt:
        move.w  d7,DB_RLCNT(a6)
        beq.s   .br_dots
        movea.l DB_RLR(a6),a0
        move.w  d7,d1
        moveq   #7,d0                   ; cmd 7 = batch save+draw transparent black lines!
        trap    #8
.br_dots:
        bsr.w   ste_bk_draw_dots
        movem.l (sp)+,d0-d7/a0-a3/a5
.bdr_done_ret:
        rts

; Horizontal radar line: d0=sx1, d1=sy, d2=sx2 -> ring-wrapped dst in DB_RING(a6)
.br_hline:
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .bh_ret
        cmpi.w  #28,d7
        bcc.s   .bh_ret
        add.w   STE_BK_HSCR(pc),d0
        add.w   STE_BK_HSCR(pc),d2
        move.w  d0,d3
        andi.w  #15,d3
        move.w  #$ffff,d4
        lsr.w   d3,d4                   ; ENDMASK1
        move.w  d2,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        move.w  #$ffff,d3
        lsl.w   d5,d3                   ; ENDMASK3
        lsr.w   #4,d0
        lsr.w   #4,d2
        sub.w   d0,d2
        blt.s   .bh_ret
        addq.w  #1,d2                   ; word_cols
        cmpi.w  #1,d2
        bne.s   .bh_m2
        and.w   d3,d4
.bh_m2:
        move.w  d2,d5
        lsl.w   #3,d5
        lea     0(a5,d5.w),a0
        cmpa.l  STE_BK_REND(pc),a0
        bhi.s   .bh_ret
        ; Ring line yr = (y0 + sy) % 208
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bh_yok
        subi.w  #RING_H,d1
.bh_yok:
        mulu.w  #RING_STRIDE,d1
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0
        add.l   d0,d1
        movea.l DB_RING(a6),a1
        adda.l  d1,a1
        move.l  a1,(a2)+
        move.l  a5,(a2)+
        move.w  d2,(a2)+
        move.w  #1,(a2)+
        move.w  d4,(a2)+
        move.w  d3,(a2)+
        addq.w  #1,d7
        adda.w  d5,a5
.bh_ret:
        rts

; Vertical radar line (Y_STEP=4, ring-wrap splitting!): d0=sx, d1=sy1, d2=sy2
.br_vline:
        cmpi.w  #320,d0
        bcc.w   .bv_ret
        cmpi.w  #PITCH_VIS_H,d1
        bcc.w   .bv_ret
        cmpi.w  #PITCH_VIS_H,d2
        bcs.s   .bv_y2
        move.w  #(PITCH_VIS_H-1),d2
.bv_y2: sub.w   d1,d2
        blt.w   .bv_ret
        addq.w  #4,d2
        lsr.w   #2,d2                   ; d2 = total dots (Y_STEP=4)
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        moveq   #0,d4
        bset    d5,d4                   ; ENDMASK1 = ENDMASK3 = single bit
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0       ; d0.l = x_byte_off
        ; yr1 = (y0 + sy1) % 208
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bv_yr1
        subi.w  #RING_H,d1
.bv_yr1:
        ; Check if yr1 + (d2-1)*4 >= 208 (crosses ring seam!)
        move.w  d2,d3
        subq.w  #1,d3
        lsl.w   #2,d3
        add.w   d1,d3
        cmpi.w  #RING_H,d3
        blt.s   .bv_one
        ; Split into top segment (yr1..207) and bottom segment (wrapped..)!
        move.w  #(RING_H-1),d3
        sub.w   d1,d3
        lsr.w   #2,d3
        addq.w  #1,d3                   ; d3 = cnt1
        move.w  d2,d5
        sub.w   d3,d5                   ; d5 = cnt2
        move.w  d5,-(sp)
        move.w  d3,d5
        lsl.w   #2,d5
        add.w   d1,d5
        subi.w  #RING_H,d5              ; d5 = yr2 (0..3)
        move.w  d5,-(sp)
        move.w  d3,d2
        bsr.s   .bv_emit
        move.w  (sp)+,d1                ; yr2
        move.w  (sp)+,d2                ; cnt2
        ble.s   .bv_ret
.bv_one:
        bsr.s   .bv_emit
.bv_ret:
        rts

; Emit 1 vertical radar segment: d0.l=x_off, d1.w=yr, d2.w=cnt, d4.w=mask
.bv_emit:
        cmpi.w  #28,d7
        bcc.s   .be_ret
        move.l  STE_BK_REND(pc),d5
        sub.l   a5,d5
        lsr.l   #3,d5
        ble.s   .be_ret
        cmp.w   d5,d2
        ble.s   .be_ok
        move.w  d5,d2
.be_ok: move.w  d1,d3
        mulu.w  #RING_STRIDE,d3
        add.l   d0,d3
        movea.l DB_RING(a6),a1
        adda.l  d3,a1
        move.l  a1,(a2)+
        move.l  a5,(a2)+
        move.w  #1,(a2)+
        move.w  d2,(a2)+
        move.w  d4,(a2)+
        move.w  d4,(a2)+
        addq.w  #1,d7
        move.w  d2,d5
        lsl.w   #3,d5
        adda.w  d5,a5
.be_ret:
        rts

; Draw 23 transparent 2x1 radar dots onto Backbuffer (ring-wrap aware!)
ste_bk_draw_dots:
        movea.l DB_RDR(a6),a2
        moveq   #0,d7
        movea.l -$5012(a4),a5           ; Home 11 players
        moveq   #10,d5
        moveq   #2,d4                   ; orange
        bsr.s   .bd_team
        movea.l -$4fbc(a4),a5           ; Away 11 players
        moveq   #10,d5
        moveq   #4,d4                   ; red
        bsr.s   .bd_team
        move.w  -$0e14(a4),d0
        blt.s   .bd_done
        move.w  -$0e12(a4),d1
        moveq   #0,d4                   ; white ball
        bsr.s   .bd_dot
.bd_done:
        move.w  d7,DB_RDCNT(a6)
        rts

.bd_team:
        tst.w   $0c(a5)
        beq.s   .bdt_n
        move.w  $20(a5),d0
        blt.s   .bdt_n
        move.w  $22(a5),d1
        bsr.s   .bd_dot
.bdt_n: lea     $186(a5),a5
        dbra    d5,.bd_team
        rts

.bd_dot:
        cmpi.w  #318,d0
        bcc.s   .bdd_r
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .bdd_r
        cmpi.w  #48,d7
        bcc.s   .bdd_r
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2
        move.w  #$c000,d3
        lsr.w   d2,d3
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bdd_y
        subi.w  #RING_H,d1
.bdd_y: mulu.w  #RING_STRIDE,d1
        add.l   d0,d1
        movea.l DB_RING(a6),a0
        adda.l  d1,a0
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
        beq.s   .bdd_r
        cmpi.w  #2,d4
        bne.s   .bdd_c4
        or.w    d3,2(a0)
        rts
.bdd_c4:
        or.w    d3,4(a0)
.bdd_r: rts

; ---------------------------------------------------------------------------
; Step D: Draw ALL Active Sprites from STE_SPR_LIST onto Backbuffer!
; Exact world-to-ring projection, clean y=181 clipping, and 208->0 seam split!
; ZERO beam waits! ZERO overlap chains! ZERO flicker!
; ---------------------------------------------------------------------------
ste_bk_draw_spr:
        move.w  STE_SPR_CNT(pc),d7
        beq.w   .bds_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        lea     STE_SPR_LIST.l,a5       ; active sprite source list
        movea.l DB_STK(a6),a3           ; Backbuffer restore stack write cursor
        moveq   #0,d6                   ; slot_idx & drawn count (0..31)
        subq.w  #1,d7
.bds_lp:
        ; Check vertical visibility: scr_y = world_y - STE_CUR_WY in [0 .. PITCH_VIS_H-1]
        move.w  10(a5),d1               ; world_y
        sub.w   STE_CUR_WY(pc),d1       ; scr_y
        blt.w   .bds_nxt
        cmpi.w  #PITCH_VIS_H,d1
        bge.w   .bds_nxt
        ; Clip height h = min(16, PITCH_VIS_H - scr_y)
        move.w  #PITCH_VIS_H,d3
        sub.w   d1,d3
        cmpi.w  #16,d3
        ble.s   .bds_hok
        moveq   #16,d3                  ; d3 = h (1..16)
.bds_hok:
        ; Check horizontal visibility: rel_col = (world_x >> 4) - DB_TX in [0 .. 19]
        move.w  8(a5),d0                ; world_x
        move.w  d0,d2
        andi.w  #15,d2                  ; d2 = skew (0..15)
        lsr.w   #4,d0                   ; world_col (0..79)
        move.w  d0,d4
        sub.w   DB_TX(a6),d4            ; rel_col
        blt.w   .bds_nxt
        cmpi.w  #20,d4                  ; allow up to col 20 (skew=0 fits in col 20)
        bgt.w   .bds_nxt
        bne.s   .bds_xok
        tst.w   d2
        bne.w   .bds_nxt                ; col 20 with skew > 0 would touch col 21 -> skip!
.bds_xok:
        ; Compute yr = (y0 + scr_y) % 208
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bds_yr
        subi.w  #RING_H,d1
.bds_yr:
        ; Compute x_byte_off = world_col * 8 -> d0.l
        lsl.w   #3,d0
        ext.l   d0
        ; Compute dst_top = RING_BASE + yr * 168 + world_col * 8 -> a0
        move.w  d1,d4
        mulu.w  #RING_STRIDE,d4
        add.l   d0,d4
        movea.l DB_RING(a6),a0
        adda.l  d4,a0                   ; a0 = dst_top

        ; Check if yr + h > RING_H (crosses 208 -> 0 ring seam!)
        move.w  d1,d4
        add.w   d3,d4
        cmpi.w  #RING_H,d4
        ble.s   .bds_nowr
        ; Split at ring seam: h1 = 208 - yr, h2 = h - h1, dst_bot = RING_BASE + world_col * 8
        move.w  #RING_H,d4
        sub.w   d1,d4                   ; d4 = h1 (1..15)
        move.w  d3,d5
        sub.w   d4,d5                   ; d5 = h2 (1..15)
        movea.l DB_RING(a6),a1
        adda.l  d0,a1                   ; a1 = dst_bot
        bra.s   .bds_rec
.bds_nowr:
        move.w  d3,d4                   ; h1 = h
        moveq   #0,d5                   ; h2 = 0
        suba.l  a1,a1                   ; dst_bot = 0
.bds_rec:
        ; Push 16-byte restore record onto Backbuffer's stack (a3):
        ; [+0: dst_top.l, +4: dst_bot.l, +8: h1.w, +10: h2.w, +12: slot_idx.w, +14: pad.w]
        move.l  a0,(a3)+
        move.l  a1,(a3)+
        move.w  d4,(a3)+                ; h1
        move.w  d5,(a3)+                ; h2
        move.w  d6,(a3)+                ; slot_idx
        clr.w   (a3)+

        ; Save-under slot a2 = DB_SAV(a6) + d6 * 256
        move.w  d6,d0
        lsl.w   #8,d0
        ext.l   d0
        movea.l DB_SAV(a6),a2
        adda.l  d0,a2
        addq.w  #1,d6

        ; Call TRAP #8 cmd 3: a0=dst_top, a1=KO2_src, a2=slot, d1=skew, d2=(h2<<16)|h1, d3=dst_bot
        move.l  a1,d3                   ; d3.l = dst_bot (or 0)
        movea.l 4(a5),a1                ; a1 = KO2 3bpp sprite src
        move.w  d2,d1                   ; d1.w = skew (0..15)
        move.w  d5,d2
        swap    d2
        move.w  d4,d2                   ; d2 = (h2<<16) | h1
        moveq   #3,d0
        trap    #8

        cmpi.w  #32,d6
        bcc.s   .bds_done
.bds_nxt:
        lea     16(a5),a5
        dbra    d7,.bds_lp
.bds_done:
        move.w  d6,DB_SCNT(a6)
        movem.l (sp)+,d0-d7/a0-a3/a5
.bds_ret:
        rts

; ---------------------------------------------------------------------------
; TRAP #8 ($a0.w) — Supervisor STE Blitter Dispatcher (Official Shared-Bus $80)
;   cmd 2 : reverse-LIFO restore of d1.w sprite records ending at a0 (a1=SAV_BASE)
;   cmd 3 : save+draw 4bpp masked sprite (a0=dst_top, a1=src, a2=slot, d1=skew, d2=h2|h1, d3=dst_bot)
;   cmd 4 : clear STE_RING_A, STE_RING_B, STE_BLACK_LINE
;   cmd 6 : batch reverse-LIFO restore of d2.w radar line records ending at a2
;   cmd 7 : batch save+draw of d1.w transparent black radar lines at a0
;   cmd 8 : unmirrored 21-tile horizontal row blit (a0=RING_BASE, d1=tx_left, d2=ty_row)
;   cmd 9 : unmirrored 13-tile vertical col blit   (a0=RING_BASE, d1=tx_col, d2=ty_top)
; ---------------------------------------------------------------------------
ste_trap8_handler:
        cmpi.w  #2,d0
        beq.s   .cmd2_rest_lifo
        cmpi.w  #3,d0
        beq.w   .cmd3_spr
        cmpi.w  #4,d0
        beq.w   .cmd4_clr
        cmpi.w  #6,d0
        beq.w   .cmd6_rad_rest
        cmpi.w  #7,d0
        beq.w   .cmd7_rad_draw
        cmpi.w  #8,d0
        beq.w   .cmd8_blit_row
        bra.w   .cmd9_blit_col

; Official Atari STE Shared-Bus ($80) Blitter trigger: yields every 64 cycles (8 us)
; so 1-line-early HBlank-locked Timer B NEVER misses HBlank, and bset #7 NEVER stalls!
.blt80: move.b  #$80,BLT_LINE.w
.b80_w: bset    #7,BLT_LINE.w
        nop
        bne.s   .b80_w
        rts

; --- cmd 2: Batched Reverse-LIFO sprite restore (d1.w records ending at a0, a1=SAV_BASE) ---
.cmd2_rest_lifo:
        movem.l d2-d3,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-14),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #8,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c2_lp: lea     -16(a0),a0
        move.w  12(a0),d0               ; slot_idx (0..31)
        lsl.w   #8,d0
        ext.l   d0
        add.l   a1,d0                   ; slot_addr
        move.l  d0,BLT_SRC_ADDR.w
        move.l  (a0),BLT_DST_ADDR.w     ; dst_top
        move.w  8(a0),d2                ; h1
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  10(a0),d3               ; h2 (wrap bottom segment?)
        beq.s   .c2_nxt
        ; Note: BLT_SRC_ADDR already points right after h1*16 bytes in slot!
        move.l  4(a0),BLT_DST_ADDR.w    ; dst_bot
        move.w  d3,BLT_YCOUNT.w
        bsr.w   .blt80
.c2_nxt:
        dbra    d1,.c2_lp
        movem.l (sp)+,d2-d3
        rte

; --- cmd 3: Save-under + Direct NFSR 4bpp Masked Sprite Draw (ring-seam & clip aware!) ---
; a0=dst_top, a1=KO2_src, a2=slot, d1.w=skew, d2.l=(h2<<16)|h1, d3.l=dst_bot
.cmd3_spr:
        movem.l d2-d5/a3-a5,-(sp)
        movea.l a0,a4                   ; a4 = dst_top
        movea.l a2,a5                   ; a5 = slot
        ; 1. Build 16-word 1bpp sprite mask in STE_MASK_BUF (Shared-Bus $80 -> ZERO Hog blits in live play!)
        lea     STE_MASK_BUF.l,a3
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        clr.w   BLT_SRC_XINC.w
        move.w  #$78,BLT_SRC_YINC.w
        clr.w   BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #1,BLT_XCOUNT.w
        clr.b   BLT_SKEW.w
        move.w  #$0203,BLT_HOP.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  #$0207,BLT_HOP.w
        lea     $28(a1),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     $28(a2),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80

        ; 2. Draw Top segment (a4=dst_top, a1=src, a5=slot, a3=mask, d4=h1, d1=skew)
        move.w  d2,d4                   ; d4 = h1 (1..16)
        bsr.s   .c3_seg
        ; 3. Draw Bottom wrap segment if h2 > 0!
        swap    d2
        tst.w   d2
        beq.s   .c3_done
        move.w  d4,d0
        mulu.w  #$78,d0
        adda.l  d0,a1                   ; advance src by h1 lines
        move.w  d4,d0
        lsl.w   #4,d0
        adda.w  d0,a5                   ; advance slot by h1*16 bytes
        move.w  d4,d0
        add.w   d0,d0
        adda.w  d0,a3                   ; advance mask by h1*2 bytes
        movea.l d3,a4                   ; a4 = dst_bot
        move.w  d2,d4                   ; d4 = h2
        bsr.s   .c3_seg
.c3_done:
        movem.l (sp)+,d2-d5/a3-a5
        rte

; Helper: save-under + masked 4bpp draw of d4 lines (a4=dst, a1=src, a5=slot, a3=mask, d1=skew)
.c3_seg:
        ; A. Save-under (a4 -> a5, d4 lines x 8 words)
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.l  a4,BLT_SRC_ADDR.w
        move.l  a5,BLT_DST_ADDR.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #(RING_STRIDE-14),BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #8,BLT_XCOUNT.w
        move.w  d4,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        bsr.w   .blt80

        ; B. Configure skew
        tst.w   d1
        bne.s   .c3s_sk
        move.w  #1,BLT_XCOUNT.w
        clr.w   BLT_DST_XINC.w
        move.w  #RING_STRIDE,BLT_DST_YINC.w
        clr.b   BLT_SKEW.w
        bra.s   .c3s_m
.c3s_sk:
        move.w  #$ffff,d0
        lsr.w   d1,d0
        move.w  d0,BLT_ENDMASK1.w
        not.w   d0
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_XCOUNT.w
        move.w  #8,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-8),BLT_DST_YINC.w
        move.b  d1,d0
        ori.b   #$40,d0                 ; NFSR = 1
        move.b  d0,BLT_SKEW.w
.c3s_m:
        ; Pass 1: Clear mask holes in planes 0, 1, 2 (~SRC & DST, Shared-Bus $80 -> <= 8 us TB latency!)
        clr.w   BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #$0204,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w
        lea     2(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; Pass 2: OR mask into plane 3 (sprite colours 9..15)
        move.w  #$0207,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; Pass 3: OR sprite planes 0, 1, 2 from KO2 src a1 (stride $78)
        move.w  #$78,BLT_SRC_YINC.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     $28(a1),a2
        lea     2(a4),a0
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     $28(a2),a2
        addq.l  #2,a0
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        rts

; --- cmd 4: Zero STE_RING_A, STE_RING_B, and STE_BLACK_LINE ---
.cmd4_clr:
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        clr.w   BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.l  #STE_RING_A,BLT_DST_ADDR.w
        move.w  #84,BLT_XCOUNT.w
        move.w  #423,BLT_YCOUNT.w       ; 423 * 168 = 71,064B (strictly inside $088ee0..$09a4ff!)
        move.b  #$c0,BLT_LINE.w
        move.l  #STE_BLACK_LINE,BLT_DST_ADDR.w
        move.w  #80,BLT_XCOUNT.w
        move.w  #4,BLT_YCOUNT.w         ; 640B zeroed for lines 197..199!
        move.b  #$c0,BLT_LINE.w
        rte

; --- cmd 6: Batched Reverse-LIFO Radar Line Restore (d2.w records ending at a2) ---
.cmd6_rad_rest:
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d2
.c6_lp: lea     -16(a2),a2
        move.l  4(a2),BLT_SRC_ADDR.w
        move.l  (a2),BLT_DST_ADDR.w
        move.w  8(a2),d1                ; word_cols
        lsl.w   #2,d1                   ; XCOUNT = word_cols * 4
        move.w  d1,d0
        subq.w  #1,d0
        add.w   d0,d0
        neg.w   d0
        cmpi.w  #4,d1
        bne.s   .c6_s1
        addi.w  #(4*RING_STRIDE),d0
        bra.s   .c6_s2
.c6_s1: addi.w  #RING_STRIDE,d0
.c6_s2: move.w  d0,BLT_DST_YINC.w
        move.w  d1,BLT_XCOUNT.w
        move.w  10(a2),BLT_YCOUNT.w
        bsr.w   .blt80
        dbra    d2,.c6_lp
        rte

; --- cmd 7: Batched Transparent Black Radar Line Save + Draw (d1.w records at a0) ---
.cmd7_rad_draw:
        movem.l d2-d6/a1,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #$ffff,BLT_ENDMASK2.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c7_lp: movea.l (a0)+,a1                ; dst
        move.l  (a0)+,d4                ; save pool ptr
        move.w  (a0)+,d3                ; word_cols
        move.w  (a0)+,d2                ; H
        move.w  d3,d5
        lsl.w   #2,d5
        move.w  d5,d6
        subq.w  #1,d6
        add.w   d6,d6
        neg.w   d6
        cmpi.w  #1,d3
        bne.s   .c7_s1
        addi.w  #(4*RING_STRIDE),d6
        bra.s   .c7_s2
.c7_s1: addi.w  #RING_STRIDE,d6
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
        bsr.w   .blt80
        move.w  (a0)+,BLT_ENDMASK1.w
        move.w  (a0)+,BLT_ENDMASK3.w
        move.w  #8,BLT_DST_XINC.w
        move.w  d3,d6
        subq.w  #1,d6
        lsl.w   #3,d6
        neg.w   d6
        cmpi.w  #1,d3
        bne.s   .c7_d1
        addi.w  #(4*RING_STRIDE),d6
        bra.s   .c7_d2
.c7_d1: addi.w  #RING_STRIDE,d6
.c7_d2: move.w  d6,BLT_DST_YINC.w
        move.w  d3,BLT_XCOUNT.w
        move.w  #$000f,BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a1
        clr.w   BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a1
        move.w  #$000f,BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        dbra    d1,.c7_lp
        movem.l (sp)+,d2-d6/a1
        rte

; --- cmd 8: Unmirrored 21-tile Horizontal Row Blit (a0=RING_BASE, d1=tx_left, d2=ty_row) ---
.cmd8_blit_row:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        clr.b   BLT_SKEW.w

        ; Map ptr a2 = STE_PIT_MAP + ty_row*80 + tx_left
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        ; Dst a3 = a0 (RING_BASE) + (ty_row % 13)*16*168 + tx_left*8
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #RING_ROWS,d0
        swap    d0
        lsl.w   #4,d0
        mulu.w  #RING_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        ; Tile count = min(21, 80 - tx_left)
        moveq   #21,d7
        moveq   #80,d0
        sub.w   d1,d0
        ble.s   .c8_done
        cmp.w   d7,d0
        bge.s   .c8_cnt
        move.w  d0,d7
.c8_cnt:
        ; Clear Plane 3 for the row in ONE call (unmirrored!)
        move.w  d7,d5
        move.w  d7,d4
        subq.w  #1,d4
        lsl.w   #3,d4
        neg.w   d4
        addi.w  #RING_STRIDE,d4
        move.w  #8,BLT_DST_XINC.w
        move.w  d4,BLT_DST_YINC.w
        move.w  d7,BLT_XCOUNT.w
        clr.w   BLT_HOP.w
        lea     6(a3),a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80

        ; Blit 3bpp tiles (unmirrored -> 2x faster!)
        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-4),BLT_DST_YINC.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        move.w  d5,d7
        subq.w  #1,d7
.c8_lp: moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #8,a3
        dbra    d7,.c8_lp
.c8_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte

; --- cmd 9: Unmirrored 13-tile Vertical Column Blit (a0=RING_BASE, d1=tx_col, d2=ty_top) ---
.cmd9_blit_col:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        clr.b   BLT_SKEW.w

        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #RING_ROWS,d0
        swap    d0
        move.w  d0,d6                   ; cur_row_mod (0..12)
        lsl.w   #4,d0
        mulu.w  #RING_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        moveq   #RING_ROWS,d7           ; 13 rows!
        moveq   #96,d0
        sub.w   d2,d0
        ble.w   .c9_done
        cmp.w   d7,d0
        bge.s   .c9_cnt
        move.w  d0,d7
.c9_cnt:
        ; Clear Plane 3 for entire 208-line vertical column in ONE call!
        move.w  d1,d0
        lsl.w   #3,d0
        ext.l   d0
        lea     6(a0),a1
        adda.l  d0,a1
        clr.w   BLT_DST_XINC.w
        move.w  #RING_STRIDE,BLT_DST_YINC.w
        move.w  #1,BLT_XCOUNT.w
        clr.w   BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  #RING_H,BLT_YCOUNT.w    ; 208 lines (unmirrored -> 2x faster!)
        bsr.w   .blt80

        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-4),BLT_DST_YINC.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        subq.w  #1,d7
.c9_lp: moveq   #0,d0
        move.b  (a2),d0
        adda.w  #80,a2
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.w  #1,d6
        cmpi.w  #RING_ROWS,d6
        blt.s   .c9_st
        moveq   #0,d6
        suba.l  #(RING_BYTES-16*RING_STRIDE),a3
        bra.s   .c9_nx
.c9_st: adda.w  #(16*RING_STRIDE),a3
.c9_nx: dbra    d7,.c9_lp
.c9_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte
