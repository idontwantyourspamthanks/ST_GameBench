; name: p7_skip_render
; default: yes
; site: $1dbbe
; orig: 203866e604800000 6400
; phase: deferred
; data: $b6000 5248
; note: P7 item 5(a), static-frame skip (work/notes/p7_static_skip.md).  Master renderer $1dbbe (reached by
;       `jsr $5056` at $315a4 and $325d8).  When nothing the 3D window depends on has changed since the image
;       that sits in the BACK buffer was drawn, return without drawing: the back buffer already holds the
;       identical picture (the window rows 58-199 are written only by the renderer, work/notes/p7_static_skip.md
;       section 3), the HUD, post-render calls and the flip run as before.
;       Per-buffer snapshot of the render inputs (SC = scalar words, OBJ = NPC/effect records, MK = marker
;       records) kept for buffer b = bit 16 of $67a6; VAL[b] = 1 when all three parts equal the inputs the
;       image in buffer b was drawn from.  Skip only when: caller is $315a8 (main loop), type $6220 = 13 and
;       $40b6 = 0, no HUD message timer active ($7590/$7582/$759c < 0), VAL[b] = 1, the stage of the SC words
;       equals SC[b], the wave phase is unchanged if the last render into b read the wave table, OBJ and MK
;       are unchanged, no effect record and no state-0 unit within 16 cells.  Everything else renders as
;       before and records what it drew.  A skip replays the one piece of render state the original carries
;       to the next frame ($1dcae-$1dcca: wave phase $1877c, pointer $1dfba) when the original would have.
;       Invalidated (VAL = 0) by: p7_skip_enter (3D view entry), p7_skip_gate ($1b6be), p7_skip_scn (scene
;       render from any caller but $1dbe2), another caller of $1dbbe, type/message conditions above.
;       Data block D = $b6000: VAL.w[2] +0, WV.w[2] +4, WP.l[2] +8, WAVE.w +$10, NSKIP.l +$14, NREND.l +$18,
;       NINV.l +$1c, WPTMP.l +$20, NUNS.l +$24, NSC.l +$28, NOBJ.l +$2c, NWAV.l +$30, SCNR.w[2] +$34, SCN.w +$38.
D       equ     $b6000
VAL     equ     D+$00
WV      equ     D+$04
WP      equ     D+$08
WAVE    equ     D+$10
NSKIP   equ     D+$14
NREND   equ     D+$18
NINV    equ     D+$1c
WPTMP   equ     D+$20
NUNS    equ     D+$24
NSC     equ     D+$28
NOBJ    equ     D+$2c
NWAV    equ     D+$30
SCNR    equ     D+$34
SCN     equ     D+$38
REPLAY  equ     $b7500
SCL     equ     104
SC0     equ     $b6040
SC1     equ     SC0+SCL
STG     equ     SC1+SCL
OBJ0    equ     $b6180
OBJL    equ     $480
OBJ1    equ     OBJ0+OBJL
MK0     equ     $b6a80
MKMAX   equ     80
MKL     equ     MKMAX*16
MK1     equ     MK0+MKL

        org     $1dbbe
        jmp     $b7510.l
        nop
        nop

        org     $b7500
        move.l  $66e6.w,d0              ; displaced
        subi.l  #$6400,d0               ; displaced
        jmp     $1dbc8.l

        org     $b7510
HK56:   cmpi.l  #$315a8,(a7)
        bne     .other
        cmpi.w  #13,$6220.w
        bne     .nofoot
        tst.w   $40b6.w
        bne     .nofoot
        tst.w   $7590.w
        bpl     .nofoot
        tst.w   $7582.w
        bpl     .nofoot
        tst.w   $759c.w
        bpl     .nofoot
        move.l  $67a6.w,d7
        swap    d7
        andi.w  #1,d7                   ; d7 = b
        move.w  d7,d6
        add.w   d6,d6                   ; d6 = 2b
        move.w  d6,d5
        add.w   d5,d5                   ; d5 = 4b
        lea     VAL.l,a6
        adda.w  d6,a6                   ; a6 -> VAL[b]
        lea     SC0.l,a4
        lea     OBJ0.l,a5
        lea     MK0.l,a3
        tst.w   d7
        beq.s   .bsel
        lea     SC1.l,a4
        lea     OBJ1.l,a5
        lea     MK1.l,a3
.bsel:  lea     STG.l,a2                ; stage the scalar inputs (104 bytes)
        move.w  $6220.w,(a2)+
        move.w  $66e0.w,(a2)+
        move.l  $66e6.w,(a2)+
        move.l  $66ea.w,(a2)+
        move.l  $670a.w,(a2)+
        move.w  $6f78.w,(a2)+
        move.w  $67be.w,(a2)+
        move.w  $6806.w,(a2)+           ; ($6808 is per-polygon scratch written by $1fa7c before it is read)
        clr.w   (a2)+                   ; pad to a long
        lea     $763e.w,a0
        rept    9
        move.l  (a0)+,(a2)+
        endr
        move.w  $17fc4.l,(a2)+
        move.w  $18768.l,(a2)+
        lea     $18556.l,a0
        rept    3
        move.l  (a0)+,(a2)+
        endr
        lea     $18772.l,a0
        rept    2
        move.l  (a0)+,(a2)+
        endr
        move.l  $18784.l,(a2)+
        move.w  $18788.l,(a2)+
        move.w  $18796.l,(a2)+
        move.l  $18798.l,(a2)+
        move.l  $53ac.w,(a2)+
        move.l  $53da.w,(a2)+
        lea     STG.l,a0
        movea.l a4,a1
        moveq   #SCL/4-1,d0
.c1:    cmpm.l  (a0)+,(a1)+
        dbne    d0,.c1
        bne     .scdiff
        tst.w   (a6)
        beq     .full
        lea     WV.l,a0
        tst.w   0(a0,d6.w)
        beq.s   .nowv
        lea     WP.l,a0
        move.l  $1dfba.l,d0
        cmp.l   0(a0,d5.w),d0
        bne     .wdiff
.nowv:  bsr     OBJPASS
        tst.w   d3
        bne     .unsup
        tst.w   d2
        bne     .objdiff
        bsr     MKCMP
        bne     .objdiff
        addq.l  #1,NSKIP.l              ; nothing changed: the back buffer is current
        lea     SCNR.l,a0
        tst.w   0(a0,d6.w)
        beq.s   .skipx
        addq.w  #8,$1877c.l             ; the original's $1dcae-$1dcca, as the render would have done
        andi.w  #$7e,$1877c.l
        lea     $18574.l,a0
        move.w  $1877c.l,d0
        adda.w  d0,a0
        move.l  a0,$1dfba.l
.skipx: rts
.scdiff:                                ; scalars changed: record them, drop the object parts
        lea     STG.l,a0
        movea.l a4,a1
        moveq   #SCL/4-1,d0
.c2:    move.l  (a0)+,(a1)+
        dbra    d0,.c2
        clr.w   (a6)
        addq.l  #1,NSC.l
        bra.s   .render
.full:  bsr     OBJPASS                 ; same scalars, parts not recorded yet: record them all
        bsr     MKCOPY
        tst.w   d3
        bne.s   .unsup
        move.w  #1,(a6)
        addq.l  #1,NOBJ.l
        bra.s   .render
.objdiff:
        bsr     MKCOPY
        tst.w   d3
        bne.s   .unsup
        addq.l  #1,NOBJ.l
        bra.s   .render
.wdiff: addq.l  #1,NWAV.l
        bra.s   .render
.unsup: clr.w   (a6)
        addq.l  #1,NUNS.l
.render:
        move.l  $1dfba.l,WPTMP.l
        clr.w   WAVE.l
        clr.w   SCN.l
        jsr     REPLAY.l
        move.l  $67a6.w,d6
        swap    d6
        andi.w  #1,d6
        add.w   d6,d6
        move.w  d6,d5
        add.w   d5,d5
        lea     WV.l,a0
        move.w  WAVE.l,0(a0,d6.w)
        lea     WP.l,a0
        move.l  WPTMP.l,0(a0,d5.w)
        lea     SCNR.l,a0
        move.w  SCN.l,0(a0,d6.w)
        addq.l  #1,NREND.l
        rts
.nofoot:
        clr.l   VAL.l
        addq.l  #1,NUNS.l
        jmp     REPLAY.l
.other: clr.l   VAL.l                   ; not the main loop's call: it draws into either buffer
        addq.l  #1,NINV.l
        jmp     REPLAY.l

; Window test and object record stage.  The record words are compared against OBJ[b] (a5) and written
; through.  Out: d2 <> 0 if anything differed, d3 <> 0 if an effect or a state-0 unit is within 16 cells.
; The three tables are the ones the marker pass reads ($20136 units, $201ac effects).
EMITD1  macro
        cmp.w   (a5),d1
        beq.s   .f\@
        moveq   #1,d2
.f\@:   move.w  d1,(a5)+
        endm
EMIT    macro
        move.w  \1(a0),d1
        EMITD1
        endm
OBJPASS:
        moveq   #0,d2
        moveq   #0,d3
        move.w  $66e0.w,d6
        ble     .bad                    ; zoom <= 0: window unknown, do not skip
        ext.l   d6
        asl.l   #4,d6                   ; 16 cells
        move.l  $66e6.w,d4
        move.l  $66ea.w,d5
        lea     $3532.w,a0
        moveq   #29,d0
.n:     move.w  $2e(a0),d1
        bmi     .ni
        EMITD1                          ; unit type
        move.l  6(a0),d1
        sub.l   d4,d1
        bpl.s   .nx
        neg.l   d1
.nx:    cmp.l   d6,d1
        bgt     .no
        move.l  $a(a0),d1
        sub.l   d5,d1
        bpl.s   .ny
        neg.l   d1
.ny:    cmp.l   d6,d1
        bgt     .no
        tst.w   $2e(a0)
        bne.s   .nin
        moveq   #1,d3                   ; state 0 (the $50a4 path) is not modelled
.nin:   move.w  #$7fff,d1
        EMITD1
        EMIT    0
        EMIT    2
        EMIT    4
        EMIT    6
        EMIT    8
        EMIT    $a
        EMIT    $c
        EMIT    $e
        EMIT    $16
        EMIT    $1a
        EMIT    $1c
        EMIT    $1e
        EMIT    $20
        EMIT    $2c
        EMIT    $34
        bra.s   .nn
.no:    move.w  #$7ffe,d1
        EMITD1
        bra.s   .nn
.ni:    EMITD1
.nn:    lea     $42(a0),a0
        dbra    d0,.n
        lea     $3cee.w,a0
        moveq   #29,d0
.f:     move.w  (a0),d1
        bmi.s   .fi
        EMITD1
        move.l  4(a0),d1
        sub.l   d4,d1
        bpl.s   .fx
        neg.l   d1
.fx:    cmp.l   d6,d1
        bgt.s   .fo
        move.l  $a(a0),d1
        sub.l   d5,d1
        bpl.s   .fy
        neg.l   d1
.fy:    cmp.l   d6,d1
        bgt.s   .fo
        moveq   #1,d3                   ; effect in the window: animated, not modelled
.fo:    move.w  #$7ffe,d1
        EMITD1
        bra.s   .fn
.fi:    EMITD1
.fn:    lea     $18(a0),a0
        dbra    d0,.f
        rts
.bad:   moveq   #1,d3
        rts

; Marker records: 16 bytes each from $4bfba, count = $6f78+1.  MKCMP: Z=1 if equal to MK[b] (a3).
MKCMP:  move.w  $6f78.w,d0
        bmi.s   .eq
        cmpi.w  #MKMAX-1,d0
        bgt.s   .ov
        lea     $4bfba.l,a0
        movea.l a3,a1
        addq.w  #1,d0
        asl.w   #2,d0
        subq.w  #1,d0
.l:     cmpm.l  (a0)+,(a1)+
        dbne    d0,.l
        rts
.ov:    moveq   #1,d3
        rts                             ; Z=0
.eq:    cmp.w   d0,d0
        rts
MKCOPY: move.w  $6f78.w,d0
        bmi.s   .z
        cmpi.w  #MKMAX-1,d0
        bgt.s   .ov
        lea     $4bfba.l,a0
        movea.l a3,a1
        addq.w  #1,d0
        asl.w   #2,d0
        subq.w  #1,d0
.l:     move.l  (a0)+,(a1)+
        dbra    d0,.l
.z:     rts
.ov:    moveq   #1,d3
        rts
