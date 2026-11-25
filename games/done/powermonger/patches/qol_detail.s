; name: qol_detail
; default: yes
; stage: 2
; site: $1168c
; orig: 2c0adc8b2e06
; data: $dc300 16
; note: MicroProse-style Alt+D detail toggle (High / Medium / Low) with 2-second top-bar status flash (via pm_tooltip exports).
;       State block DET at $dc300 (zero-filled at boot -> High detail, 100% pixel-identical default):
;         +0 DET_LVL.w : 0 = High (full), 1 = Medium (no rain, 50% trees), 2 = Low (no rain, no trees, flat-shaded terrain)
;         +2 DET_REQ.b : set non-zero by qol_keys2 on Alt+D
;         +3 DET_DRT.b : banner needs compose_sb
;         +4 DET_END.l : VBL timestamp ($6f304) when the 2s banner expires (0 = inactive)
;       Site $1168c = tree/scenery renderer (object type 2): High = all trees, Medium = 50% (btst #2 of record ptr a3, 12-byte
;       stride alternates deterministically), Low = skip all trees.
;       Exports: $dc360 = hud_chk (called from pm_tooltip), $dc700 = flat_tri (called from p6_tri when DET_LVL == 2).
DET     equ     $dc300
DET_LVL equ     DET+0
DET_REQ equ     DET+2
DET_DRT equ     DET+3
DET_END equ     DET+4
SLOPE   equ     $d5000
S_TIP   equ     $cdc00                  ; pm_tooltip state block
SB_TIP  equ     S_TIP+$290              ; pm_tooltip 52-char string buffer
COMP_SB equ     $cd006                  ; pm_tooltip compose_sb export
BLIT_SB equ     $cd00c                  ; pm_tooltip blit export
CMAP_A  equ     $dc500
CTAB_A  equ     $dc580

        org     $1168c
        jmp     $dc330.l

; ---- tree/scenery filter ($dc330) ---------------------------------------------------------------------------------
        org     $dc330
tree_d: move.w  DET_LVL.l,d6
        beq.s   .go                     ; 0 = High: all trees
        subq.w  #1,d6
        bne.s   .skip                   ; 2 = Low: no trees
        move.l  a3,d6                   ; 1 = Medium: 50% trees (12-byte record stride -> bit 2 alternates 0/1)
        btst    #2,d6
        bne.s   .skip
.go:    move.l  a2,d6                   ; displaced 3 instructions
        add.l   a3,d6
        move.l  d6,d7
        jmp     $11692.l
.skip:  rts

; ---- HUD banner check ($dc360), called from pm_tooltip with a6 = S_TIP; returns d0 = 1 if banner drawn, 0 else ----
        org     $dc360
hud_chk:
        tst.b   DET_REQ.l
        beq.s   .chk
        clr.b   DET_REQ.l
        move.w  DET_LVL.l,d0
        addq.w  #1,d0
        cmpi.w  #3,d0
        blo.s   .st
        moveq   #0,d0
.st:    move.w  d0,DET_LVL.l
        move.l  $6f304.l,d0
        addi.l  #100,d0                 ; show banner for 100 VBLs (~2.0 s)
        bne.s   .nz
        moveq   #1,d0
.nz:    move.l  d0,DET_END.l
        st.b    DET_DRT.l
.chk:   move.l  DET_END.l,d0
        beq.s   .no
        sub.l   $6f304.l,d0
        ble.s   .exp
        tst.b   DET_DRT.l
        beq.s   .drw
        clr.b   DET_DRT.l
        move.w  DET_LVL.l,d0
        mulu.w  #52,d0
        lea     BANNERS(pc),a0
        adda.w  d0,a0
        lea     SB_TIP.l,a1
        moveq   #12,d1                  ; 13 longs = 52 bytes
.cp:    move.l  (a0)+,(a1)+
        dbra    d1,.cp
        jsr     COMP_SB.l
        clr.w   $12(a6)                 ; sHK = 0
        move.w  #$7fff,6(a6)            ; sKEY = $7fff (mark active so qol_hover does not overwrite)
.drw:   jsr     BLIT_SB.l
        moveq   #1,d0
        rts
.exp:   clr.l   DET_END.l
        clr.w   6(a6)                   ; sKEY = 0: let tooltip/hover resume next pass
.no:    moveq   #0,d0
        rts

BANNERS:
        dc.b    "Detail: High (full detail)                          "
        dc.b    "Detail: Medium (no rain, 50% trees)                 "
        dc.b    "Detail: Low (no rain, no trees, flat terrain)       "
        even

; ---- 101-entry dominant colour map + 10 solid-colour 1-group writers ($dc500..$dc6ff) ----------------------------
; Indices: 0=col0, 1=col1, 2=col2, 3=col3, 4=col4, 5=col6, 6=col11, 7=col12, 8=col13, 9=col14
        org     $dc500
CMAP:   dc.b    9,9,9,9,9,9,9,9,9,9,9,1,1,1,1,2
        dc.b    2,2,2,2,2,2,2,3,3,3,3,3,5,5,1,1
        dc.b    1,1,8,8,8,8,7,7,7,7,7,6,6,6,5,5
        dc.b    1,1,1,1,8,8,8,8,7,7,7,7,7,6,6,6
        dc.b    5,7,1,1,1,8,8,8,8,8,7,7,7,7,7,6
        dc.b    6,6,6,3,1,1,1,2,2,2,2,2,3,3,3,3
        dc.b    3,4,4,4,4,0,0,0,0,0,0,0,0,0,0,0
        dc.b    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        org     $dc580
CTAB:   dc.w    col0-CTAB,col1-CTAB,col2-CTAB,col3-CTAB,col4-CTAB
        dc.w    col6-CTAB,col11-CTAB,col12-CTAB,col13-CTAB,col14-CTAB

        dc.l    $00000000,$00000000     ; col 0 (0000)
col0:   not.l   d3
        and.l   d3,(a2)
        and.l   d3,4(a2)
        rts
        dc.l    $ffff0000,$00000000     ; col 1 (0001)
col1:   or.w    d3,(a2)
        not.l   d3
        and.w   d3,2(a2)
        and.l   d3,4(a2)
        rts
        dc.l    $0000ffff,$00000000     ; col 2 (0010)
col2:   or.w    d3,2(a2)
        not.l   d3
        and.w   d3,(a2)
        and.l   d3,4(a2)
        rts
        dc.l    $ffffffff,$00000000     ; col 3 (0011)
col3:   or.l    d3,(a2)
        not.l   d3
        and.l   d3,4(a2)
        rts
        dc.l    $00000000,$ffff0000     ; col 4 (0100)
col4:   or.w    d3,4(a2)
        not.l   d3
        and.l   d3,(a2)
        and.w   d3,6(a2)
        rts
        dc.l    $0000ffff,$ffff0000     ; col 6 (0110)
col6:   or.l    d3,2(a2)
        not.w   d3
        and.w   d3,(a2)
        and.w   d3,6(a2)
        rts
        dc.l    $ffffffff,$0000ffff     ; col 11 (1011)
col11:  or.l    d3,(a2)
        or.w    d3,6(a2)
        not.w   d3
        and.w   d3,4(a2)
        rts
        dc.l    $00000000,$ffffffff     ; col 12 (1100)
col12:  or.l    d3,4(a2)
        not.l   d3
        and.l   d3,(a2)
        rts
        dc.l    $ffff0000,$ffffffff     ; col 13 (1101)
col13:  or.w    d3,(a2)
        or.l    d3,4(a2)
        not.w   d3
        and.w   d3,2(a2)
        rts
        dc.l    $0000ffff,$ffffffff     ; col 14 (1110)
col14:  or.w    d3,2(a2)
        or.l    d3,4(a2)
        not.w   d3
        and.w   d3,(a2)
        rts

; ---- flat-shaded triangle filler ($dc700), entered from p6_tri after range check + sort ---------------------------
        org     $dc700
FSLOPE_ macro
        move.l  \1,\3
        swap    \3
        ext.l   \3
        bpl.s   fsp\4
        neg.l   \3
fsp\4:  move.w  \3,\2
        or.w    \1,\2
        cmp.w   #63,\2
        bhi.w   fsl\4
        move.w  \1,\2
        lsl.w   #8,\2
        add.w   \3,\3
        add.w   \3,\3
        add.w   \3,\2
        move.l  (a1,\2.w),\2
fsq\4:  tst.l   \1
        bpl.s   fsr\4
        neg.l   \2
fsr\4:
        endm

FSLOW_  macro
fsl\4:  cmp.w   \3,\1
        ble.s   fsb\4
        swap    \3
        divu.w  \1,\3
        andi.l  #$ffff,\3
        bra.s   fse\4
fsb\4:  lsl.l   #8,\3
        divu.w  \1,\3
        bvc.s   fsc\4
        move.l  #$10000,\3
        bra.s   fse\4
fsc\4:  andi.l  #$ffff,\3
        lsl.l   #8,\3
fse\4:  move.l  \3,\2
        bra.w   fsq\4
        endm

flat_tri:
        move.w  d0,-(a7)                ; save y0
        cmp.w   d0,d1
        beq.w   fflat1
        cmp.w   d0,d2
        beq.w   fflat2
        sub.w   d0,d1
        sub.w   d0,d2
        clr.w   d0
        sub.l   d0,d1                   ; [dx1 | dy1]
        sub.l   d0,d2                   ; [dx2 | dy2]
        lea     SLOPE.l,a1
        FSLOPE_ d1,d6,d7,1              ; s1
        FSLOPE_ d2,d5,d7,2              ; s2
        cmp.l   d6,d5
        beq.w   fnil
        bgt.s   foa
        movea.l d5,a3
        movea.l d6,a4
        move.w  d1,d4
        sub.w   d2,d4
        bmi.s   fob2
        moveq   #1,d4
        move.l  d1,d5
        sub.l   d2,d5
        move.w  d2,d7
        bra.s   fo3
fob2:   moveq   #2,d4
        move.l  d2,d5
        sub.l   d1,d5
        move.w  d1,d7
        bra.s   fo3
foa:    moveq   #$1c,d3
        movea.l d6,a3
        movea.l d5,a4
        move.w  d1,d4
        sub.w   d2,d4
        bmi.s   foa2
        moveq   #2,d4
        move.l  d1,d5
        sub.l   d2,d5
        move.w  d2,d7
        bra.s   fo3
foa2:   moveq   #1,d4
        move.l  d2,d5
        sub.l   d1,d5
        move.w  d1,d7
fo3:    movea.l d0,a2
        move.w  (a7)+,d2
        cmp.w   #2,d5
        blo.s   fc1
        FSLOPE_ d5,d6,d1,3
        move.l  d6,-(a7)
        subq.w  #2,d5
        move.w  d5,-(a7)
        move.w  d4,-(a7)
        bra.w   fgo
fc1:    add.w   d5,d7
        subq.w  #1,d7
        clr.w   -(a7)
        bra.w   fgo

fflat2: exg     d1,d2
        exg     d0,d1
fflat1: cmp.w   d0,d2
        beq.w   fnil
        sub.w   d0,d2
        move.w  d2,d7
        swap    d0
        swap    d1
        swap    d2
        cmp.w   d0,d1
        bge.s   ff1a
        exg     d0,d1
        moveq   #$1c,d3
ff1a:   lea     SLOPE.l,a1
        move.w  d2,d4
        sub.w   d0,d4
        swap    d4
        move.w  d7,d4
        FSLOPE_ d4,d6,d5,4
        movea.l d6,a3
        move.w  d2,d4
        sub.w   d1,d4
        swap    d4
        move.w  d7,d4
        FSLOPE_ d4,d6,d5,5
        movea.l d6,a4
        swap    d0
        clr.w   d0
        swap    d1
        clr.w   d1
        movea.l d1,a2
        move.w  (a7)+,d2
        subq.w  #1,d7
        clr.w   -(a7)

fgo:    move.l  d0,d4
        move.l  a2,d5
        andi.w  #$7f,d3
        lea     CMAP_A.l,a0
        moveq   #0,d0
        move.b  (a0,d3.w),d0
        add.w   d0,d0
        lea     CTAB_A.l,a5
        adda.w  (a5,d0.w),a5
        movea.l $e3e2.l,a1
        lsl.w   #5,d2
        adda.w  d2,a1
        lsl.w   #2,d2
        adda.w  d2,a1
        moveq   #$1e,d6
        bra.s   frend

fiter:  add.l   a3,d4
        add.l   a4,d5
frend:  move.l  d4,d0
        swap    d0
        add.w   d0,d0
        move.l  d5,d1
        swap    d1
        add.w   d1,d1
        move.w  (a6,d1.w),d2
        move.w  (a6,d0.w),d3
        lea     (a1,d3.w),a2
        sub.w   d3,d2
        bmi.s   fabort
        bne.s   fmulti
        and.w   d6,d0
        add.w   d0,d0
        move.l  -$80(a6,d0.w),d3
        and.w   d6,d1
        add.w   d1,d1
        and.l   -$40(a6,d1.w),d3
        jsr     (a5)
        lea     $a0(a1),a1
        dbra    d7,fiter
fchk:   move.w  (a7)+,d0
        beq.s   fdone
        move.w  (a7)+,d7
        subq.w  #1,d0
        bne.s   .fr
        movea.l (a7)+,a3
        clr.w   -(a7)
        bra.s   fiter
.fr:    movea.l (a7)+,a4
        clr.w   -(a7)
        bra.s   fiter
fabort: move.w  (a7)+,d0
        beq.s   fdone
        addq.l  #6,a7
fdone:  rts
fnil:   addq.l  #2,a7
        rts

fmulti: subq.w  #8,d2
        bne.s   fgen
        and.w   d6,d0
        add.w   d0,d0
        move.l  -$80(a6,d0.w),d3
        jsr     (a5)
        addq.l  #8,a2
        and.w   d6,d1
        add.w   d1,d1
        move.l  -$40(a6,d1.w),d3
        jsr     (a5)
        lea     $a0(a1),a1
        dbra    d7,fiter
        bra.s   fchk

fgen:   and.w   d6,d0
        add.w   d0,d0
        move.l  -$80(a6,d0.w),d3
        jsr     (a5)
        addq.l  #8,a2
        movem.l -8(a5),d0-d1
        lsr.w   #1,d2
        neg.w   d2
        jmp     fcend(pc,d2.w)
        rept    18
        move.l  d0,(a2)+
        move.l  d1,(a2)+
        endr
fcend:  move.l  d5,d1
        swap    d1
        add.w   d1,d1
        and.w   d6,d1
        add.w   d1,d1
        move.l  -$40(a6,d1.w),d3
        jsr     (a5)
        lea     $a0(a1),a1
        dbra    d7,fiter
        bra.w   fchk

        FSLOW_  d1,d6,d7,1
        FSLOW_  d2,d5,d7,2
        FSLOW_  d5,d6,d1,3
        FSLOW_  d4,d6,d5,4
        FSLOW_  d4,d6,d5,5
