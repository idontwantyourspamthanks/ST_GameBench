; name: sky_vbl
; default: no
; site: $c5f0
; orig: 007c070048e7fff8
; requires: sky_fill sky_clr sky_fdst sky_ldst sky2_aciax sky_vblx
; note: The Amiga's sky and the lit panel, part 1 of 7: the VBL hook, the Timer B raster interrupts and all state (work/notes/visuals.md).
; note: The Amiga clears the 3D window to colour 15 and its copper list changes colour 15 five times above the horizon row and once at
; note: it (the sea), then reloads all 16 colours for the panel.  Here: sky_fill fills the window with solid colour 15 and records the
; note: horizon row of the page it filled; this hook (first thing in the VBL handler $c5f0) looks up the page the shifter shows
; note: ($ff8201/03) and programs MFP Timer B (event count = one count per display line) for up to 6 colour-15 changes plus one
; note: terminal interrupt at the first panel row (colour 15 back, or the whole panel palette when the landscape is darker than day).
; note: The game's palette writes are redirected to a shadow palette (sky_fdst, sky_ldst) that this hook copies to the shifter every VBL.
; note: Machines: 68000 only (ST, Mega ST, STE, Mega STE) and only if Timer B counts exactly 200 lines per frame; anywhere else
; note: (TT, Falcon) ST = $ff and all six sites behave like the original code.
; note: SKY_CFG (byte at SKY+28): bit0 sky bands + solid sea, bit1 dawn/dusk tint, bit2 lit panel.  SKY_ST (SKYV+1): 0 = not probed,
; note: 1..120 = counting lines, $7f = on, $ff = off.  SKY_SMASK (SKY+29): bit i = band i (0 = top .. 5 = the horizon/sea line) is
; note: written by a line-synchronous handler (exact, one line of CPU each) instead of a direct one (see visuals.md, jitter).
SKY     equ     $8f100                  ; code: window $8F100-$8F7FF
SKYV    equ     $8ecea                  ; state: window sky2_ $8ECEA-$8EFFF (reserved and zeroed by sky2_aciax's `data:` line)
CFGDEF  equ     5                       ; default options: sky + lit panel (tint off)
SMDEF   equ     $20                     ; default: only the horizon line is line-synchronous
MODE    equ     $13e                    ; (a5) screen mode set by $5eae: 3 = the 3D view (140-row window + 60-row panel)
LEVEL   equ     $18c                    ; (a5) current palette brightness 0..15 (fade $66ec)
AMBIENT equ     $18a                    ; (a5) brightness of the hour (table $c42a: 7 night .. 15 day)
MFP     equ     $fffffa00
IERA    equ     $07
IPRA    equ     $0b
ISRA    equ     $0f
IMRA    equ     $13
TBCR    equ     $1b
TBDR    equ     $21
ST_ON   equ     $7f
; offsets from SKYV
V_ST    equ     1
V_H     equ     2                       ; horizon row of the shown page, 0 = no sky on this frame
V_LH    equ     4                       ; horizon the raster list was built for
V_KEY   equ     6                       ; (level << 8) | (ambient << 4) | cfg the colours were computed for
V_C0    equ     8                       ; colour 15 at the top of the frame when a band starts at or above row 0
V_C0S   equ     10                      ; non-zero: the top colour is the palette's own colour 15
V_PNEED equ     11                      ; non-zero: the panel needs its own palette (terminal = sky_tbp)
V_DIRTY equ     12
V_C1    equ     13                      ; Timer B count to the first interrupt
V_C2    equ     14                      ; count from the first to the second
V_RR    equ     16                      ; round-robin slot offset (0, 8, 16, 24)
V_BASE  equ     18                      ; video base seen at the last VBL
V_VEC   equ     22                      ; first Timer B handler of the frame
V_SLOT  equ     26                      ; 4 x { page.l, horizon.w, fresh.w }
V_BAND  equ     58                      ; 6 band colours at the current level, hardware format
V_CNT   equ     70                      ; scratch: counts 1..8
V_SHAD  equ     80                      ; shadow of $ff8240..$ff825e (the landscape palette)
V_PPAL  equ     112                     ; the panel palette
V_SW    equ     144                     ; scratch: sync mask being shifted out
V_SF    equ     146                     ; scratch: this band wants a synchronous handler
V_YT    equ     147                     ; line count of the terminal interrupt (140, or 139 with the panel palette)
V_PALD  equ     148                     ; non-zero: the shifter must be reloaded from the shadow at the next VBL
V_LOW   equ     149                     ; non-zero: this VBL handler runs at IPL 5 with the IKBD masked in the MFP (sky_vblx undoes it)
V_END   equ     150

        org     $c5f0
        jmp     SKY.l                   ; replaces `ori.w #$700,sr / movem.l d0-d7/a0-a4,-(a7)`; returns to $c5f8
        nop

        org     $8f100
        bra.w   sky_vbl                 ; SKY+0   fixed entry points for the partner patches, 4 bytes each
        bra.w   sky_fill                ; SKY+4
        bra.w   sky_clr                 ; SKY+8
        bra.w   sky_fdst                ; SKY+12
        bra.w   sky_ldst                ; SKY+16
        bra.w   sky_aciax               ; SKY+20
        bra.w   sky_vblx                ; SKY+24
sky_cfg:
        dc.b    CFGDEF,SMDEF            ; SKY+28 options, SKY+29 line-synchronous bands

; ---- VBL hook -------------------------------------------------------------------------------------------------------
sky_vbl:
        ori.w   #$700,sr                ; the two original instructions
        movem.l d0-d7/a0-a4,-(sp)
        lea     SKYV.l,a4
        lea     MFP.w,a1
        move.b  V_ST(a4),d0
        bmi     .out                    ; off for good
        cmpi.b  #ST_ON,d0
        beq.s   .on
        tst.b   d0
        bne.s   .chk
        moveq   #1,d1                   ; 68000/68010 ignore the scale field of the extension word; a 68020+ does not
        lea     sky_cfg(pc),a0
        dc.w    $45f0,$1200             ; lea (a0,d1.w*2),a2
        suba.l  a0,a2
        cmpa.w  #1,a2
        bne.s   .off                    ; 68020+ (TT, Falcon, accelerators): leave everything original
.count: clr.b   TBCR(a1)                ; count the display lines of one frame: Timer B, event count mode, no interrupt
        move.b  #250,TBDR(a1)
        move.b  #8,TBCR(a1)
        addq.b  #1,V_ST(a4)
        bra     .out
.chk:   move.b  TBDR(a1),d1
        clr.b   TBCR(a1)
        cmpi.b  #50,d1                  ; 250 - 200 lines
        beq.s   .good
        cmpi.b  #120,d0                 ; a VBL can be late while a loader masks interrupts: try again for a while
        bcs.s   .count
.off:   st      V_ST(a4)
        bra     .out
.good:  movem.l $ffff8240.w,d0-d7       ; the shadow starts as what the shifter shows now (every palette writer of the game
        movem.l d0-d7,V_SHAD(a4)        ; runs inside this handler or at IPL 7: no write can be half done here)
        move.b  #ST_ON,V_ST(a4)
        move.w  #-1,V_KEY(a4)
        st      V_PALD(a4)
        bra     .out

.on:    tst.b   V_PALD(a4)              ; the game wrote the palette, or the panel palette was loaded last frame
        beq.s   .nocopy
        movem.l V_SHAD(a4),d0-d7        ; landscape palette for the top of the frame
        movem.l d0-d7,$ffff8240.w
        clr.b   V_PALD(a4)
.nocopy:
        moveq   #0,d0                   ; the page this frame shows (as the pointer code $a66c reads it)
        move.b  $ffff8201.w,d0
        swap    d0
        move.b  $ffff8203.w,d0
        lsl.w   #8,d0
        cmp.l   V_BASE(a4),d0
        beq.s   .same
        move.l  d0,V_BASE(a4)           ; a flip: the new page has a sky only if sky_fill filled it since it was last shown
        clr.w   V_H(a4)
        lea     V_SLOT(a4),a0
        moveq   #3,d1
.sl:    cmp.l   (a0),d0
        bne.s   .sn
        tst.w   6(a0)
        beq.s   .sn
        clr.w   6(a0)
        move.w  4(a0),V_H(a4)
.sn:    addq.l  #8,a0
        dbra    d1,.sl
.same:  cmpi.w  #3,MODE(a5)
        beq.s   .m3
        clr.w   V_H(a4)                 ; not the 3D view: no sky, and no page keeps a claim
        clr.w   V_SLOT+6(a4)
        clr.w   V_SLOT+14(a4)
        clr.w   V_SLOT+22(a4)
        clr.w   V_SLOT+30(a4)
.m3:    move.w  V_H(a4),d6
        beq     .out
        move.w  LEVEL(a5),d7
        moveq   #15,d5                  ; ambient level: 15 under a flare ($661c), else the hour's
        btst    #0,$9c(a5)
        bne.s   .amb
        move.w  AMBIENT(a5),d5
.amb:   move.w  d7,d0
        lsl.w   #4,d0
        or.w    d5,d0
        lsl.w   #4,d0
        or.b    sky_cfg(pc),d0
        cmp.w   V_KEY(a4),d0
        beq.s   .keyok
        move.w  d0,V_KEY(a4)
        st      V_DIRTY(a4)
        bsr     sky_colours
.keyok: cmp.w   V_LH(a4),d6
        bne.s   .build
        tst.b   V_DIRTY(a4)
        beq     .arm

; raster list: boundaries y = h-62, -30, -14, -6, -2, h (Amiga $62ca, table $62f8); the terminal interrupt comes last.
; R = the Timer B line count at which a handler is entered: y for a direct handler (end of row y-1), y-1 for a
; line-synchronous one (it waits for the end of row y-1 itself).
.build: move.w  d6,V_LH(a4)
        clr.b   V_DIRTY(a4)
        moveq   #140-256,d5             ; terminal: count 140 (colour 15 back) or 139 (panel palette, one line of lead)
        tst.b   V_PNEED(a4)
        beq.s   .yt
        subq.b  #1,d5
.yt:    move.b  d5,V_YT(a4)
        andi.w  #$ff,d5
        move.w  d5,d4
        subq.w  #1,d4                   ; last row a band may start on
        moveq   #0,d2                   ; previous R
        moveq   #0,d7                   ; number of band interrupts
        st      V_C0S(a4)
        moveq   #0,d0
        move.b  sky_cfg+1(pc),d0
        move.w  d0,V_SW(a4)
        lea     sky_dtab(pc),a1
        lea     V_BAND(a4),a2
        lea     sky_slot(pc),a0
        lea     V_CNT+1(a4),a3
        btst    #0,sky_cfg(pc)
        beq.s   .term
        moveq   #5,d1
.bl:    lsr.w   V_SW(a4)                ; C = this band is line-synchronous
        scs     V_SF(a4)
        move.w  d6,d0
        sub.w   (a1)+,d0                ; y
        move.w  (a2)+,d3
        tst.w   d0
        bgt.s   .pos
        move.w  d3,V_C0(a4)             ; starts above the window: it is the colour at the top
        clr.b   V_C0S(a4)
        bra.s   .nx
.pos:   cmp.w   d4,d0
        bgt.s   .term
        move.w  d3,SL_COL(a0)
        move.w  d3,SL_COL2(a0)
        move.l  a0,d5                   ; entry: the direct handler of this slot
        tst.b   V_SF(a4)
        beq.s   .dir
        cmpi.w  #2,d0
        bcs.s   .dir
        moveq   #SL_SYNC,d3
        add.l   d3,d5                   ; entry: the synchronous handler
        subq.w  #1,d0
.dir:   move.b  d0,d3
        sub.b   d2,d3
        move.b  d3,(a3)+                ; lines from the previous handler
        move.w  d0,d2
        tst.w   d7
        bne.s   .lk
        move.l  d5,V_VEC(a4)
        bra.s   .lk2
.lk:    move.l  d5,SL_NXT-SL_LEN(a0)    ; the previous slot chains to this entry
        move.l  d5,SL_NXT2-SL_LEN(a0)
.lk2:   lea     SL_LEN(a0),a0
        addq.w  #1,d7
.nx:    dbra    d1,.bl
.term:  move.b  V_YT(a4),d0
        sub.b   d2,d0
        move.b  d0,(a3)+                ; lines to the terminal interrupt (>= 1)
        st      (a3)                    ; reload after the terminal: 255, never reached
        lea     sky_tbe(pc),a2
        tst.b   V_PNEED(a4)
        beq.s   .t1
        lea     sky_tbp(pc),a2
.t1:    tst.w   d7
        bne.s   .t2
        move.l  a2,V_VEC(a4)
        bra.s   .cnt
.t2:    move.l  a2,SL_NXT-SL_LEN(a0)    ; the last band chains to the terminal
        move.l  a2,SL_NXT2-SL_LEN(a0)
        lea     sky_slot(pc),a0
        lea     V_CNT+3(a4),a3          ; slot j carries count j+2 (Timer B reloads from its data latch at each underflow)
        subq.w  #1,d7
.cl:    move.b  (a3),SL_CNT(a0)
        move.b  (a3)+,SL_CNT2(a0)
        lea     SL_LEN(a0),a0
        dbra    d7,.cl
.cnt:   move.b  V_CNT+1(a4),V_C1(a4)
        move.b  V_CNT+2(a4),V_C2(a4)

.arm:   lea     MFP.w,a1                ; (the list builder used a1)
        clr.b   TBCR(a1)
        move.w  V_SHAD+30(a4),d0
        lea     sky_tbe(pc),a0
        move.w  d0,2(a0)                ; the palette's colour 15 for the panel rows
        tst.b   V_C0S(a4)
        bne.s   .c0
        move.w  V_C0(a4),d0
.c0:    move.w  d0,$ffff825e.w
        lea     sky_acia(pc),a0
        move.l  a0,$118.w               ; IKBD handler at IPL 5 so that Timer B (higher MFP priority) can interrupt it
        bset    #0,IERA(a1)
        bset    #0,IMRA(a1)
        move.b  #$fe,IPRA(a1)           ; no stale request
        move.l  V_VEC(a4),$120.w
        move.b  V_C1(a4),TBDR(a1)       ; timer stopped: loads the counter
        move.b  #8,TBCR(a1)             ; event count: one count at the end of each display line
        move.b  V_C2(a4),TBDR(a1)       ; running: goes to the latch, used at the first underflow
        move.b  V_PNEED(a4),d0          ; the panel palette will be in the shifter at the next VBL
        or.b    d0,V_PALD(a4)
        st      V_LOW(a4)               ; the rest of the handler (world block, DMA mixer: up to 30 000 cycles) can be
        bclr    #6,$15(a1)              ; interrupted by Timer B only: the IKBD stays masked (IMRB bit 6) as under IPL 7,
        move.w  #$2500,sr               ; and the VBL (level 4) cannot re-enter.  sky_vblx restores both before the rte.
.out:   jmp     $c5f8.l

sky_dtab:
        dc.w    62,30,14,6,2,0
; band colours as on the Amiga (copper list $5dd8: $118 $22a $33a $44c $55f, sea $136), then the tinted sets for
; ambient 13-14, 11-12 and 9-10 (dusk and dawn; CFG bit1)
sky_base:
        dc.w    $118,$22a,$33a,$44c,$55f,$136
        dc.w    $118,$22a,$439,$757,$a86,$136
        dc.w    $117,$328,$637,$955,$d83,$235
        dc.w    $116,$326,$625,$943,$c62,$124
sky_ptab:
        dc.b    0,2,4,6,9,11,13,15      ; panel level while the picture is faded below night level (7)

; d7 = level, d5 = ambient: the six band colours and, if wanted, the panel palette
sky_colours:
        movem.l d5-d7,-(sp)
        lea     sky_base(pc),a0
        btst    #1,sky_cfg(pc)
        beq.s   .r0
        cmpi.w  #9,d5
        bcs.s   .r0
        cmpi.w  #15,d5
        bcc.s   .r0
        moveq   #16,d0
        sub.w   d5,d0
        lsr.w   #1,d0                   ; 13,14 -> 1; 11,12 -> 2; 9,10 -> 3
        mulu.w  #12,d0
        adda.w  d0,a0
.r0:    lea     V_BAND(a4),a2
        move.w  d7,d3
        moveq   #5,d6
.b:     move.w  (a0)+,d0
        bsr.s   sky_scale
        move.w  d2,(a2)+
        dbra    d6,.b
        moveq   #15,d3
        cmpi.w  #7,d7
        bcc.s   .p
        move.b  sky_ptab(pc,d7.w),d3
.p:     clr.b   V_PNEED(a4)
        btst    #2,sky_cfg(pc)
        beq.s   .x
        cmp.w   d7,d3
        beq.s   .x
        st      V_PNEED(a4)
        lea     $602a.l,a0              ; the current base palette (16 Amiga words; $6210 copies the mode's palette here)
        lea     V_PPAL(a4),a2
        moveq   #15,d6
.pp:    move.w  (a0)+,d0
        bsr.s   sky_scale
        move.w  d2,(a2)+
        dbra    d6,.pp
.x:     movem.l (sp)+,d5-d7
        rts

; d0 = $0RGB (Amiga), d3 = level: each gun * level / 16 as the fade does, then the game's own packing ($67fc: ST form,
; or the STE form when pal_fade is installed).  Result d2.w.  Uses d0-d2/d4.
sky_scale:
        moveq   #0,d2
        moveq   #2,d4
.l:     move.w  d0,d1
        andi.w  #$f,d1
        mulu.w  d3,d1
        andi.w  #$f0,d1
        ror.w   #4,d2
        or.b    d1,d2
        lsr.w   #4,d0
        dbra    d4,.l
        jmp     $67fc.l

; ---- Timer B handlers (MFP level 6; the MFP runs in software end-of-interrupt mode, $a9f4) -----------------------------
; One slot per band, two handlers in each.
; Direct: the colour write is the first instruction (about 60 cycles after the interrupt is taken); it lands in the
; horizontal blank unless the interrupted instruction was a divide (then a few pixels of one row are a line late).
; Synchronous: entered one line early, waits for the counter to move (end of the row above the boundary), then writes.
; Both then leave the count for the interrupt after the next in Timer B's latch and install the next handler.
SLOT    macro
        move.w  #0,$ffff825e.w          ; +0  direct
        move.b  #0,(MFP+TBDR).w         ; +6
        move.l  #0,$120.w               ; +12
        move.b  #$fe,(MFP+ISRA).w       ; +20
        rte                             ; +26
        move.b  #0,(MFP+TBDR).w         ; +28 synchronous
        move.l  #0,$120.w               ; +34
        move.w  d0,-(sp)                ; +42
        move.b  (MFP+TBDR).w,d0         ; +44
        cmp.b   (MFP+TBDR).w,d0         ; +48
        beq.s   *-4                     ; +52
        move.w  #0,$ffff825e.w          ; +54
        move.w  (sp)+,d0                ; +60
        move.b  #$fe,(MFP+ISRA).w       ; +62
        rte                             ; +68
        endm
SL_COL  equ     2
SL_CNT  equ     9
SL_NXT  equ     14
SL_SYNC equ     28
SL_CNT2 equ     31
SL_NXT2 equ     36
SL_COL2 equ     56
SL_LEN  equ     70
sky_slot:
        SLOT
        SLOT
        SLOT
        SLOT
        SLOT
        SLOT

; terminal, landscape and panel share the palette: colour 15 back to the palette's own at the first panel row
sky_tbe:
        move.w  #0,$ffff825e.w
        clr.b   (MFP+TBCR).w
        move.b  #$fe,(MFP+ISRA).w
        rte

; terminal, panel with its own palette: taken at the end of row 138, waits for the end of row 139 (the counter moves),
; then writes all 16 colours inside that horizontal blank
sky_tbp:
        movem.l d0-d7/a0-a1,-(sp)
        movem.l SKYV+V_PPAL.l,d1-d7/a1
        lea     (MFP+TBDR).w,a0
        move.b  (a0),d0
.w:     cmp.b   (a0),d0
        beq.s   .w
        movem.l d1-d7/a1,$ffff8240.w
        clr.b   (MFP+TBCR).w
        movem.l (sp)+,d0-d7/a0-a1
        move.b  #$fe,(MFP+ISRA).w
        rte

; IKBD/ACIA interrupt: vector $118 points here while the sky is armed.  Same register frame as the game's `movem.l
; d0-d7/a0-a4,-(a7)` at $afde, pushed in two halves at IPL 5, so Timer B waits at most one 72-cycle instruction.
sky_vblx:
        bclr    #7,$8f(a5)              ; the original instruction at $c61c
        tst.b   SKYV+V_LOW.l
        beq.s   .o
        ori.w   #$700,sr
        clr.b   SKYV+V_LOW.l
        bset    #6,(MFP+$15).w
.o:     jmp     $c622.l                 ; `movem.l (a7)+,d0-d7/a0-a4 / rte`

sky_acia:
        move.w  #$2500,sr
        movem.l a0-a4,-(sp)
        movem.l d0-d7,-(sp)
        jmp     $afe2.l
; jmp from $b004 (sky_aciax): the handler's exit `movem.l (a7)+,d0-d7/a0-a4 / rte`, also in two halves
sky_aciax:
        movem.l (sp)+,d0-d7
        movem.l (sp)+,a0-a4
        rte

; ---- sky_fill: jmp from $c84a ------------------------------------------------------------------------------------------
sky_fill:
        movea.l $144(a5),a4             ; the two original instructions
        adda.l  $1a2(a5),a4
        lea     SKYV.l,a0
        cmpi.b  #ST_ON,V_ST(a0)
        bne.s   .orig
        moveq   #5,d0
        and.b   sky_cfg(pc),d0
        beq.s   .orig
        cmpi.w  #3,MODE(a5)
        bne.s   .orig
        move.w  $1544(a5),d4            ; horizon row
        ble.s   .orig
        cmpi.w  #139,d4
        bgt.s   .orig
        move.l  $144(a5),d1
        cmp.l   $7fac.l,d1              ; the background template of the $481c loop: not a screen page
        beq.s   .orig
        lea     V_SLOT(a0),a1
        moveq   #3,d2
.f:     cmp.l   (a1),d1
        beq.s   .hit
        addq.l  #8,a1
        dbra    d2,.f
        move.w  V_RR(a0),d2
        addq.w  #8,d2
        andi.w  #$18,d2
        move.w  d2,V_RR(a0)
        lea     V_SLOT(a0,d2.w),a1
        clr.w   6(a1)
        move.l  d1,(a1)
.hit:   move.w  d4,4(a1)
        move.w  #1,6(a1)                ; fresh: the page gets its sky when the shifter shows it
        btst    #0,d0
        beq.s   .orig                   ; panel only: the original dithered fill
        moveq   #-1,d0                  ; 140 rows of solid colour 15, as the Amiga's blitter fill ($ca96)
        move.w  #$8b,d4
        jmp     $c8d0.l
.orig:  jmp     $c852.l

; ---- sky_clr: jsr from $c8c2 (the page clear $c8bc/$c8c0): the draw page loses its sky ---------------------------------
sky_clr:
        move.l  $144(a5),d1
        lea     SKYV.l,a0
        lea     V_SLOT(a0),a1
        moveq   #3,d4
.l:     cmp.l   (a1),d1
        bne.s   .n
        clr.w   6(a1)
.n:     addq.l  #8,a1
        dbra    d4,.l
        cmp.l   V_BASE(a0),d1
        bne.s   .x
        clr.w   V_H(a0)                 ; it is the page on screen (single-buffer screens draw there)
.x:     move.w  $38(a5),d4              ; the two original instructions
        subq.w  #1,d4
        rts

; ---- sky_fdst / sky_ldst: jsr from $6790 / $61fa: where the game's palette writes go -----------------------------------
sky_fdst:
        lea     $240(a6),a1             ; original
        move.b  SKYV+V_ST.l,d7
        cmpi.b  #ST_ON,d7
        bne.s   .x
        st      SKYV+V_PALD.l
        lea     SKYV+V_SHAD.l,a1
.x:     move.l  $180(a5),d7             ; original
        rts
sky_ldst:
        lea     $240(a6),a1             ; original
        move.b  SKYV+V_ST.l,d0
        cmpi.b  #ST_ON,d0
        bne.s   .x
        st      SKYV+V_PALD.l
        lea     SKYV+V_SHAD.l,a1
.x:     moveq   #$f,d0                  ; original
        rts
