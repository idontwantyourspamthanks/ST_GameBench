; ---------------------------------------------------------------------------
; Player Manager v1.1 — Atari STE Triple-Buffered Amiga Engine (KO2STE.BIN)
;
; Loaded at $0ae940..$0b0eff (max 9,664 bytes) ONLY on Atari STE / Mega STE
; (when BR_IS_STE == 1, 2 MB+ RAM). Plain 68000 ST never loads/calls this and
; keeps 100% classic v1.0 ST mode automatically.
;
; 2 MB+ STE Match Arena ($0d0000..$169fff = 616 KB, >250 KB below 2MB HDDRIVER):
;   $0d0000..$1077ff : DB_A / DB_B / DB_C 448-line linear Ring Buffers (3 x 74 KB)
;   $107800..$10c23f : DB_C save-under/HUD/radar pools + DB_A/B/C fast radar RLR
;   $10c400..$10e4cf : 1bpp radar pre-bake scratch (load-time) + $10e000 render stack
;   $10e800..$1367ff : 5-scale x 16-hscr pre-baked radar (solid $ffff + masked!)
;   $136800..$15e7ff : 640 x 256B pre-trimmed, pre-masked, X-trimmed 4bpp sprites
;   $15e800..$165fff : 7,680 x 4B pre-expanded 32-bit pitch tile source pointers
;   $166000..$1674ff : 336 x 16B DOT_X_LUT (byte offsets + 32-bit Home/Away/Ball masks)
;   $168000..$169fff : DB_A / DB_B 4 KB HUD save-under pools (max 3,040B < 4,096B!)
;
; Entry points (fixed header at $0ae940):
;   +$00 : bra.w ste_install_hooks  (after KO2ENG.BIN loads, before $01fd92)
;   +$04 : bra.w ste_cleanup        (in Supervisor SR=$2700 on KO2 exit)
;   +$08 : STE_SND_SIZE.l           (filled by ko2_bridge.s with AMIGASND.BIN size)
;   +$0c : bra.w ste_load_pitch     (after $013450, loads AMIGAP0..3.BIN -> $081000)
; ---------------------------------------------------------------------------

        org     $0ae940

KO2_A4          equ     $0284aa

; Amiga pitch data ($081000..$088e1f)
STE_PIT_PAL     equ     $081000         ; 32 bytes (8 STE 12-bit pitch colours)
STE_PIT_MAP     equ     $081020         ; 7,680 bytes (80 x 96 tilemap)
STE_PIT_TILES   equ     $082e20         ; 24,576 bytes (256 x 96 bytes 3bpp tiles)

; Low-RAM save pools for DB_A / DB_B + KO2 hidden HUD source
STE_RING_A      equ     $088e60
STE_RING_B      equ     $0923f0
STE_SAV_A       equ     $07c800         ; $07c800..$07e7ff (8 KB)
STE_SAV_B       equ     $078000         ; $078000..$079fff (8 KB)
STE_HUD_SAV_A   equ     $168000         ; $168000..$168fff (4 KB — full 4-box HUD save-under!)
STE_HUD_SAV_B   equ     $169000         ; $169000..$169fff (4 KB — full 4-box HUD save-under!)
STE_HUD_MASK    equ     $07b000         ; $07b000..$07bbff (box headers + 1bpp planes < $07bc00!)
STE_HUD_SRC     equ     $07f1c0         ; KO2 hidden bottom HUD (16 lines x 160B)
STE_RPOOL_A     equ     $07fd00         ; $07fd00..$0804ff (2 KB)
STE_RPOOL_B     equ     $080500         ; $080500..$080cff (2 KB)

; Metadata in KO2-untouched RAM ($09ba00..$09caa0 < $09d000 FILES.CR!)
STE_STK_A       equ     $09ba00         ; 32 x 16B = 512B -> $09bc00
STE_STK_B       equ     $09bc00         ; 32 x 16B = 512B -> $09be00
STE_RLR_A       equ     $09be00
STE_RLR_B       equ     $09bfc0
STE_SPR_LIST    equ     $09c180         ; 32 x 16B = 512B -> $09c380
STE_RAD_CACHE   equ     $09c380         ; 24 x 8B  = 192B -> $09c440
STE_RDR_A       equ     $09c460         ; 48 x 12B = 576B -> $09c6a0
STE_RDR_B       equ     $09c6a0         ; 48 x 12B = 576B -> $09c8e0
STE_Y168_TBL    equ     $09c8e0         ; 224 x 2B = 448B y*168 LUT -> $09caa0

; 2 MB+ Upper-RAM Pre-Baked Caches ($10e800..$189fff)
STE_RAD_BAKE    equ     $10e800         ; 160 KB (5 scales x 32 KB)
STE_SPR_CACHE   equ     $136800         ; 160 KB (640 x 256B sprites)
STE_MAP32       equ     $15e800         ;  30 KB (7,680 x 4B tile ptrs)
STE_DOT_XLUT    equ     $166000         ; 5.3 KB (336 x 16B radar dot X-LUT)
STE_ARENA_END   equ     $16a000         ; Bus-Error + anti-alias probe address

RING_STRIDE     equ     168             ; 336 pixels = 21 x 16px words (4bpp)
RING_H          equ     224             ; 14 tile rows = 224 scanlines
RING_ROWS       equ     14              ; 224 / 16
RING_BYTES      equ     37632           ; 224 * 168
PITCH_VIS_H     equ     200             ; full 320x200 pitch!
HUD_SCR_Y       equ     183             ; transparent HUD top scanline (183..198)

; Buffer descriptor offsets (64 bytes per buffer: DB_A at 0, DB_B at 64, DB_C at 128)
DB_RING         equ     0               ; .l ring base ($0d0000 / $0e2800 / $0f5000)
DB_SAV          equ     4               ; .l save-under base
DB_STK          equ     8               ; .l sprite restore stack base
DB_RPOOL        equ     12              ; .l radar line save pool base (2 KB)
DB_RLR          equ     16              ; .l radar line record base (256 x 4B)
DB_RDR          equ     20              ; .l radar dot record base (48 x 12B)
DB_TX           equ     24              ; .w last tile X drawn into this ring
DB_TY           equ     26              ; .w last tile Y drawn into this ring
DB_SCNT         equ     28              ; .w sprites drawn onto this ring (0..32)
DB_RLCNT        equ     30              ; .w radar words drawn onto this ring (0..254)
DB_RDCNT        equ     32              ; .w radar dots + UL drawn onto this ring (0..48)
DB_WTGT         equ     34              ; .w reserved
DB_START        equ     36              ; .l display start addr (RING + y0*168 + tx*8)
DB_WRAP         equ     40              ; .l display wrap addr  (RING + tx*8)
DB_WRAPY        equ     44              ; .w wrap scanline
DB_HSCR         equ     46              ; .w fine hscroll (0..15)
DB_HUDSAV       equ     48              ; .l HUD save-under base
DB_HUD_T        equ     52              ; .l unused
DB_HUD_B        equ     56              ; .l unused
DB_HUD_H1       equ     60              ; .w HUD segment count drawn on this ring (0..4)
DB_HUD_H2       equ     62              ; .w unused
DB_SIZE         equ     64

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

; Fixed Jump Table & Header at $0ae940 (offsets +$00..+$10 ABI-locked with ko2_bridge.s!)
ste_entry:
        bra.w   ste_install_hooks       ; +$00
        bra.w   ste_cleanup             ; +$04
STE_SND_SIZE:   dc.l    0               ; +$08 (set by ko2_bridge.s)
        bra.w   ste_load_pitch          ; +$0c

; ---------------------------------------------------------------------------
; Audio State variables (+$10 = STE_SND_BASE, read by ko2_bridge.s!)
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
; Triple-Buffered Video & Engine State (+$24 = STE_PITCH_OK)
; ---------------------------------------------------------------------------
STE_PITCH_OK:   dc.w    0               ; +$24: 1 = AMIGAPx.BIN loaded & pre-baked
STE_BIG_RAM:    dc.w    0               ; 1 = >= 2 MB STE verified
STE_SHOW_IDX:   dc.w    0               ; newest completed buffer index (0..2)
STE_DISP_IDX:   dc.w    0               ; buffer index currently scanned out by Shifter
STE_PEND_IDX:   dc.w    0               ; buffer index queued in $8201/$03/$0d for next VSync
STE_PEND_HSCR:  dc.w    0               ; hscr matching STE_PEND_IDX (applied after VSync!)
STE_BK_IDX:     dc.w    0               ; backbuffer index being rendered in ste_pu_sup
STE_VBL_SEQ:    dc.w    0               ; seqlock counter incremented in ste_vbl_end
STE_HUD_TICK:   dc.w    0               ; HUD cache refresh counter
STE_HUD_CCNT:   dc.w    0               ; cached non-empty HUD box count (0..4)
STE_HUD_HVALID: dc.w    0               ; 16-bit mask of valid hscr slots in STE_HUD_CACHE
STE_HUD_HASH:   dc.l    -1              ; rolling dirty hash of STE_HUD_SRC
STE_STATS_DIRTY: dc.w   0               ; 1 = returning from Half-Time/Stats ($078000 dirty)
STE_ORIG_TB:    dc.l    0               ; saved KO2 original Timer B vector ($120.w)
STE_ORIG_VBL:   dc.l    0               ; saved TOS original VBL vector ($70.w)
STE_KBD_IOREC:  dc.l    0               ; XBIOS Iorec(1) ptr for 44-cycle Cconis check!
STE_CUR_WX:     dc.w    176             ; current camera world X (pixels)
STE_CUR_WY:     dc.w    64              ; current camera world Y (pixels)
STE_SPR_CNT:    dc.w    0               ; active sprites in STE_SPR_LIST (0..32)
STE_WALKOUT:    dc.w    0               ; 1 = walk-out ($0a->$0b->$01), clears at centre circle ($02)
STE_CUR_60HZ:   dc.w    0               ; 0 = 50 Hz PAL, 1 = 60 Hz NTSC turbo (toggled by 'H')
STE_RAD_C_HCNT: dc.w    0
STE_RAD_C_VCNT: dc.w    0
STE_BK_HSCR:    dc.w    0               ; backbuffer hscr (0..15) during draw
STE_BK_Y0:      dc.w    0               ; backbuffer y0 (0..223) during draw
STE_BK_TX8:     dc.l    0               ; backbuffer tx*8 during draw
STE_UL_DASH:    dc.l    0               ; secondary/pass-target player struct ptr ($fc3f)
STE_FRM_CNT:    dc.l    0               ; published STE frames counter
STE_SAV_ISP:    dc.l    0               ; saved KO2 ISP across ste_pu_sup ($10e000 stack!)

str_60hz:       dc.b    "60 HZ MODE",0
str_50hz:       dc.b    "50 HZ MODE",0
                even

DB_A:
        dc.l    STE_RING_A, STE_SAV_A, STE_STK_A, STE_RPOOL_A, STE_RLR_A, STE_RDR_A
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    STE_RING_A, STE_RING_A
        dc.w    224, 0
        dc.l    STE_HUD_SAV_A, 0, 0
        dc.w    0, 0
DB_B:
        dc.l    STE_RING_B, STE_SAV_B, STE_STK_B, STE_RPOOL_B, STE_RLR_B, STE_RDR_B
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    STE_RING_B, STE_RING_B
        dc.w    224, 0
        dc.l    STE_HUD_SAV_B, 0, 0
        dc.w    0, 0
DB_C:
        dc.l    0, 0, 0, 0, 0, 0
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    0, 0
        dc.w    224, 0
        dc.l    0, 0, 0
        dc.w    0, 0

; ---------------------------------------------------------------------------
; ste_install_hooks: Verify 2 MB+ STE arena & patch KO2ENG.BIN ($010000..$024000)
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
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        clr.w   STE_VBL_SEQ
        clr.w   STE_HUD_HVALID
        moveq   #-1,d0
        move.l  d0,STE_HUD_HASH
        clr.w   STE_STATS_DIRTY
        clr.l   STE_ORIG_TB
        clr.l   STE_ORIG_VBL
        clr.w   STE_SPR_CNT
        clr.w   STE_WALKOUT
        clr.w   STE_CUR_60HZ
        clr.l   STE_UL_DASH

        ; Cache XBIOS Iorec(1) keyboard ring-buffer struct for 44-cycle Cconis()!
        move.w  #1,-(sp)
        move.w  #14,-(sp)               ; XBIOS #14 Iorec(1)
        trap    #14
        addq.l  #4,sp
        move.l  d0,STE_KBD_IOREC

        ; Probe 2 MB+ STE arena & install TRAP #8 ($a0.w) + VBL ($70.w) via Supexec
        pea     ste_inst_trap8(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp
        tst.w   STE_BIG_RAM
        beq.w   .ih_abort               ; < 2 MB safety guard -> leave Classic ST intact!

        ; Prebuild 224-entry y*168 LUT ($09c8e0..$09ca9f)
        lea     STE_Y168_TBL.l,a0
        moveq   #0,d0
        move.w  #223,d1
.y168:  move.w  d0,(a0)+
        addi.w  #RING_STRIDE,d0
        dbra    d1,.y168

        ; Apply all 18 6-byte jmp hooks into KO2ENG.BIN via compact table
        lea     ste_hook_tbl(pc),a0
        moveq   #17,d0
.ih_lp: movea.l (a0)+,a1
        move.w  #$4ef9,(a1)+
        move.l  (a0)+,(a1)
        dbra    d0,.ih_lp

        ; Replace KO2's two radar-dot divs.w pairs ($01fd00 & $01fd64, 12B each) with shift fast-path!
        move.w  #$4eb9,d0
        move.l  #ste_rad_div,d1
        move.w  #$6004,d2               ; bra.s +4 (lands on $01fd0c / $01fd70)
        move.w  d0,$01fd00.l
        move.l  d1,$01fd02.l
        move.w  d2,$01fd06.l
        move.w  d0,$01fd64.l
        move.l  d1,$01fd66.l
        move.w  d2,$01fd6a.l

        ; Expand KO2's sprite Y-culling limit from 183 ($b7) to 200 ($c8) for full 320x200 pitch!
        move.w  #PITCH_VIS_H,d1
        move.w  d1,$01a304.l
        move.w  d1,$01a34e.l
        move.w  d1,$01a3c4.l
        move.w  d1,$01a41c.l

        ; Skip ALL KO2 hidden $078000 radar line/dot & solid underline drawers!
        move.w  #$4e75,d1
        move.w  d1,$01fae8.l            ; rts (radar pitch lines)
        move.w  d1,$01fbb4.l            ; rts (radar dot plot 1; keeps $20(a5)/$22(a5) updates!)
        move.w  d1,$01fbf8.l            ; rts (radar dot plot 2)
        move.w  d1,$01fc3c.l            ; rts (radar dot erase — protects STE_SAV_B @ $078000!)
        move.w  d1,$01fca0.l            ; rts (radar ball dot — protects STE_SAV_B @ $078000!)
        move.l  #$60000036,$01f9e0.l    ; bra.w $01fa18 (skip $078000 solid underline!)
.ih_abort:
        rts

ste_hook_tbl:
        dc.l    $01849e,ste_load_samples
        dc.l    $0184fe,ste_play_sound
        dc.l    $018506,ste_play_sound_hi
        dc.l    $018598,ste_stop_sound
        dc.l    $018d06,ste_vbl_skip
        dc.l    $018e0a,ste_vbl_end
        dc.l    $01c1d0,ste_pitch_update
        dc.l    $01a32c,ste_draw_id     ; intercept spr_id (0..639) -> 256B pre-baked cache!
        dc.l    $01a3a0,ste_draw_id
        dc.l    $01a3f6,ste_draw_id
        dc.l    $01a426,ste_draw_spr_core
        dc.l    $01a83e,ste_erase_spr
        dc.l    $01a376,$01a39c         ; bypass KO2 Classic ST Timer B raster wait 1
        dc.l    $01a3cc,$01a3f2         ; bypass KO2 Classic ST Timer B raster wait 2
        dc.l    $01fa76,ste_rec_ul_dash
        dc.l    $01780e,ste_fast_sqrt
        dc.l    $02024a,ste_fast_cconis ; 44-cycle direct Iorec(1) empty check (skips TRAP #1!)
        dc.l    $01b63e,ste_key_hook    ; in-match 'H' = live 50 Hz <-> 60 Hz toggle!

; ---------------------------------------------------------------------------
; Fast KO2 Per-Frame Helpers: Underline, Sqrt, Radar Div, Iorec Cconis, 'H' Key
; ---------------------------------------------------------------------------
ste_rec_ul_dash:
        move.l  a5,STE_UL_DASH
        jmp     $01faae.l

ste_rad_div:
        tst.w   d0
        bmi.s   .srd_div
        tst.w   d1
        bmi.s   .srd_div
        cmpi.w  #16,-$0e0a(a4)
        beq.s   .srd_16
        cmpi.w  #8,-$0e0a(a4)
        beq.s   .srd_8
.srd_div:
        ext.l   d0
        ext.l   d1
        divs.w  -$0e0a(a4),d0
        divs.w  -$0e0a(a4),d1
        rts
.srd_16:
        lsr.w   #4,d0
        lsr.w   #4,d1
        rts
.srd_8:
        lsr.w   #3,d0
        lsr.w   #3,d1
        rts

ste_fast_cconis:
        move.l  a0,-(sp)
        movea.l STE_KBD_IOREC(pc),a0
        move.w  6(a0),d0                ; ibufhd
        cmp.w   8(a0),d0                ; == ibuftl?
        bne.s   .fc_key
        moveq   #0,d0                   ; empty -> 0 in 44 cycles (no TRAP #1!)
        movea.l (sp)+,a0
        rts
.fc_key:
        move.w  #$0b,-(sp)              ; key waiting -> genuine GEMDOS Cconis()
        trap    #1
        addq.l  #2,sp
        movea.l (sp)+,a0
        rts

ste_key_hook:
        move.w  d0,d1
        andi.w  #$df,d1
        cmpi.w  #'H',d1                 ; 'h' or 'H' = toggle 50 Hz <-> 60 Hz!
        bne.s   .kh_pass
        movem.l d0-d2/a0-a3,-(sp)
        pea     ste_toggle_hz(pc)
        move.w  #$26,-(sp)              ; Supexec
        trap    #14
        addq.l  #6,sp
        lea     str_60hz(pc),a3
        tst.w   STE_CUR_60HZ
        bne.s   .kh_msg
        lea     str_50hz(pc),a3
.kh_msg:
        move.l  a3,-$11d8(a4)           ; KO2 bottom-centre HUD message ptr
        move.w  #90,-$11d4(a4)          ; show for ~1.5s, then auto-restore clock
        clr.w   STE_HUD_TICK            ; trigger immediate HUD dirty check next frame!
        moveq   #-1,d0
        move.l  d0,STE_HUD_HASH
        movem.l (sp)+,d0-d2/a0-a3
        jmp     $01b556.l
.kh_pass:
        jmp     $01b650.l               ; Esc disabled -> continue to $01b650 spacebar check

ste_toggle_hz:
        move.b  $ffff8260.w,d0
        andi.b  #3,d0
        cmpi.b  #2,d0                   ; skip on 71 Hz monochrome monitor
        beq.s   .thz_ret
        bchg    #1,$ffff820a.w          ; flip bit 1 (1 = 50 Hz PAL, 0 = 60 Hz NTSC)
        btst    #1,$ffff820a.w
        beq.s   .thz_60
        move.w  #1,$448.w
        clr.w   STE_CUR_60HZ
        rts
.thz_60:
        clr.w   $448.w
        move.w  #1,STE_CUR_60HZ
.thz_ret:
        rts

ste_fast_sqrt:
        cmpi.l  #1,d0
        bls.s   .sq_ret
        movem.l d1-d2,-(sp)
        moveq   #32,d2                  ; clears d2[31:16] = 0 for all word-load paths below!
        cmpi.l  #$1000,d0
        bcc.s   .sq_hi
        cmpi.l  #$100,d0
        bcs.s   .sq_lp
        move.w  #128,d2
        bra.s   .sq_lp
.sq_hi: cmpi.l  #$100000,d0
        bcc.s   .sq_vhi
        move.w  #512,d2
        cmpi.l  #$10000,d0
        bcs.s   .sq_lp
        move.w  #2048,d2
        bra.s   .sq_lp
.sq_vhi:
        move.w  #8192,d2
        cmpi.l  #$1000000,d0
        bcs.s   .sq_lp
        move.w  #$ffff,d2
.sq_lp: move.l  d2,d1
        move.l  d0,d2
        divu.w  d1,d2
        ext.l   d2
        add.l   d1,d2
        lsr.l   #1,d2
        sub.l   d2,d1
        cmpi.w  #-1,d1
        blt.s   .sq_lp
        cmpi.w  #1,d1
        bgt.s   .sq_lp
        move.l  d2,d0
        movem.l (sp)+,d1-d2
.sq_ret:
        rts

ste_inst_trap8:
        movem.l d3-d6/a3,-(sp)
        clr.w   STE_BIG_RAM
        ; HAGA overwrites $42e.w = $80000 and saves real top-$8000 in $608.w ($1f8000/$3f8000)!
        cmpi.l  #(STE_ARENA_END+4),$42e.w
        bge.s   .it8_probe
        cmpi.l  #(STE_ARENA_END+4),$608.w
        blt.w   .it8_done
.it8_probe:
        ; Belt-and-suspenders Bus-Error + anti-alias probe at STE_ARENA_END ($178000)
        move.w  sr,d3
        move.w  #$2700,sr
        move.l  $8.w,a2
        move.l  sp,a3
        lea     .it8_pfail(pc),a0
        move.l  a0,$8.w
        moveq   #0,d4
        move.l  STE_ARENA_END.l,d5
        move.l  (STE_ARENA_END-$100000).l,d6
        move.l  #$5a3c96e1,STE_ARENA_END.l
        nop
        cmpi.l  #$5a3c96e1,STE_ARENA_END.l
        bne.s   .it8_prest
        cmp.l   (STE_ARENA_END-$100000).l,d6
        bne.s   .it8_prest
        move.l  #$a5c3691e,STE_ARENA_END.l
        nop
        cmpi.l  #$a5c3691e,STE_ARENA_END.l
        bne.s   .it8_prest
        moveq   #1,d4
.it8_prest:
        move.l  d5,STE_ARENA_END.l
        bra.s   .it8_pdone
.it8_pfail:
        moveq   #0,d4
.it8_pdone:
        move.l  a3,sp
        move.l  a2,$8.w
        move.w  d3,sr
        tst.w   d4
        beq.w   .it8_done
        move.w  #1,STE_BIG_RAM
        move.l  #ste_trap8_handler,$a0.w
        move.l  $70.w,STE_ORIG_VBL
        move.l  #ste_vbl_irq,$70.w
        lea     DB_A(pc),a0
        move.l  #$0d0000,DB_RING(a0)    ; DB_A = $0d0000..$0e27ff (74 KB)
        move.l  #$10b640,DB_RLR(a0)     ; 256 x 4B fast radar restore ptrs -> $10ba40
        lea     DB_B(pc),a0
        move.l  #$0e2800,DB_RING(a0)    ; DB_B = $0e2800..$0f4fff (74 KB)
        move.l  #$10ba40,DB_RLR(a0)     ; 256 x 4B fast radar restore ptrs -> $10be40
        lea     DB_C(pc),a0
        move.l  #$0f5000,DB_RING(a0)    ; DB_C = $0f5000..$1077ff (74 KB)
        move.l  #$107800,DB_SAV(a0)     ; +$0000 (8 KB)
        move.l  #$109800,DB_HUDSAV(a0)  ; +$2000 (4 KB)
        move.l  #$10a800,DB_RPOOL(a0)   ; +$3000 (2 KB)
        move.l  #$10b000,DB_STK(a0)     ; +$3800 (512B)
        move.l  #$10be40,DB_RLR(a0)     ; 256 x 4B fast radar restore ptrs -> $10c240
        move.l  #$10b400,DB_RDR(a0)     ; +$3c00 (576B -> $10b640)
.it8_done:
        movem.l (sp)+,d3-d6/a3
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
        tst.l   STE_ORIG_VBL
        beq.s   .cl_novbl
        move.l  STE_ORIG_VBL(pc),$70.w
.cl_novbl:
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
        tst.w   STE_BIG_RAM
        beq.s   .lp_fail
        cmpi.l  #32288,d0
        bne.s   .lp_fail
        clr.w   STE_SHOW_IDX
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        clr.w   STE_VBL_SEQ
        clr.w   STE_HUD_TICK
        clr.w   STE_HUD_CCNT
        clr.w   STE_HUD_HVALID
        moveq   #-1,d1
        move.l  d1,STE_HUD_HASH
        clr.w   STE_SPR_CNT
        clr.w   STE_WALKOUT
        clr.l   STE_UL_DASH
        clr.w   STE_STATS_DIRTY
        bsr.s   ste_reset_bufs
        moveq   #4,d0                   ; cmd 4 = clear all 3 linear rings
        trap    #8
        bsr.w   ste_prebake_all_rad     ; 160 KB 5-scale radar (solid $ffff + masked!)
        bsr.w   ste_prebake_assets      ; 160 KB 640-sprite cache + 30 KB map32 + 5.3 KB DOT_XLUT!
        move.w  #1,STE_PITCH_OK
        rts
.lp_fail:
        clr.w   STE_PITCH_OK
        rts

ste_reset_bufs:
        lea     DB_A(pc),a0
        bsr.s   .rb_one
        lea     DB_B(pc),a0
        bsr.s   .rb_one
        lea     DB_C(pc),a0
.rb_one:
        move.w  #-999,DB_TX(a0)
        move.w  #-999,DB_TY(a0)
        clr.w   DB_SCNT(a0)
        clr.w   DB_RLCNT(a0)
        clr.w   DB_RDCNT(a0)
        move.l  DB_RING(a0),DB_START(a0)
        move.l  DB_RING(a0),DB_WRAP(a0)
        move.w  #RING_H,DB_WRAPY(a0)
        clr.w   DB_HSCR(a0)
        clr.w   DB_HUD_H1(a0)
        clr.w   DB_HUD_H2(a0)
        rts

; ---------------------------------------------------------------------------
; Audio: ste_load_samples / ste_play_sound / ste_play_sound_hi / ste_stop_sound
; ---------------------------------------------------------------------------
ste_load_samples:
        movem.l d0,-(sp)
        move.l  a5,d0
        addq.l  #1,d0
        and.l   #$fffffffe,d0
        movea.l d0,a5
        move.l  a5,-$1452(a4)
        move.l  a5,STE_SND_BASE         ; ko2_bridge.s loads AMIGASND.BIN directly here!
        adda.l  #$5a00,a5               ; reserve 23,040B inside KO2's $1c138 Malloc block
        clr.w   -$142a(a4)
        movem.l (sp)+,d0
        rts

ste_play_sound:
        tst.w   -$142a(a4)
        bne.s   ste_ps_rts
ste_play_sound_hi:
        tst.w   -$5eec(a4)
        bne.s   ste_ps_rts
        tst.l   STE_SND_BASE
        beq.s   ste_ps_rts
        clr.b   STE_SND_PEND
        clr.l   STE_SCRIPT_PTR
        move.l  a2,STE_SCRIPT_ST
        clr.w   STE_REPEAT_CNT
        move.w  #1,-$142a(a4)
        clr.b   STE_SND_STOP
        move.l  a2,STE_SCRIPT_PTR
        move.b  #1,STE_SND_PEND
ste_ps_rts:
        rts

ste_stop_sound:
        clr.b   STE_SND_PEND
        clr.l   STE_SCRIPT_PTR
        move.b  #1,STE_SND_STOP
        clr.w   -$142a(a4)
        rts

; ---------------------------------------------------------------------------
; VBL IRQ ($70.w) & VBL End ($018e0a): Lockstep Triple-Buffered Shifter Sync
; ---------------------------------------------------------------------------
ste_vbl_skip:
        movem.l d0-d1,-(sp)
        jmp     $018d6e.l

ste_vbl_irq:
        tst.w   STE_PITCH_OK
        beq.s   .vt_chain_fast
        tst.l   $0231c8.l               ; KO2 -$52e2(a4): KO2 VBL active?
        beq.s   .vt_stats_mark
        tst.w   $02356a.l               ; KO2 -$4f40(a4): Half-Time/Full-Time/Stats on $078000?
        bne.s   .vt_stats_mark
.vt_chain_fast:
        move.l  STE_ORIG_VBL(pc),-(sp)
        rts

.vt_stats_mark:
        clr.w   STE_SHOW_IDX
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        move.w  #1,STE_STATS_DIRTY
        clr.b   $fffffa1b.w
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        move.b  #$07,$ffff8205.w
        move.b  #$80,$ffff8207.w
        clr.b   $ffff8209.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        bra.s   .vt_chain_fast

ste_vbl_end:
        tst.w   STE_PITCH_OK
        beq.w   .ve_novid
        tst.w   $02356a.l               ; Half-Time/Full-Time/Stats active?
        bne.w   .ve_novid
        movem.l d0-d1/a0-a1,-(sp)
        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        bne.s   .ve_pal
        move.l  $0120.w,STE_ORIG_TB
.ve_pal:
        ; Load STE 12-bit Amiga pitch palette (0..7)
        lea     STE_PIT_PAL.l,a0
        lea     $ffff8240.w,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+

        ; 1. Apply HSCROLL/LINEWID for STE_PEND_IDX (the VBASE GSTMCU JUST latched at VSync!)
        move.w  STE_PEND_HSCR(pc),d0
        beq.s   .ve_bh0
        clr.b   $ffff820f.w
        move.b  d0,$ffff8265.w
        bra.s   .ve_b2
.ve_bh0:
        move.b  #4,$ffff820f.w
        clr.b   $ffff8265.w
.ve_b2:
        move.w  STE_PEND_IDX(pc),STE_DISP_IDX
        ; 2. Queue newest completed buffer (STE_SHOW_IDX) into VBASE ($8201/$03/$0d) ONLY!
        move.w  STE_SHOW_IDX(pc),d0
        move.w  d0,STE_PEND_IDX
        addq.w  #1,STE_VBL_SEQ          ; notify .pu_pick3 seqlock that (DISP, PEND) rotated!
        lsl.w   #6,d0                   ; * 64 (DB_SIZE)
        lea     DB_A(pc),a0
        adda.w  d0,a0
        move.w  DB_HSCR(a0),STE_PEND_HSCR
        move.l  DB_START(a0),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8201.w          ; VBASE HI
        move.w  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8203.w          ; VBASE MID
        move.b  d0,$ffff820d.w          ; VBASE LO (latched cleanly by GSTMCU at next VSync!)
        movem.l (sp)+,d0-d1/a0-a1
.ve_novid:
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
        movem.l d0-d4/a0-a1,-(sp)
        movea.l STE_SND_BASE(pc),a1
        move.l  a1,d0
        beq.w   .step_stop
        moveq   #8,d4
.next_cmd:
        subq.w  #1,d4
        blt.w   .step_stop
        movea.l STE_SCRIPT_PTR(pc),a0
        move.l  a0,d0
        beq.w   .step_stop
        addq.w  #1,STE_REPEAT_CNT
        blt.s   .keep_ptr
        addq.l  #2,STE_SCRIPT_PTR
.keep_ptr:
        move.w  (a0),d0
        beq.w   .step_stop
        blt.s   .cmd_neg
        cmpi.w  #200,d0
        bge.s   .cmd_pitch
        cmpi.w  #100,d0
        bge.s   .cmd_s_hi
        subq.w  #1,d0
        bra.s   .cmd_sample
.cmd_s_hi:
        subi.w  #101,d0
        bra.s   .cmd_sample
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
        subi.w  #200,d0
        move.b  d0,STE_SND_PITCH
        bra.s   .next_cmd
.cmd_sample:
        cmpi.w  #17,d0
        bcc.s   .next_cmd
        mulu.w  #12,d0
        lea     0(a1,d0.w),a0
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.w  (a0)+,d3
        cmpi.l  #16,d2
        ble.s   .step_ret
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
        clr.w   STE_REPEAT_CNT
        clr.w   $0284aa-$142a
.step_ret:
        movem.l (sp)+,d0-d4/a0-a1
.vbl_done:
        rts

; ---------------------------------------------------------------------------
; O(1) Direct-Indexed Sprite List Hooks ($01a32c/$01a3a0/$01a3f6/$01a426/$01a83e)
; Stores slot_idx (0..31) directly in 4(a3) of KO2's unused Classic-ST save struct!
; ---------------------------------------------------------------------------
ste_draw_id:
        cmpi.w  #640,d3
        bcc.s   .di_raw
        moveq   #0,d2
        move.w  d3,d2
        lsl.l   #8,d2                   ; * 256 (ZERO mulu!)
        lea     STE_SPR_CACHE.l,a1
        adda.l  d2,a1
        bra.s   ste_draw_spr_core
.di_raw:
        ext.l   d3
        add.w   d3,d3
        movea.l -$11f0(a4),a0
        move.w  0(a0,d3.w),d3
        movea.l -$1204(a4),a1
        adda.l  d3,a1

ste_draw_spr_core:
        ; Input: d0.w = x_scr, d1.w = y_scr, a1 = sprite slot, a3 = &entity+$b8 (4-byte ptr ONLY!)
        ; Stores (slot_idx + 1) in (a3).l (1..32 != 0) — NEVER touch 4(a3) ($bc(a5) is live KO2 data!)
        add.w   STE_CUR_WX(pc),d0       ; world_x (0..1279)
        add.w   STE_CUR_WY(pc),d1       ; world_y (0..1535)
        lea     STE_SPR_LIST.l,a0
        move.w  STE_SPR_CNT(pc),d4      ; current count (0..32)
        move.l  (a3),d2                 ; O(1) cached (slot_idx + 1), or 0 if inactive
        subq.l  #1,d2                   ; d2.w = 0..31 (or $ffff if was 0)
        cmp.w   d4,d2
        bcc.s   .dsc_add
        lsl.w   #4,d2
        adda.w  d2,a0
        cmpa.l  (a0),a3                 ; exact hit at cached slot?
        beq.s   .dsc_upd
        lea     STE_SPR_LIST.l,a0
.dsc_add:
        cmpi.w  #32,d4
        bcc.s   .dsc_ret
        moveq   #0,d2
        move.w  d4,d2
        addq.l  #1,d2
        move.l  d2,(a3)                 ; (a3) = slot_idx + 1 (1..32, non-zero!)
        move.w  d4,d2
        lsl.w   #4,d2
        adda.w  d2,a0
        move.l  a3,(a0)
        addq.w  #1,d4
        move.w  d4,STE_SPR_CNT          ; publish new count LAST!
        bra.s   .dsc_upd
.dsc_set1:
        move.l  #1,(a3)
.dsc_upd:
        move.l  a1,4(a0)
        move.w  d0,8(a0)                ; world_x
        move.w  d1,10(a0)               ; world_y
        bra.s   .dsc_out
.dsc_ret:
        move.l  #1,(a3)
.dsc_out:
        movem.l (sp)+,d0-d2/d4/d7/a0-a1/a3
        rts

ste_erase_spr:
        tst.l   (a3)                    ; fast O(1) skip for inactive/off-screen entities (28 cyc!)
        beq.s   .es_rts
        movem.l d0-d1/a0-a2,-(sp)
        move.l  (a3),d0                 ; O(1) cached (slot_idx + 1)
        clr.l   (a3)                    ; mark entity inactive in KO2
        subq.l  #1,d0                   ; slot_idx (0..31)
        cmp.w   STE_SPR_CNT(pc),d0
        bcc.s   .es_ret
        move.w  d0,d1
        lsl.w   #4,d1
        lea     STE_SPR_LIST.l,a0
        adda.w  d1,a0
        cmpa.l  (a0),a3
        bne.s   .es_ret
        move.w  STE_SPR_CNT(pc),d1
        subq.w  #1,d1
        move.w  d1,STE_SPR_CNT
        cmp.w   d0,d1                   ; already last slot?
        beq.s   .es_ret
        lsl.w   #4,d1
        lea     STE_SPR_LIST.l,a1
        adda.w  d1,a1                   ; a1 = last entry moving into slot d0
        movea.l (a1),a2
        tst.l   (a2)                    ; only update if swapped entity wasn't cleared directly!
        beq.s   .es_cp
        moveq   #0,d1
        move.w  d0,d1
        addq.l  #1,d1
        move.l  d1,(a2)                 ; update moved entity's (a2) = d0 + 1!
.es_cp: move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
.es_ret:
        movem.l (sp)+,d0-d1/a0-a2
.es_rts:
        rts

; ---------------------------------------------------------------------------
; ste_pitch_update ($01c1d0): User Camera Clamp -> ONE Supervisor Frame Render!
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

        ; 2. Compute clamped world camera (wx, wy) & write back to -$1112/-$110e (0px edge drift!)
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  -$1112(a4),d0
        addi.w  #176,d0
        bge.s   .wx_lo
        moveq   #0,d0
        move.l  #$ff500000,-$1112(a4)
        bra.s   .wx_ok
.wx_lo: cmpi.w  #960,d0
        ble.s   .wx_ok
        move.w  #960,d0
        move.l  #$03100000,-$1112(a4)
.wx_ok:
        move.w  -$110e(a4),d1
        addi.w  #64,d1
        bge.s   .wy_lo
        moveq   #0,d1
        move.l  #$ffc00000,-$110e(a4)
        bra.s   .wy_ok
.wy_lo: cmpi.w  #1336,d1
        ble.s   .wy_ok
        move.w  #1336,d1
        move.l  #$04f80000,-$110e(a4)
.wy_ok:
        move.w  d0,STE_CUR_WX
        move.w  d1,STE_CUR_WY

        ; Call KO2's off-screen goal arrow updater ($01bffa) in User mode BEFORE Backbuffer render!
        jsr     $01bffa.l

        ; Enter Supervisor mode ONCE (preserving IPL=0 so VBL/TC/IKBD fire freely!)
        ; for ALL Blitter + CPU backbuffer work — zero mid-frame TRAP #8 bouncing!
        moveq   #0,d0
        trap    #8
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; ---------------------------------------------------------------------------
; TRAP #8 ($a0.w): d0==0 -> Full Frame Render (ste_pu_sup), d0==4 -> Clear Rings
; ---------------------------------------------------------------------------
ste_trap8_handler:
        tst.w   d0
        bne.w   cmd4_clr

ste_pu_sup:
        move.l  sp,STE_SAV_ISP          ; isolate render + IRQ stack from KO2's tight $0282xx USP/ISP!
        lea     $10e000.l,sp
        ; Returning from Half-Time/Stats screen ($078000 was overwritten)? Reset cleanly!
        tst.w   STE_STATS_DIRTY
        beq.s   .pu_clean
        clr.w   STE_STATS_DIRTY
        clr.w   STE_SHOW_IDX
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        clr.w   STE_HUD_HVALID
        moveq   #-1,d0
        move.l  d0,STE_HUD_HASH
        bsr.w   ste_reset_bufs
        bsr.w   ste_clr_rings
.pu_clean:
        move.w  STE_CUR_WX(pc),d0
        move.w  STE_CUR_WY(pc),d1
        ; d2 = tx = wx >> 4 (0..60), d3 = ty = wy >> 4 (0..83), d7 = hscr = wx & 15
        move.w  d0,d2
        lsr.w   #4,d2
        move.w  d1,d3
        lsr.w   #4,d3
        move.w  d0,d7
        andi.w  #15,d7
        move.w  d7,STE_BK_HSCR

        ; Compute y0 = wy % 224 -> d4.w
        moveq   #0,d4
        move.w  d1,d4
        divu.w  #RING_H,d4
        swap    d4
        move.w  d4,STE_BK_Y0
        move.w  d2,d5
        lsl.w   #3,d5
        ext.l   d5
        move.l  d5,STE_BK_TX8

        ; Select INVISIBLE Triple-Buffered Backbuffer descriptor a6 (never DISP, PEND, or SHOW!)
.pu_pick3:
        move.w  STE_VBL_SEQ(pc),d0
        move.w  STE_DISP_IDX(pc),d1
        move.w  STE_PEND_IDX(pc),d4
        move.w  STE_SHOW_IDX(pc),d5
        cmp.w   STE_VBL_SEQ(pc),d0
        bne.s   .pu_pick3
        moveq   #0,d0
.pb_lp: cmp.w   d1,d0
        beq.s   .pb_nx
        cmp.w   d4,d0
        beq.s   .pb_nx
        cmp.w   d5,d0
        bne.s   .pb_got
.pb_nx: addq.w  #1,d0
        cmpi.w  #3,d0
        blt.s   .pb_lp
        bra.s   .pu_pick3               ; all 3 in use (CPU ahead of VBL) -> VSync pace!
.pb_got:
        move.w  d0,STE_BK_IDX
        lsl.w   #6,d0
        lea     DB_A(pc),a6
        adda.w  d0,a6

.pu_got_bk:
        ; === STEP A: Reverse-LIFO Erase of Backbuffer's Previous Frame ===
        bsr.w   ste_bk_erase_hud
        bsr.w   ste_bk_erase_spr
        bsr.w   ste_bk_erase_rad

        ; === STEP B: Update Backbuffer's Dirty Edge Tiles (14 rows x 21 cols + mirror) ===
        move.w  d2,d5
        sub.w   DB_TX(a6),d5            ; dtx
        move.w  d3,d6
        sub.w   DB_TY(a6),d6            ; dty
        move.w  d5,d0
        bpl.s   .adx
        neg.w   d0
.adx:   cmpi.w  #3,d0
        bgt.s   .bk_full
        move.w  d6,d0
        bpl.s   .ady
        neg.w   d0
.ady:   cmpi.w  #3,d0
        bgt.s   .bk_full

        tst.w   d5
        beq.s   .bk_chky
        bgt.s   .bk_sr
        move.w  d2,d0
.bk_sl: bsr.w   ste_bk_draw_col
        addq.w  #1,d0
        cmp.w   DB_TX(a6),d0
        blt.s   .bk_sl
        bra.s   .bk_chky
.bk_sr:
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
        move.w  d3,d0
.bk_su: bsr.w   ste_bk_draw_row
        addq.w  #1,d0
        cmp.w   DB_TY(a6),d0
        blt.s   .bk_su
        bra.s   .bk_tiles_ok
.bk_sd:
        move.w  DB_TY(a6),d0
        addi.w  #RING_ROWS,d0
        move.w  d3,d1
        addi.w  #(RING_ROWS-1),d1
.bk_sdl: bsr.w  ste_bk_draw_row
        addq.w  #1,d0
        cmp.w   d1,d0
        ble.s   .bk_sdl
        bra.s   .bk_tiles_ok

.bk_full:
        move.w  d3,d0
        moveq   #(RING_ROWS-1),d1
.bk_fy: bsr.w   ste_bk_draw_row
        addq.w  #1,d0
        dbra    d1,.bk_fy

.bk_tiles_ok:
        move.w  d2,DB_TX(a6)
        move.w  d3,DB_TY(a6)

        ; Precompute DB_WRAP = RING + tx*8 and DB_START = RING + y0*168 + tx*8
        move.l  DB_RING(a6),d0
        add.l   STE_BK_TX8(pc),d0
        move.l  d0,DB_WRAP(a6)
        move.w  STE_BK_Y0(pc),d1
        add.w   d1,d1
        lea     STE_Y168_TBL.l,a0
        moveq   #0,d4
        move.w  0(a0,d1.w),d4
        add.l   d0,d4
        move.l  d4,DB_START(a6)

        ; === STEP C: Transparent Vector Radar + 23 Dots + Active Player Underlines ===
        bsr.w   ste_bk_draw_rad
        bsr.w   ste_bk_draw_ul

        ; === STEP D: Batched Sprites + 3-Blit Pre-Interleaved Transparent Bottom HUD ===
        bsr.w   ste_bk_draw_spr
        bsr.w   ste_bk_draw_hud

        ; === STEP E: Atomic 1-Instruction Front <-> Back Publish + RTE to User Mode ===
        move.w  STE_BK_HSCR(pc),DB_HSCR(a6)
        move.w  STE_BK_IDX(pc),STE_SHOW_IDX
        addq.l  #1,STE_FRM_CNT
        movea.l STE_SAV_ISP(pc),sp
        rte

; Direct Supervisor Tile Strip Blits (ZERO TRAP #8!)
ste_bk_draw_row:
        cmpi.w  #96,d0
        bcc.s   .bdr_ret
        movem.l d0-d2/a0,-(sp)
        move.w  d2,d1                   ; d1 = tx_left
        move.w  d0,d2                   ; d2 = ty_row
        movea.l DB_RING(a6),a0
        bsr.w   cmd8_blit_row
        movem.l (sp)+,d0-d2/a0
.bdr_ret:
        rts

ste_bk_draw_col:
        cmpi.w  #80,d0
        bcc.s   .bdc_ret
        movem.l d0-d2/a0,-(sp)
        move.w  d0,d1                   ; d1 = tx_col
        move.w  d3,d2                   ; d2 = ty_top
        movea.l DB_RING(a6),a0
        bsr.w   cmd9_blit_col
        movem.l (sp)+,d0-d2/a0
.bdc_ret:
        rts

; ---------------------------------------------------------------------------
; Helper: ste_sy_ptr(d1.w=sy 0..199, d0.l=rel_x_byte_off, a6=DB) -> a0=ring ptr
; ---------------------------------------------------------------------------
ste_sy_ptr:
        add.w   d1,d1
        lea     STE_Y168_TBL.l,a0
        move.w  0(a0,d1.w),d1
        andi.l  #$ffff,d1
        add.l   d0,d1
        movea.l DB_START(a6),a0
        adda.l  d1,a0
        rts

; ---------------------------------------------------------------------------
; Step A.1: Direct Reverse-LIFO Blitter Restore of Backbuffer's Old HUD
; Each 16-byte record in DB_HUDSAV: [+0: dst.l, +4: sav.l, +8: xcnt4.w, +10: ycnt.w, +12: dst_yinc.w]
; ---------------------------------------------------------------------------
ste_bk_erase_hud:
        move.w  DB_HUD_H1(a6),d1
        beq.s   .beh_ret
        clr.w   DB_HUD_H1(a6)
        movem.l d0-d2/a0-a1,-(sp)
        movea.l DB_HUDSAV(a6),a0
        lsl.w   #4,d1
        adda.w  d1,a0                   ; end of d1 16-byte restore records
        lsr.w   #4,d1
        subq.w  #1,d1
        lea     BLT_SRC_ADDR.w,a1
        moveq   #-1,d0
        move.l  d0,4(a1)                ; ENDMASK1/2 = $ffffffff
        move.w  d0,8(a1)                ; ENDMASK3 = $ffff
        clr.b   25(a1)                  ; SKEW = 0
        move.w  #2,-4(a1)               ; SRC_XINC = 2
        move.w  #2,-2(a1)               ; SRC_YINC = 2
        move.w  #2,10(a1)               ; DST_XINC = 2
        move.w  #$0203,22(a1)           ; COPY
        moveq   #-$40,d2                ; $c0 HOG
.c7_lp:
        lea     -16(a0),a0
        move.l  4(a0),(a1)              ; SRC = sav
        move.l  (a0),14(a1)             ; DST = dst
        move.w  12(a0),12(a1)           ; DST_YINC = precomputed dst_yinc
        move.w  8(a0),18(a1)            ; XCOUNT = xcnt4
        move.w  10(a0),20(a1)           ; YCOUNT = ycnt
        move.b  d2,24(a1)               ; HOG blit!
        dbra    d1,.c7_lp
        movem.l (sp)+,d0-d2/a0-a1
.beh_ret:
        rts

; ---------------------------------------------------------------------------
; 64 KB 16-HSCR Pre-Interleaved 3-Blit 4bpp Transparent Bottom HUD ($168000..$177fff)
;   - ste_hud_scan packs 1bpp planes when STE_HUD_SRC changes & clears STE_HUD_HVALID.
;   - ste_hud_bake_hscr Blitter-shifts 1bpp planes into [INV_MASK4] + [PIXELS4] once per hscr.
;   - Every frame executes ONLY 3 SKEW=0 contiguous HOG blits per non-empty HUD box!
; ---------------------------------------------------------------------------
STE_HUD_PDATA   equ     STE_HUD_MASK+192 ; packed 1bpp planes ($07b0c0..$07bbff = 2,880B)

ste_hud_regions:
        dc.b    0,9,0,7                 ; Box 0: Top-Left (player/card)
        dc.b    10,16,0,7               ; Box 1: Top-Mid-Right (Home score)
        dc.b    17,19,0,7               ; Box 2: Top-Far-Right (Away score)
        dc.b    0,19,8,15               ; Box 3: Bottom-Mid (clock/status)

ste_hud_scan:
        movem.l d0-d7/a0-a5,-(sp)
        lea     STE_HUD_MASK.l,a2       ; 4 x 16B box headers
        lea     STE_HUD_PDATA.l,a4      ; packed 1bpp plane arena
        lea     ste_hud_regions(pc),a5
        clr.w   STE_HUD_CCNT
        clr.w   STE_HUD_HVALID          ; invalidate all 16 hscr 4bpp slots!
        moveq   #3,d7
.hs_reg:
        moveq   #0,d0
        move.b  (a5)+,d0                ; c0
        moveq   #0,d1
        move.b  (a5)+,d1                ; c1
        moveq   #0,d2
        move.b  (a5)+,d2                ; y0
        moveq   #0,d3
        move.b  (a5)+,d3                ; y1
        moveq   #99,d4                  ; min_c
        moveq   #-1,d5                  ; max_c
        move.w  #99,-(sp)               ; +2(sp) = min_y
        move.w  #-1,-(sp)               ; +0(sp) = max_y
        move.w  d2,d6
        lsl.w   #5,d2
        move.w  d2,d3
        add.w   d2,d2
        add.w   d2,d2
        add.w   d3,d2                   ; y0 * 160
        move.w  d0,d3
        lsl.w   #3,d3
        add.w   d3,d2
        lea     STE_HUD_SRC.l,a1
        adda.w  d2,a1
.hs_ylp:
        movea.l a1,a0
        move.w  d0,d2
.hs_xlp:
        move.l  (a0)+,d3
        or.w    (a0)+,d3
        addq.l  #2,a0
        tst.l   d3
        beq.s   .hs_nx
        cmp.w   d4,d2
        bge.s   .hs_mxc
        move.w  d2,d4
.hs_mxc:
        cmp.w   d5,d2
        ble.s   .hs_my
        move.w  d2,d5
.hs_my: cmp.w   2(sp),d6
        bge.s   .hs_mxy
        move.w  d6,2(sp)
.hs_mxy:
        cmp.w   (sp),d6
        ble.s   .hs_nx
        move.w  d6,(sp)
.hs_nx: addq.w  #1,d2
        cmp.w   d1,d2
        ble.s   .hs_xlp
        lea     160(a1),a1
        addq.w  #1,d6
        cmp.b   -1(a5),d6
        ble.s   .hs_ylp

        move.w  (sp)+,d6                ; max_y
        move.w  (sp)+,d2                ; min_y
        tst.w   d6
        bge.s   .hs_got
        clr.w   6(a2)
        lea     16(a2),a2
        bra.w   .hs_nr
.hs_got:
        sub.w   d2,d6
        addq.w  #1,d6                   ; d6 = h (1..8)
        move.w  d5,d1
        sub.w   d4,d1
        addq.w  #1,d1                   ; d1 = w_src (1..20)
        move.w  d1,d0
        addq.w  #1,d0                   ; d0 = w_buf = w_src + 1
        mulu.w  d6,d0
        add.w   d0,d0                   ; d0 = plane_sz = w_buf * h * 2
        move.l  d0,d3
        lsl.l   #2,d3
        add.l   a4,d3
        cmpi.l  #$07bc00,d3
        bhi.w   .hs_skip
        addq.w  #1,STE_HUD_CCNT
        addi.w  #HUD_SCR_Y,d2
        move.w  d2,(a2)+                ; +0: y_off (183..198)
        move.w  d4,d2
        lsl.w   #3,d2
        move.w  d2,(a2)+                ; +2: col8
        move.w  d1,(a2)+                ; +4: w_src
        move.w  d6,(a2)+                ; +6: h
        move.w  d5,(a2)+                ; +8: hi=flags(bit0=has_p2, bit1=has_p1), lo=max_c(0..19)
        move.w  d0,(a2)+                ; +10: plane_sz
        move.l  a4,(a2)+                ; +12: pdata

        movea.l a4,a0                   ; TOTMASK
        movea.l a4,a1
        adda.w  d0,a1                   ; SHAD
        lea     0(a1,d0.w),a3           ; P2
        move.l  d3,-(sp)
        move.l  a5,-(sp)
        move.w  d7,-(sp)
        lea     0(a3,d0.w),a4           ; P1
        move.w  -16(a2),d2
        subi.w  #HUD_SCR_Y,d2
        mulu.w  #160,d2
        add.w   -14(a2),d2
        lea     STE_HUD_SRC.l,a5
        adda.w  d2,a5
        move.w  d1,d2
        lsl.w   #3,d2
        move.w  #160,d3
        sub.w   d2,d3
        subq.w  #1,d6
.hp_y:  moveq   #0,d5
        move.w  -12(a2),d4
        subq.w  #1,d4
.hp_x:  move.w  (a5)+,d0
        move.w  (a5)+,d1
        beq.s   .hp_np1
        bset    #1,-8(a2)
.hp_np1:
        move.w  (a5)+,d2
        beq.s   .hp_np2
        bset    #0,-8(a2)
.hp_np2:
        addq.l  #2,a5
        move.w  d1,(a4)+
        move.w  d2,(a3)+
        or.w    d1,d0
        or.w    d2,d0
        move.w  d0,d7
        lsr.w   #1,d7
        or.w    d5,d7
        move.w  d0,d1
        not.w   d1
        and.w   d1,d7
        or.w    d7,d0
        move.w  d0,(a0)+
        move.w  d7,(a1)+
        moveq   #0,d5
        roxr.w  #1,d5
        dbra    d4,.hp_x
        move.w  d5,(a0)+
        move.w  d5,(a1)+
        clr.w   (a3)+
        clr.w   (a4)+
        adda.w  d3,a5
        dbra    d6,.hp_y
        move.w  (sp)+,d7
        movea.l (sp)+,a5
        movea.l (sp)+,a4
        bra.s   .hs_nr
.hs_skip:
        clr.w   6(a2)
        lea     16(a2),a2
.hs_nr: dbra    d7,.hs_reg
        movem.l (sp)+,d0-d7/a0-a5
        rts

STE_HUD_TMP_SY: dc.w    0
STE_HUD_TMP_E1: dc.w    0
STE_HUD_TMP_E3: dc.w    0
STE_HUD_TMP_SK: dc.b    0,0

; Direct Supervisor 1-Plane NFSR Transparent Bottom HUD (ZERO TRAP #8, skips zero planes!)
ste_bk_draw_hud:
        movem.l d0-d7/a0-a5,-(sp)
        move.w  STE_HUD_TICK(pc),d0
        addq.w  #1,STE_HUD_TICK
        andi.w  #7,d0
        bne.s   .bdh_go
        lea     (STE_HUD_SRC+2*160).l,a0
        moveq   #-1,d0
        bsr.s   .bh_hrow
        lea     (2*160)(a0),a0
        bsr.s   .bh_hrow
        lea     (4*160)(a0),a0
        bsr.s   .bh_hrow
        lea     (2*160)(a0),a0
        bsr.s   .bh_hrow
        cmp.l   STE_HUD_HASH(pc),d0
        beq.s   .bdh_go
        move.l  d0,STE_HUD_HASH
        bsr.w   ste_hud_scan
        bra.s   .bdh_go

.bh_hrow:
        moveq   #9,d3
.bh_hc: add.l   (a0)+,d0
        add.w   (a0)+,d0
        addq.l  #2,a0
        rol.l   #3,d0
        add.l   (a0)+,d0
        add.w   (a0)+,d0
        addq.l  #2,a0
        dbra    d3,.bh_hc
        rts

.bdh_go:
        clr.w   DB_HUD_H1(a6)
        tst.w   STE_HUD_CCNT
        beq.w   .bdh_done
        move.w  STE_BK_HSCR(pc),d5
        bne.s   .bdh_hsk
        moveq   #-1,d0
        move.w  d0,STE_HUD_TMP_E1
        move.w  d0,STE_HUD_TMP_E3
        clr.b   STE_HUD_TMP_SK
        bra.s   .bdh_hset
.bdh_hsk:
        moveq   #-1,d0
        lsr.w   d5,d0
        move.w  d0,STE_HUD_TMP_E1
        not.w   d0
        move.w  d0,STE_HUD_TMP_E3
        move.w  d5,d0
        ori.b   #$40,d0                 ; NFSR | hscr (reads xcnt-1 source words/row!)
        move.b  d0,STE_HUD_TMP_SK
.bdh_hset:
        lea     STE_HUD_MASK.l,a2       ; 4 x 16B tight 1bpp box headers
        movea.l DB_HUDSAV(a6),a3        ; 16B restore records [0..63]
        lea     96(a3),a4               ; save-under pixel pool cursor
        lea     BLT_SRC_ADDR.w,a0
        move.w  #-1,6(a0)               ; ENDMASK2 = $ffff (constant!)
        move.w  #2,-4(a0)               ; SRC_XINC = 2 (constant!)
        moveq   #-$40,d7                ; $c0 HOG
        moveq   #3,d6                   ; 4 boxes
.bdh_bx:
        move.w  6(a2),d4                ; d4 = h (0 = empty)
        beq.w   .bdh_nb
        move.w  4(a2),d3                ; w_src
        tst.w   d5
        bne.s   .bdh_bsk
        move.w  #2,STE_HUD_TMP_SY
        cmpi.b  #19,9(a2)
        beq.s   .bdh_bwok
        addq.w  #1,d3
        bra.s   .bdh_bwok
.bdh_bsk:
        addq.w  #1,d3
        move.w  #4,STE_HUD_TMP_SY
        cmpi.b  #19,9(a2)
        beq.s   .bdh_bwok
        addq.w  #1,d3
        move.w  #2,STE_HUD_TMP_SY
.bdh_bwok:
        ; d3 = xcnt (1..20), d4 = h (1..8)
        move.w  (a2),d0                 ; y_off (183..198)
        add.w   d0,d0
        lea     STE_Y168_TBL.l,a1
        move.w  0(a1,d0.w),d0
        andi.l  #$ffff,d0
        movea.w 2(a2),a1                ; col8 (0..152)
        add.l   a1,d0
        movea.l DB_START(a6),a1
        adda.l  d0,a1                   ; a1 = dst_top in Backbuffer ring!

        move.w  d3,d1
        lsl.w   #2,d1                   ; d1 = xcnt4 = xcnt * 4
        move.w  d1,d2
        add.w   d2,d2                   ; xcnt * 8
        neg.w   d2
        addi.w  #170,d2                 ; d2 = sav_yinc = 170 - xcnt*8!

        ; Write 16B restore record [dst.l, sav.l, xcnt4.w, ycnt.w, sav_yinc.w, 0.w]
        move.l  a1,(a3)+
        move.l  a4,(a3)+
        move.w  d1,(a3)+
        move.w  d4,(a3)+
        move.w  d2,(a3)+
        clr.w   (a3)+
        addq.w  #1,DB_HUD_H1(a6)

        ; 1. Save-under 4bpp rectangle (ring -> sav, SKEW=0)
        moveq   #-1,d0
        move.w  d0,4(a0)                ; ENDMASK1 = $ffff
        move.w  d0,8(a0)                ; ENDMASK3 = $ffff
        clr.b   25(a0)                  ; SKEW = 0
        move.w  d2,-2(a0)               ; SRC_YINC = sav_yinc
        move.w  #2,10(a0)               ; DST_XINC = 2
        move.w  #2,12(a0)               ; DST_YINC = 2
        move.w  d1,18(a0)               ; XCOUNT = xcnt4
        move.w  #$0203,22(a0)
        move.l  a1,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)

        move.w  d3,d0
        mulu.w  d4,d0
        lsl.l   #3,d0
        adda.l  d0,a4                   ; advance sav += xcnt * h * 8

        ; 2. Barrel-shift 1bpp planes directly onto ring (skips zero P2/P1 planes!)
        move.w  STE_HUD_TMP_E1(pc),4(a0)
        move.w  STE_HUD_TMP_E3(pc),8(a0)
        move.b  STE_HUD_TMP_SK(pc),25(a0)
        move.w  STE_HUD_TMP_SY(pc),-2(a0)
        move.w  #8,10(a0)               ; DST_XINC = 8
        addq.w  #6,d2                   ; d2 = (170 - xcnt*8) + 6 = 176 - xcnt*8!
        move.w  d2,12(a0)               ; DST_YINC = 176 - xcnt*8
        move.w  d3,18(a0)               ; XCOUNT = xcnt
        movea.l 12(a2),a5               ; TOTMASK
        ; AND ~TOTMASK onto P0, P1, P2 (3 planes, NOT 4!)
        move.w  #$0204,22(a0)
        move.l  a5,(a0)
        move.l  a1,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.l  a5,(a0)
        addq.l  #2,a1
        move.l  a1,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.l  a5,(a0)
        addq.l  #2,a1
        move.l  a1,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        ; OR TOTMASK -> P3 (+6), SHAD -> P0 (+0), optional P2_HOME -> P1 (+2), P1_AWAY -> P2 (+4)
        move.w  #$0207,22(a0)
        move.l  a5,(a0)
        addq.l  #2,a1                   ; a1 = dst_top + 6 (P3)
        move.l  a1,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        subq.l  #6,a1                   ; a1 = dst_top (P0)
        moveq   #0,d0
        move.w  10(a2),d0               ; plane_sz
        adda.l  d0,a5                   ; SHAD
        move.l  a5,(a0)
        move.l  a1,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        adda.l  d0,a5                   ; P2_HOME
        btst    #0,8(a2)
        beq.s   .bdh_np2
        move.l  a5,(a0)
        addq.l  #2,a1
        move.l  a1,14(a0)
        subq.l  #2,a1
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.bdh_np2:
        adda.l  d0,a5                   ; P1_AWAY
        btst    #1,8(a2)
        beq.s   .bdh_nb
        move.l  a5,(a0)
        addq.l  #4,a1
        move.l  a1,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.bdh_nb:
        lea     16(a2),a2
        dbra    d6,.bdh_bx
.bdh_done:
        movem.l (sp)+,d0-d7/a0-a5
        rts

; ---------------------------------------------------------------------------
; Step A.2: Direct Reverse-LIFO Blitter Sprite Restore (4w if 9(a0)!=0, else 8w)
; ---------------------------------------------------------------------------
ste_bk_erase_spr:
        move.w  DB_SCNT(a6),d1
        beq.w   .bes_ret
        clr.w   DB_SCNT(a6)
        movem.l d0-d2/a0-a2,-(sp)
        move.w  d1,d0
        lsl.w   #4,d0
        movea.l DB_STK(a6),a0
        adda.w  d0,a0                   ; end of Backbuffer's sprite restore stack
        move.w  d1,d0
        lsl.w   #8,d0
        ext.l   d0
        movea.l DB_SAV(a6),a1
        adda.l  d0,a1                   ; end of Backbuffer's save-under slots
        lea     BLT_SRC_ADDR.w,a2
        move.w  #2,-4(a2)               ; SRC_XINC = 2
        move.w  #2,-2(a2)               ; SRC_YINC = 2
        move.w  #2,10(a2)               ; DST_XINC = 2
        moveq   #-1,d0
        move.l  d0,4(a2)                ; ENDMASK1/2 = $ffffffff
        move.w  d0,8(a2)                ; ENDMASK3 = $ffff
        move.w  #$0203,22(a2)           ; COPY
        clr.b   25(a2)                  ; SKEW = 0
        moveq   #-$40,d2                ; $c0 HOG
        subq.w  #1,d1
.c2_blp:
        lea     -16(a0),a0
        lea     -256(a1),a1
        moveq   #0,d0
        move.b  8(a0),d0                ; h (1..16)
        beq.s   .c2_bsk
        tst.b   9(a0)                   ; is_4w (1 = 16px single col, 0 = 32px two cols)?
        beq.s   .c2_w8
        move.w  #(RING_STRIDE-6),12(a2)
        move.w  #4,18(a2)
        bra.s   .c2_go
.c2_w8: move.w  #(RING_STRIDE-14),12(a2)
        move.w  #8,18(a2)
.c2_go: move.l  a1,(a2)
        move.l  (a0),14(a2)
        move.w  d0,20(a2)
        move.b  d2,24(a2)
.c2_bsk:
        dbra    d1,.c2_blp
        movem.l (sp)+,d0-d2/a0-a2
.bes_ret:
        rts

; ---------------------------------------------------------------------------
; Step A.3: Reverse-LIFO CPU Restore of Radar Dots/UL + Unrolled Radar Words
; ---------------------------------------------------------------------------
ste_bk_erase_rad:
        movem.l d0-d1/a0-a2,-(sp)
        move.w  DB_RDCNT(a6),d0
        beq.s   .ber_nod
        clr.w   DB_RDCNT(a6)
        move.w  d0,d1
        lsl.w   #2,d0
        move.w  d0,a1
        add.w   d0,d0
        add.w   a1,d0                   ; d0 * 12 (ZERO mulu!)
        movea.l DB_RDR(a6),a0
        adda.w  d0,a0
        subq.w  #1,d1
.ber_dl:
        lea     -12(a0),a0
        movea.l (a0),a1
        move.l  4(a0),(a1)+
        move.l  8(a0),(a1)
        dbra    d1,.ber_dl
.ber_nod:
        move.w  DB_RLCNT(a6),d0
        beq.s   .ber_ret
        clr.w   DB_RLCNT(a6)
        movea.l DB_RLR(a6),a0
        movea.l DB_RPOOL(a6),a2
        move.w  d0,d1
        andi.w  #3,d1
        beq.s   .ber_f4
        subq.w  #1,d1
.ber_fr:
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        dbra    d1,.ber_fr
.ber_f4:
        lsr.w   #2,d0
        subq.w  #1,d0
        blt.s   .ber_ret
.ber_flp:
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        dbra    d0,.ber_flp
.ber_ret:
        movem.l (sp)+,d0-d1/a0-a2
        rts

; ---------------------------------------------------------------------------
; Step C: Split Solid-$ffff + Masked Radar Draw + DOT_X_LUT 23-Dot Drawer
; ---------------------------------------------------------------------------
ste_bk_draw_rad:
        move.w  -$0f82(a4),d0
        cmpi.w  #$0a,d0
        beq.s   .bdr_wo_on
        cmpi.w  #$0b,d0
        beq.s   .bdr_wo_on
        cmpi.w  #$01,d0
        bne.s   .bdr_wo_off
        tst.w   STE_WALKOUT
        bne.w   .bdr_done_ret
        bra.s   .bdr_chk_en
.bdr_wo_on:
        move.w  #1,STE_WALKOUT
        rts
.bdr_wo_off:
        clr.w   STE_WALKOUT
        cmpi.w  #$0d,d0
        beq.w   .bdr_done_ret
        cmpi.w  #$0e,d0
        beq.w   .bdr_done_ret
.bdr_chk_en:
        tst.w   -$0e10(a4)
        ble.w   .bdr_done_ret
        move.w  -$0e0a(a4),d6
        ble.w   .bdr_done_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        movea.l DB_RLR(a6),a2
        movea.l DB_RPOOL(a6),a5
        moveq   #0,d7
        lsr.w   #2,d6
        subq.w  #2,d6                   ; 8,12,16,20,24 -> 0..4
        cmpi.w  #5,d6
        bcc.w   .br_dots
        swap    d6
        clr.w   d6
        lsr.l   #1,d6                   ; scale_idx * $8000
        moveq   #0,d0
        move.w  STE_BK_HSCR(pc),d0
        lsl.l   #8,d0
        lsl.l   #3,d0                   ; hscr * 2048
        add.l   d6,d0
        lea     STE_RAD_BAKE.l,a3
        adda.l  d0,a3
        move.w  (a3)+,d0                ; solid_cnt ($ffff words)
        move.w  (a3)+,d1                ; mask_cnt (partial words)
        move.w  d0,d7
        add.w   d1,d7                   ; total words saved for ste_bk_erase_rad!
        beq.w   .br_dots

        ; 1. Solid $ffff horizontal radar words (2B delta only, ZERO RMW!)
        tst.w   d0
        beq.s   .br_ms_go
        movea.l DB_START(a6),a1
        move.l  #$ffff0000,d4
        move.l  #$0000ffff,d5
        move.w  d0,d6
        andi.w  #3,d6
        beq.s   .br_sf4
        subq.w  #1,d6
.br_srem:
        adda.w  (a3)+,a1
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        move.l  d4,(a1)
        move.l  d5,4(a1)
        dbra    d6,.br_srem
.br_sf4:
        lsr.w   #2,d0
        subq.w  #1,d0
        blt.s   .br_ms_go
.br_sflp:
        adda.w  (a3)+,a1
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        move.l  d4,(a1)
        move.l  d5,4(a1)
        adda.w  (a3)+,a1
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        move.l  d4,(a1)
        move.l  d5,4(a1)
        adda.w  (a3)+,a1
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        move.l  d4,(a1)
        move.l  d5,4(a1)
        adda.w  (a3)+,a1
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        move.l  d4,(a1)
        move.l  d5,4(a1)
        dbra    d0,.br_sflp

        ; 2. Masked radar words (endpoints & vertical dotted lines)
.br_ms_go:
        tst.w   d1
        beq.w   .br_dots
        movea.l DB_START(a6),a1
        move.w  d1,d6
        andi.w  #3,d6
        beq.s   .br_f4
        subq.w  #1,d6
.br_rem:
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        dbra    d6,.br_rem
.br_f4:
        lsr.w   #2,d1
        subq.w  #1,d1
        blt.s   .br_dots
.br_f0:
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        dbra    d1,.br_f0

.br_dots:
        move.w  d7,DB_RLCNT(a6)
        bsr.w   ste_bk_draw_dots
        movem.l (sp)+,d0-d7/a0-a3/a5
.bdr_done_ret:
        rts

; ---------------------------------------------------------------------------
; Pre-bake 640 Sprites (with max_1col_skew!), 32-bit Tilemap, & 336-entry DOT_XLUT
; ---------------------------------------------------------------------------
ste_prebake_assets:
        movem.l d0-d7/a0-a6,-(sp)
        movea.l (KO2_A4-$11f0).l,a4     ; 640-word sprite offset table
        movea.l (KO2_A4-$1204).l,a5     ; KO2 3bpp sprite sheet base
        lea     STE_SPR_CACHE.l,a6      ; 640 x 256B
        move.w  #639,d7
.pbs_sp:
        moveq   #0,d0
        move.w  (a4)+,d0
        lea     0(a5,d0.l),a1
        moveq   #0,d1                   ; y_skip (0..16)
        moveq   #15,d2
.pbs_tt:
        move.w  (a1),d0
        or.w    $28(a1),d0
        or.w    $50(a1),d0
        bne.s   .pbs_tf
        addq.w  #1,d1
        lea     $78(a1),a1
        dbra    d2,.pbs_tt
        clr.l   (a6)                    ; empty frame: y_skip=0, trimmed_h=0
        clr.l   4(a6)
        bra.s   .pbs_nx
.pbs_tf:
        move.w  d1,(a6)                 ; +0: y_skip.w
        lea     8(a6),a0                ; +8: contiguous [P0, P1, P2, MASK] rows
        moveq   #0,d1                   ; OR of all MASK rows (for max_1col_skew!)
        moveq   #0,d5                   ; flags: bit0=P0, bit1=P1, bit2=P2
        moveq   #0,d6                   ; row_idx (1..16)
        moveq   #0,d3                   ; trimmed_h (1..16)
.pbs_rw:
        addq.w  #1,d6
        move.w  (a1),d0
        beq.s   .pbs_p1
        bset    #0,d5
.pbs_p1:
        move.w  d0,(a0)+
        move.w  $28(a1),d4
        beq.s   .pbs_p2
        bset    #1,d5
.pbs_p2:
        move.w  d4,(a0)+
        or.w    d4,d0
        move.w  $50(a1),d4
        beq.s   .pbs_pm
        bset    #2,d5
.pbs_pm:
        move.w  d4,(a0)+
        or.w    d4,d0                   ; MASK = P0 | P1 | P2
        beq.s   .pbs_w3
        move.w  d6,d3
        or.w    d0,d1                   ; accumulate horizontal span across all active rows
.pbs_w3:
        move.w  d0,(a0)+
        lea     $78(a1),a1
        dbra    d2,.pbs_rw
        move.w  d3,2(a6)                ; +2: trimmed_h.w (1..16)
        move.w  d5,4(a6)                ; +4: flags.w
        ; Count trailing zero bits of d1.w (d1 != 0 guaranteed!) -> max_1col_skew (0..15)
        moveq   #0,d0
.pbs_tz:
        btst    d0,d1
        bne.s   .pbs_tzd
        addq.w  #1,d0
        bra.s   .pbs_tz
.pbs_tzd:
        move.w  d0,6(a6)                ; +6: max_1col_skew (skew <= this fits in 16px = 4w!)
.pbs_nx:
        lea     256(a6),a6
        dbra    d7,.pbs_sp

        ; Pre-expand 80x96 byte tilemap -> 7,680 32-bit tile addresses ($15e800..$165fff)
        lea     STE_PIT_MAP.l,a0
        lea     STE_PIT_TILES.l,a1
        lea     STE_MAP32.l,a2
        move.w  #7679,d1
.pbm_lp:
        moveq   #0,d0
        move.b  (a0)+,d0
        mulu.w  #96,d0
        lea     0(a1,d0.l),a3
        move.l  a3,(a2)+
        dbra    d1,.pbm_lp

        ; Pre-build 336 x 16B DOT_XLUT ($166000..$1674ff) for zero-shift 32-bit dot plotting!
        ; Entry layout: [+0: col_off.w, +2: $0000.w, +4: m.w, +6: m.w, +8: ~m.w, +10: ~m.w, +12: ~m.w, +14: $ffff.w]
        lea     STE_DOT_XLUT.l,a0
        moveq   #0,d0                   ; x_sh = 0..335
.pbd_lp:
        move.w  d0,d1
        andi.w  #$fff0,d1
        lsr.w   #1,d1                   ; col_byte_off = (x_sh >> 4) * 8
        move.w  d0,d2
        andi.w  #15,d2
        move.w  #$c000,d3
        lsr.w   d2,d3                   ; m = $c000 >> (x_sh & 15)
        move.w  d3,d4
        not.w   d4                      ; ~m
        move.w  d1,(a0)+                ; +0: col_off.w
        clr.w   (a0)+                   ; +2: $0000 -> 2(a0).l = [$0000 : m]
        move.w  d3,(a0)+                ; +4: m     -> 4(a0).l = [m : m]
        move.w  d3,(a0)+                ; +6: m
        move.w  d4,(a0)+                ; +8: ~m    -> 8(a0).l = [~m : ~m]
        move.w  d4,(a0)+                ; +10: ~m
        move.w  d4,(a0)+                ; +12: ~m   -> 12(a0).l = [~m : $ffff]
        move.w  #-1,(a0)+               ; +14: $ffff
        addq.w  #1,d0
        cmpi.w  #336,d0
        blt.s   .pbd_lp

        movem.l (sp)+,d0-d7/a0-a6
        rts

; Pre-bake ALL 5 radar zoom scales (8, 12, 16, 20, 24 -> 5 x 32 KB = 160 KB @ $10e800..$1367ff)
ste_prebake_all_rad:
        movem.l d0-d7/a0-a5,-(sp)
        lea     STE_RAD_BAKE.l,a2
        moveq   #8,d6
.pba_lp:
        moveq   #4,d4
        moveq   #4,d5
        bsr.s   ste_build_rad_cache
        bsr.w   ste_rad_bake_big
        adda.l  #$8000,a2
        addq.w  #4,d6
        cmpi.w  #24,d6
        ble.s   .pba_lp
        movem.l (sp)+,d0-d7/a0-a5
        rts

ste_build_rad_cache:
        movem.l d0-d3/d7/a0/a3,-(sp)
        lea     (KO2_A4-$4d78).l,a3
        lea     STE_RAD_CACHE.l,a0
        moveq   #0,d7
.rc_hl: move.w  (a3)+,d0
        blt.s   .rc_hd
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        ext.l   d0
        divs.w  d6,d0
        add.w   d4,d0
        move.w  d0,(a0)+
        ext.l   d1
        divs.w  d6,d1
        add.w   d5,d1
        move.w  d1,(a0)+
        ext.l   d2
        divs.w  d6,d2
        add.w   d4,d2
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
        add.w   d4,d0
        move.w  d0,(a0)+
        ext.l   d1
        divs.w  d6,d1
        add.w   d5,d1
        move.w  d1,(a0)+
        ext.l   d2
        divs.w  d6,d2
        add.w   d5,d2
        move.w  d2,(a0)+
        addq.w  #1,d7
        bra.s   .rc_vl
.rc_vd: move.w  d7,STE_RAD_C_VCNT
        movem.l (sp)+,d0-d3/d7/a0/a3
        rts

ste_rad_bake_big:
        movem.l d0-d7/a0-a5,-(sp)
        moveq   #0,d5                   ; hscr = 0..15
.rbk_hs:
        lea     $10c400.l,a0
        move.w  #2099,d0
.rbk_cl:
        clr.l   (a0)+
        dbra    d0,.rbk_cl
        lea     $10c400.l,a1
        lea     STE_RAD_CACHE.l,a3
        move.w  STE_RAD_C_HCNT(pc),d6
        beq.s   .rbk_vs
        subq.w  #1,d6
.rbk_hl:
        move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .rbk_hn
        add.w   d5,d0
        add.w   d5,d2
        mulu.w  #42,d1
        lea     0(a1,d1.l),a0
.rbk_hx:
        cmp.w   d2,d0
        bgt.s   .rbk_hn
        cmpi.w  #336,d0
        bcc.s   .rbk_hn
        move.w  d0,d3
        lsr.w   #4,d3
        add.w   d3,d3
        move.w  d0,d4
        not.w   d4
        andi.w  #15,d4
        move.w  0(a0,d3.w),d7
        bset    d4,d7
        move.w  d7,0(a0,d3.w)
        addq.w  #1,d0
        bra.s   .rbk_hx
.rbk_hn:
        dbra    d6,.rbk_hl
.rbk_vs:
        move.w  STE_RAD_C_VCNT(pc),d6
        beq.s   .rbk_pk
        subq.w  #1,d6
.rbk_vl:
        move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        cmpi.w  #320,d0
        bcc.s   .rbk_vn
        cmpi.w  #PITCH_VIS_H,d2
        bcs.s   .rbk_vy2
        move.w  #(PITCH_VIS_H-1),d2
.rbk_vy2:
        add.w   d5,d0
        move.w  d0,d3
        lsr.w   #4,d3
        add.w   d3,d3
        move.w  d0,d4
        not.w   d4
        andi.w  #15,d4
.rbk_vy:
        cmp.w   d2,d1
        bgt.s   .rbk_vn
        move.w  d1,d7
        mulu.w  #42,d7
        add.w   d3,d7
        move.w  0(a1,d7.l),d0
        bset    d4,d0
        move.w  d0,0(a1,d7.l)
        addq.w  #4,d1
        bra.s   .rbk_vy
.rbk_vn:
        dbra    d6,.rbk_vl

        ; Pack Pass 1 (solid $ffff words -> delta.w) + Pass 2 (masked words -> [delta.w, m.w, ~m.w, ~m.w])
.rbk_pk:
        moveq   #0,d0
        move.w  d5,d0
        lsl.l   #8,d0
        lsl.l   #3,d0                   ; hscr * 2048
        movea.l a2,a4
        adda.l  d0,a4
        movea.l a4,a5                   ; header [solid_cnt.w, mask_cnt.w]
        clr.l   (a4)+
        ; Pass 1: solid $ffff words
        movea.l a1,a0
        moveq   #0,d2                   ; prev_off = 0
        moveq   #0,d3                   ; rel_off = 0
        moveq   #0,d7                   ; total emitted (cap <= 254)
        move.w  #(194*21-1),d6
.rbk_p1:
        move.w  (a0)+,d0
        cmpi.w  #-1,d0
        bne.s   .rbk_p1n
        cmpi.w  #254,d7
        bcc.s   .rbk_p1d
        move.w  d3,d1
        sub.w   d2,d1
        move.w  d3,d2
        move.w  d1,(a4)+                ; 2-byte delta only!
        addq.w  #1,d7
.rbk_p1n:
        addq.w  #8,d3
        dbra    d6,.rbk_p1
.rbk_p1d:
        move.w  d7,(a5)                 ; +0: solid_cnt.w
        ; Pass 2: partial-mask words (0 < m < $ffff)
        movea.l a1,a0
        moveq   #0,d2                   ; reset prev_off = 0 (Pass 2 starts at DB_START!)
        moveq   #0,d3
        moveq   #0,d4                   ; mask_cnt
        move.w  #(194*21-1),d6
.rbk_p2:
        move.w  (a0)+,d0
        beq.s   .rbk_p2n
        cmpi.w  #-1,d0
        beq.s   .rbk_p2n
        cmpi.w  #254,d7
        bcc.s   .rbk_p2d
        move.w  d3,d1
        sub.w   d2,d1
        move.w  d3,d2
        move.w  d1,(a4)+                ; +0: delta.w
        move.w  d0,(a4)+                ; +2: m.w
        not.w   d0
        move.w  d0,(a4)+                ; +4: ~m.w
        move.w  d0,(a4)+                ; +6: ~m.w
        addq.w  #1,d7
        addq.w  #1,d4
.rbk_p2n:
        addq.w  #8,d3
        dbra    d6,.rbk_p2
.rbk_p2d:
        move.w  d4,2(a5)                ; +2: mask_cnt.w
        addq.w  #1,d5
        cmpi.w  #16,d5
        blt.w   .rbk_hs
        movem.l (sp)+,d0-d7/a0-a5
        rts

; ---------------------------------------------------------------------------
; Zero-Shift 32-Bit Register-Pipelined 23-Dot Drawer via STE_DOT_XLUT ($166000)
; ---------------------------------------------------------------------------
ste_bk_draw_dots:
        movem.l a1/a4,-(sp)
        movea.l DB_RDR(a6),a2
        lea     STE_Y168_TBL.l,a3
        moveq   #0,d7
        move.l  -$0e14(a4),-(sp)        ; +4(sp): ball_x.w | ball_y.w
        move.l  -$4fbc(a4),-(sp)        ; +0(sp): Away 11 players ptr
        movea.l -$5012(a4),a5           ; Home 11 players ptr
        movea.l DB_START(a6),a1
        move.w  STE_BK_HSCR(pc),d0
        lsl.w   #4,d0                   ; hscr * 16 (pre-offset into STE_DOT_XLUT!)
        lea     STE_DOT_XLUT.l,a4
        adda.w  d0,a4
        moveq   #10,d5
.bd2_hl:
        tst.w   $0c(a5)
        beq.s   .bd2_hn
        move.w  $20(a5),d0
        cmpi.w  #318,d0
        bcc.s   .bd2_hn
        move.w  $22(a5),d1
        cmpi.w  #194,d1
        bcc.s   .bd2_hn
        lsl.w   #4,d0
        lea     0(a4,d0.w),a0           ; 16B LUT entry for (x + hscr)
        add.w   d1,d1
        move.w  (a0),d0                 ; col_byte_off
        add.w   0(a3,d1.w),d0           ; + y * 168
        move.l  12(a0),d2               ; [~m : $ffff]
        move.l  2(a0),d3                ; [$0000 : m]
        lea     0(a1,d0.w),a0
        move.l  a0,(a2)+
        move.l  (a0)+,d0                ; [P0 : P1]
        move.l  (a0),d1                 ; [P2 : P3]
        move.l  d0,(a2)+
        move.l  d1,(a2)+
        and.l   d2,d0
        or.l    d3,d0
        and.l   d2,d1
        or.l    d3,d1
        move.l  d1,(a0)
        move.l  d0,-(a0)
        addq.w  #1,d7
.bd2_hn:
        lea     $186(a5),a5
        dbra    d5,.bd2_hl

        movea.l (sp)+,a5                ; Away 11 players ptr
        moveq   #10,d5
.bd2_al:
        tst.w   $0c(a5)
        beq.s   .bd2_an
        move.w  $20(a5),d0
        cmpi.w  #318,d0
        bcc.s   .bd2_an
        move.w  $22(a5),d1
        cmpi.w  #194,d1
        bcc.s   .bd2_an
        lsl.w   #4,d0
        lea     0(a4,d0.w),a0
        add.w   d1,d1
        move.w  (a0),d0
        add.w   0(a3,d1.w),d0
        move.l  8(a0),d2                ; [~m : ~m]
        move.l  4(a0),d3                ; [m : m]
        lea     0(a1,d0.w),a0
        move.l  a0,(a2)+
        move.l  (a0)+,d0
        move.l  (a0),d1
        move.l  d0,(a2)+
        move.l  d1,(a2)+
        and.l   d2,d0
        or.l    d3,d1
        move.l  d1,(a0)
        move.l  d0,-(a0)
        addq.w  #1,d7
.bd2_an:
        lea     $186(a5),a5
        dbra    d5,.bd2_al

        move.w  (sp)+,d0                ; ball_x
        move.w  (sp)+,d1                ; ball_y
        cmpi.w  #318,d0
        bcc.s   .bd2_dn
        cmpi.w  #194,d1
        bcc.s   .bd2_dn
        lsl.w   #4,d0
        lea     0(a4,d0.w),a0
        add.w   d1,d1
        move.w  (a0),d0
        add.w   0(a3,d1.w),d0
        move.l  8(a0),d2                ; [~m : ~m]
        move.l  12(a0),d3               ; [~m : $ffff]
        move.l  2(a0),d4                ; [$0000 : m]
        lea     0(a1,d0.w),a0
        move.l  a0,(a2)+
        move.l  (a0)+,d0
        move.l  (a0),d1
        move.l  d0,(a2)+
        move.l  d1,(a2)+
        and.l   d2,d0
        and.l   d3,d1
        or.l    d4,d1
        move.l  d1,(a0)
        move.l  d0,-(a0)
        addq.w  #1,d7
.bd2_dn:
        movem.l (sp)+,a1/a4
        move.w  d7,DB_RDCNT(a6)
        rts

; ---------------------------------------------------------------------------
; Active Controlled Player Black Underline (16x1 solid $ffff, target dashed $fc3f)
; ---------------------------------------------------------------------------
ste_bk_draw_ul:
        movem.l d0-d4/d7/a0/a2/a5,-(sp)
        move.w  DB_RDCNT(a6),d7
        move.w  d7,d0
        lsl.w   #2,d0
        move.w  d0,d1
        add.w   d0,d0
        add.w   d1,d0                   ; d7 * 12 (ZERO mulu!)
        movea.l DB_RDR(a6),a2
        adda.w  d0,a2
        lea     -$5012(a4),a0
        tst.l   $12(a0)
        beq.s   .ul_away
        movea.l $16(a0),a5
        move.w  #$ffff,d4
        bsr.s   .ul_one
.ul_away:
        lea     -$4fbc(a4),a0
        tst.l   $12(a0)
        beq.s   .ul_dash
        movea.l $16(a0),a5
        move.w  #$ffff,d4
        bsr.s   .ul_one
.ul_dash:
        move.l  STE_UL_DASH(pc),d0
        beq.s   .ul_done
        clr.l   STE_UL_DASH
        movea.l d0,a5
        move.w  #$fc3f,d4
        bsr.s   .ul_one
.ul_done:
        move.w  d7,DB_RDCNT(a6)
        movem.l (sp)+,d0-d4/d7/a0/a2/a5
        rts

.ul_one:
        tst.l   $b8(a5)
        beq.s   .ul_ret
        cmpi.w  #46,d7
        bcc.s   .ul_ret
        move.w  (a5),d0
        addi.w  #168,d0
        sub.w   STE_CUR_WX(pc),d0
        cmpi.w  #305,d0
        bcc.s   .ul_ret
        move.w  4(a5),d1
        addi.w  #72,d1
        sub.w   STE_CUR_WY(pc),d1
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .ul_ret
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2
        moveq   #0,d3
        move.w  d4,d3
        swap    d3
        lsr.l   d2,d3
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        bsr.w   ste_sy_ptr
        swap    d3
        tst.w   d3
        beq.s   .ul_w2
        bsr.s   .ul_put
.ul_w2: swap    d3
        tst.w   d3
        beq.s   .ul_ret
        addq.l  #8,a0
.ul_put:
        move.w  d3,d0
        not.w   d0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        or.w    d3,(a0)
        and.w   d0,2(a0)
        and.w   d0,4(a0)
        or.w    d3,6(a0)
.ul_ret:
        rts

; ---------------------------------------------------------------------------
; Step D: Direct Batched Sprites (X-trimmed 4w single-col + 8w two-col HOG Blitter!)
; ---------------------------------------------------------------------------
ste_bk_draw_spr:
        tst.w   STE_SPR_CNT
        beq.w   .bds_ret
        movem.l d0-d7/a0-a6,-(sp)
        lea     STE_SPR_LIST.l,a5       ; active sprite source list
        movea.l DB_STK(a6),a3           ; Backbuffer sprite draw/restore stack
        lea     STE_Y168_TBL.l,a4       ; keep y*168 LUT in a4 (ZERO bsr ste_sy_ptr!)
        moveq   #0,d6                   ; drawn count (0..31)
        moveq   #0,d7                   ; current slot index
.bds_lp:
        cmp.w   STE_SPR_CNT(pc),d7
        bcc.w   .bds_done
        movea.l (a5),a0                 ; KO2 save-record ptr (a3)
        tst.l   (a0)                    ; did KO2 clear (a3) directly?
        bne.s   .bds_alive
        ; Purge dead sprite slot in-place & maintain (a3) = slot_idx + 1!
        move.w  STE_SPR_CNT(pc),d0
        subq.w  #1,d0
        move.w  d0,STE_SPR_CNT
        cmp.w   d7,d0
        beq.w   .bds_done
        lsl.w   #4,d0
        lea     STE_SPR_LIST.l,a0
        adda.w  d0,a0
        movea.l (a0),a2
        tst.l   (a2)                    ; only update if swapped entity is still alive!
        beq.s   .bds_pcp
        moveq   #0,d0
        move.w  d7,d0
        addq.l  #1,d0
        move.l  d0,(a2)
.bds_pcp:
        movea.l a5,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        bra.s   .bds_lp
.bds_alive:
        move.w  10(a5),d1               ; world_y
        sub.w   STE_CUR_WY(pc),d1       ; scr_y
        blt.s   .bds_nxt
        cmpi.w  #PITCH_VIS_H,d1
        bge.s   .bds_nxt
        movea.l 4(a5),a2                ; pre-baked 256B sprite slot
        move.w  2(a2),d3                ; pre-baked trimmed_h (0..16)
        beq.s   .bds_nxt
        add.w   (a2),d1                 ; scr_y += pre-baked y_skip
        cmpi.w  #PITCH_VIS_H,d1
        bge.s   .bds_nxt
        move.w  #PITCH_VIS_H,d4
        sub.w   d1,d4
        cmp.w   d3,d4
        bge.s   .bds_hok
        move.w  d4,d3
.bds_hok:
        move.w  8(a5),d0                ; world_x
        move.w  d0,d2
        andi.w  #15,d2                  ; d2 = skew (0..15)
        lsr.w   #4,d0                   ; world_col (0..79)
        sub.w   DB_TX(a6),d0            ; rel_col
        blt.s   .bds_nxt
        moveq   #0,d5                   ; d5 = is_4w (1 if skew <= max_1col_skew!)
        cmp.w   6(a2),d2
        bhi.s   .bds_chk20
        moveq   #1,d5
.bds_chk20:
        cmpi.w  #20,d0
        bgt.s   .bds_nxt
        bne.s   .bds_xok
        tst.w   d5                      ; rel_col == 20: safe whenever sprite fits in 1 col!
        beq.s   .bds_nxt
.bds_xok:
        lsl.w   #3,d0                   ; rel_col * 8 (0..160)
        add.w   d1,d1
        add.w   0(a4,d1.w),d0           ; + scr_y * 168 (<= 33,592 -> unsigned 16-bit, <65536!)
        moveq   #0,d1
        move.w  d0,d1
        movea.l DB_START(a6),a0
        adda.l  d1,a0                   ; a0 = dst_top (inlined, ZERO bsr!)
        ; Push 16B record: [+0: dst.l, +4: 0.l, +8: h.b, +9: is_4w.b, +10: skew.w, +12: slot.l]
        move.l  a0,(a3)+
        clr.l   (a3)+
        move.b  d3,(a3)+
        move.b  d5,(a3)+
        move.w  d2,(a3)+
        move.l  a2,(a3)+
        addq.w  #1,d6
        cmpi.w  #32,d6
        bcc.s   .bds_done
.bds_nxt:
        lea     16(a5),a5
        addq.w  #1,d7
        bra.w   .bds_lp
.bds_done:
        move.w  d6,DB_SCNT(a6)
        beq.w   .bds_fin

        ; === Inline Direct Supervisor HOG Sprite Loop (ZERO TRAP #8!) ===
        movea.l DB_SAV(a6),a5           ; a5 = DB_SAV slot
        movea.l DB_STK(a6),a6           ; a6 = DB_STK cursor
        lea     BLT_SRC_ADDR.w,a0
        move.w  #-1,6(a0)               ; ENDMASK2 = $ffff (constant across all sprites!)
        moveq   #-$40,d7                ; $c0 HOG
        subq.w  #1,d6
.c3_bsp:
        movea.l 12(a6),a1               ; pre-baked 256B slot
        movea.l (a6),a4                 ; dst_top
        moveq   #0,d4
        move.b  8(a6),d4                ; trimmed h (1..16)
        move.w  4(a1),d2                ; flags: bit0=P0, bit1=P1, bit2=P2
        addq.l  #8,a1                   ; a1 -> [P0, P1, P2, MASK] rows
        lea     6(a1),a3                ; a3 -> MASK[0]

        ; Common Save-Under setup (ENDMASK1/3=$ffff, SKEW=0, SRC/DST_XINC=2, DST_YINC=2)
        moveq   #-1,d0
        move.w  d0,4(a0)
        move.w  d0,8(a0)
        clr.b   25(a0)
        move.w  #2,-4(a0)
        move.w  #2,10(a0)
        move.w  #2,12(a0)
        move.w  #$0203,22(a0)
        move.l  a4,(a0)
        move.l  a5,14(a0)
        move.w  d4,20(a0)
        move.w  10(a6),d1               ; skew (0..15)
        bne.s   .c3b_sk
        ; --- Path A: skew == 0 -> 3 blits total (4w save + 3w AND ~MASK + 4w OR)! ---
        move.w  #(RING_STRIDE-6),-2(a0)
        move.w  #4,18(a0)
        move.b  d7,24(a0)
        clr.w   -4(a0)
        move.w  #8,-2(a0)
        move.w  #3,18(a0)
        move.w  #(RING_STRIDE-4),12(a0)
        move.w  #$0204,22(a0)
        move.l  a3,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.w  #2,-4(a0)
        move.w  #2,-2(a0)
        move.w  #4,18(a0)
        move.w  #(RING_STRIDE-6),12(a0)
        move.w  #$0207,22(a0)
        move.l  a1,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        bra.w   .c3b_nx

.c3b_sk:
        tst.b   9(a6)                   ; Path B: 0 < skew <= max_1col_skew -> 1-col (4w)!
        beq.s   .c3b_s8
        move.w  #(RING_STRIDE-6),-2(a0) ; 4w save-under (50% fewer bus words!)
        move.w  #4,18(a0)
        move.b  d7,24(a0)
        lsr.w   d1,d0                   ; d0 = $ffff >> skew
        move.w  d0,4(a0)                ; ENDMASK1
        clr.w   -4(a0)                  ; SRC_XINC = 0
        move.w  #8,-2(a0)               ; SRC_YINC = 8
        move.w  #1,18(a0)               ; XCOUNT = 1 (single 16px column!)
        move.w  #RING_STRIDE,12(a0)     ; DST_YINC = 168
        move.b  d1,25(a0)               ; SKEW = skew (FXSR=0, NFSR=0)
        bra.s   .c3b_planes

.c3b_s8:
        ; --- Path C: 2-column skewed sprite (8w save + XCOUNT=2 NFSR) ---
        move.w  #(RING_STRIDE-14),-2(a0)
        move.w  #8,18(a0)
        move.b  d7,24(a0)
        lsr.w   d1,d0
        move.w  d0,4(a0)
        not.w   d0
        move.w  d0,8(a0)
        clr.w   -4(a0)
        move.w  #8,-2(a0)
        move.w  #2,18(a0)
        move.w  #8,10(a0)
        move.w  #(RING_STRIDE-8),12(a0)
        ori.b   #$40,d1
        move.b  d1,25(a0)

.c3b_planes:
        move.w  #$0204,22(a0)           ; AND ~MASK on P0, P1, P2
        move.l  a3,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.l  a3,(a0)
        lea     2(a4),a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.l  a3,(a0)
        addq.l  #2,a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.w  #$0207,22(a0)           ; OR MASK->P3, then ONLY non-empty P0/P1/P2!
        move.l  a3,(a0)
        addq.l  #2,a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        btst    #0,d2
        beq.s   .c3b_np0
        move.l  a1,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.c3b_np0:
        btst    #1,d2
        beq.s   .c3b_np1
        lea     2(a1),a2
        move.l  a2,(a0)
        lea     2(a4),a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.c3b_np1:
        btst    #2,d2
        beq.s   .c3b_nx
        lea     4(a1),a2
        move.l  a2,(a0)
        lea     4(a4),a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.c3b_nx:
        lea     16(a6),a6
        lea     256(a5),a5
        dbra    d6,.c3_bsp
.bds_fin:
        movem.l (sp)+,d0-d7/a0-a6
.bds_ret:
        rts

; ---------------------------------------------------------------------------
; Ring Clear & Pre-Baked 32-Bit Tile Strip Blits (Direct Supervisor Routines!)
; ---------------------------------------------------------------------------
ste_clr_rings:
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        clr.w   BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.w  #84,BLT_XCOUNT.w
        lea     DB_A(pc),a0
        moveq   #2,d0
.c4_blp:
        move.l  (a0),BLT_DST_ADDR.w
        move.w  #(2*RING_H+3),BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        lea     DB_SIZE(a0),a0
        dbra    d0,.c4_blp
        rts

cmd4_clr:
        movem.l d0/a0,-(sp)
        bsr.s   ste_clr_rings
        movem.l (sp)+,d0/a0
        rte

c89_setup:
        lea     BLT_SRC_ADDR.w,a4
        move.w  #2,-4(a4)               ; SRC_XINC = 2
        move.w  #2,-2(a4)               ; SRC_YINC = 2
        move.w  #2,10(a4)               ; DST_XINC = 2
        move.w  #(RING_STRIDE-4),12(a4) ; DST_YINC = 164
        moveq   #-1,d0
        move.l  d0,4(a4)                ; ENDMASK1/2 = $ffffffff
        move.w  d0,8(a4)                ; ENDMASK3 = $ffff
        move.w  #3,18(a4)               ; XCOUNT = 3 (3bpp tile, P3 already 0)
        move.w  #$0203,22(a4)
        clr.b   25(a4)
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lsl.l   #2,d0
        lea     STE_MAP32.l,a2
        adda.l  d0,a2                   ; a2 = &STE_MAP32[(ty*80 + tx)]!
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #RING_ROWS,d0
        swap    d0
        move.w  d0,d6
        lsl.w   #4,d0
        add.w   d0,d0
        lea     STE_Y168_TBL.l,a1
        move.w  0(a1,d0.w),d0
        andi.l  #$ffff,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        move.l  a0,d5
        add.l   d3,d5                   ; d5 = DB_RING + tx*8 (for cmd 9)
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        rts

cmd8_blit_row:
        movem.l d3-d7/a1-a4,-(sp)
        bsr.s   c89_setup
        moveq   #21,d7
        moveq   #80,d0
        sub.w   d1,d0
        ble.s   .c8_done
        cmp.w   d7,d0
        bge.s   .c8_cnt
        move.w  d0,d7
.c8_cnt:
        move.w  d7,d6                   ; n_tiles (1..21)
        move.l  a3,d5                   ; row strip start
        subq.w  #1,d7
        moveq   #16,d4
        moveq   #-$40,d3
.c8_blp:
        move.l  (a2)+,(a4)
        move.l  a3,14(a4)
        move.w  d4,20(a4)
        move.b  d3,24(a4)
        addq.l  #8,a3
        dbra    d7,.c8_blp
        ; Mirror entire 16-scanline strip to +RING_BYTES in ONE HOG blit!
        move.w  d6,d0
        lsl.w   #3,d0
        move.w  #170,d4
        sub.w   d0,d4                   ; 170 - n_tiles*8
        move.w  d4,-2(a4)
        move.w  d4,12(a4)
        lsl.w   #2,d6
        move.w  d6,18(a4)
        move.l  d5,(a4)
        addi.l  #RING_BYTES,d5
        move.l  d5,14(a4)
        move.w  #16,20(a4)
        move.b  d3,24(a4)
.c8_done:
        movem.l (sp)+,d3-d7/a1-a4
        rts

cmd9_blit_col:
        movem.l d3-d7/a1-a4,-(sp)
        bsr.w   c89_setup
        moveq   #RING_ROWS,d7
        moveq   #96,d0
        sub.w   d2,d0
        ble.s   .c9_done
        cmp.w   d7,d0
        bge.s   .c9_cnt
        move.w  d0,d7
.c9_cnt:
        subq.w  #1,d7
        moveq   #16,d4
        moveq   #-$40,d3
.c9_blp:
        move.l  (a2),(a4)
        adda.w  #320,a2
        move.l  a3,14(a4)
        move.w  d4,20(a4)
        move.b  d3,24(a4)
        addq.w  #1,d6
        cmpi.w  #RING_ROWS,d6
        blt.s   .c9_bst
        moveq   #0,d6
        suba.l  #(RING_BYTES-16*RING_STRIDE),a3
        bra.s   .c9_bnx
.c9_bst:
        adda.w  #(16*RING_STRIDE),a3
.c9_bnx:
        dbra    d7,.c9_blp
        move.w  #(RING_STRIDE-4),-2(a4)
        move.l  d5,(a4)
        addi.l  #RING_BYTES,d5
        move.l  d5,14(a4)
        move.w  #RING_H,20(a4)
        move.b  d3,24(a4)
.c9_done:
        movem.l (sp)+,d3-d7/a1-a4
        rts
