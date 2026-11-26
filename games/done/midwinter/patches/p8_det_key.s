; name: p8_det_key
; default: yes
; site: $14e90
; orig: 4eb90000bd9a
; note: Detail-mode toggle ('D' key, scancode $20) and on-screen banner (HIGH / MEDIUM / LOW).
; note: Hooks `jsr $bd9a.l` (screen flip) at $14e90 in sub_014e00 (after sub_014e98 "ENEMY IN RANGE").
; note: Zero-overhead mode switching: when 'D' is pressed in 3D view ($62b8 == 2), patches:
; note:   - RING_LIM ($B7006): $10 (8 rings HIGH), $0c (6 rings MED), $0a (5 rings LOW)
; note:   - $1b1ee (fill): jmp $b7160 (exact fast fill HIGH/MED) vs jmp $b7180 (flat single-pass LOW)
; note:   - $19f80 / $1a2cc (edge walker): original 2x divu.w (HIGH, 0 cy overhead) vs
; note:     1x mulu.w reciprocal DDA ($b7b00 / $b7b30, MED & LOW, ~210 cy/edge faster)
; note: State block at $B7000:
; note:   $B7000 LEVEL.w     0 = HIGH, 1 = MEDIUM, 2 = LOW
; note:   $B7002 PREV_D.w    previous 'D' key state
; note:   $B7004 TIMER.w     banner countdown frames
; note:   $B7006 RING_LIM.w  ring loop limit ($10 / $0c / $0a)
; note:   $B7008 INIT_DONE.w set to 1 once 16 single-pass solid variants are cloned to $B7400
DET     equ     $b7000
oLVL    equ     0
oPREVD  equ     2
oTIMER  equ     4
oRING   equ     6
oINIT   equ     8

SKIPGEN equ     $b6004          ; p7_skip_render oGEN
SKIPGB  equ     $b6006          ; p7_skip_render oGENB[3] (6 bytes)
PFXKB   equ     $b4800          ; p4_pfx_fill KB[3] (6 bytes)
PFXCK   equ     $b4808          ; p4_pfx_fill CK.w

FILL_HI equ     $b71c0          ; p8_fill_fast exact entry
FILL_LO equ     $b71e0          ; p8_fill_fast LOW flat entry
WPOS_F  equ     $b7b00          ; fast reciprocal walker (+dx)
WNEG_F  equ     $b7b30          ; fast reciprocal walker (-dx)
RTAB    equ     $b7c00          ; 201-word floor(65536/dy) table

        org     $14e90
        jsr     $b7010.l

        org     $b7000
        dc.w    0               ; +0 LEVEL (0 = HIGH)
        dc.w    0               ; +2 PREV_D
        dc.w    0               ; +4 TIMER
        dc.w    $0010           ; +6 RING_LIM (8 rings)
        dc.w    0               ; +8 INIT_DONE
        dc.w    0,0,0           ; pad to $b7010

        org     $b7010
        movem.l d0-d2/a0-a2/a6,-(a7)
        lea     DET.l,a0
        cmpi.w  #2,$62b8.l      ; only toggle in 3D game context
        bne.s   .chk_tmr
        tst.b   $2c29a+$20.l    ; scancode $20 = 'D'
        bne.s   .down
        clr.w   oPREVD(a0)
        bra.s   .chk_tmr
.down:  tst.w   oPREVD(a0)
        bne.s   .chk_tmr        ; already handled this press
        move.w  #1,oPREVD(a0)
        move.w  oLVL(a0),d0
        addq.w  #1,d0
        cmpi.w  #3,d0
        bcs.s   .oklvl
        moveq   #0,d0
.oklvl: move.w  d0,oLVL(a0)
        bsr.w   .apply_lvl
        move.w  #24,oTIMER(a0)
        addq.w  #1,SKIPGEN.l    ; force all 3 buffers to redraw
        clr.l   SKIPGB.l
        clr.w   SKIPGB+4.l
        clr.l   PFXKB.l
        clr.w   PFXKB+4.l
        clr.w   PFXCK.l
.chk_tmr:
        move.w  oTIMER(a0),d0
        beq.s   .done
        subq.w  #1,d0
        move.w  d0,oTIMER(a0)
        clr.l   SKIPGB.l
        clr.w   SKIPGB+4.l
        clr.l   PFXKB.l
        clr.w   PFXKB+4.l
        clr.w   PFXCK.l
        tst.w   d0
        beq.s   .done
        lea     $2c376.l,a6
        lea     $262a2.l,a2
        move.w  #$0,$11864.l
        move.w  #$0,$18(a6)
        move.w  #$c,$11866.l
        move.w  #$a0,d0
        move.w  #$3a,d1
        move.w  oLVL(a0),d2
        add.w   d2,d2
        lea     .strs(pc),a1
        adda.w  (a1,d2.w),a1
        jsr     $117d8.l
.done:  movem.l (a7)+,d0-d2/a0-a2/a6
        jmp     $bd9a.l         ; original screen flip

; Apply detail level d0 (0=HIGH, 1=MED, 2=LOW); a0 = DET
.apply_lvl:
        move.w  d0,d1
        add.w   d1,d1
        lea     .rings(pc),a1
        move.w  (a1,d1.w),oRING(a0)
        ; Patch $1b1ee fill target: FILL_LO if LOW (d0==2), else FILL_HI
        move.l  #FILL_HI,d2
        cmpi.w  #2,d0
        bne.s   .set_fill
        move.l  #FILL_LO,d2
.set_fill:
        move.l  d2,$1b1f0.l     ; operand of `jmp $xxxxxxxx.l` at $1b1ee
        ; Patch $19f80 and $1a2cc walker DDA: original 2x divu.w if HIGH (d0==0), else fast reciprocal
        tst.w   d0
        bne.s   .set_fastw
        lea     .w_orig(pc),a1
        lea     $19f80.l,a2
        move.l  (a1),(a2)+
        move.l  4(a1),(a2)+
        move.l  8(a1),(a2)+
        lea     $1a2cc.l,a2
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        rts
.set_fastw:
        move.w  #$4ef9,$19f80.l
        move.l  #WPOS_F,$19f82.l
        move.w  #$4ef9,$1a2cc.l
        move.l  #WNEG_F,$1a2ce.l
        rts

.w_orig:dc.w    $86c4,$3403,$4243,$86c4,$4843,$3602
.rings: dc.w    $0010,$000c,$000a
.strs:  dc.w    .s_hi-.strs,.s_med-.strs,.s_lo-.strs
.s_hi:  dc.b    "DETAIL HIGH",0
.s_med: dc.b    "DETAIL MEDIUM",0
.s_lo:  dc.b    "DETAIL LOW",0
        even

        org     $b7b00
wpos_fast:
        cmpi.w  #1,d4
        beq.s   .dy1
        lea     RTAB.l,a1
        add.w   d4,d4
        mulu.w  (a1,d4.w),d3            ; d3 = (q << 16) | f
        lsr.w   #1,d4
        swap    d3                      ; d3 = (f << 16) | q
.dy1:   jmp     $19f8c.l

        org     $b7b30
wneg_fast:
        cmpi.w  #1,d4
        beq.s   .dy1
        lea     RTAB.l,a1
        add.w   d4,d4
        mulu.w  (a1,d4.w),d3
        lsr.w   #1,d4
        swap    d3
.dy1:   jmp     $1a2d8.l

        org     $b7c00
        dc.w    0,0
        dc.w    32768,21845,16384,13107,10922,9362,8192,7281
        dc.w    6553,5957,5461,5041,4681,4369,4096,3855,3640,3449
        dc.w    3276,3120,2978,2849,2730,2621,2520,2427,2340,2259
        dc.w    2184,2114,2048,1985,1927,1872,1820,1771,1724,1680
        dc.w    1638,1598,1560,1524,1489,1456,1424,1394,1365,1337
        dc.w    1310,1285,1260,1236,1213,1191,1170,1149,1129,1110
        dc.w    1092,1074,1057,1040,1024,1008,992,978,963,949
        dc.w    936,923,910,897,885,873,862,851,840,829
        dc.w    819,809,799,789,780,771,762,753,744,736
        dc.w    728,720,712,704,697,689,682,675,668,661
        dc.w    655,648,642,636,630,624,618,612,606,601
        dc.w    595,590,585,579,574,569,564,560,555,550
        dc.w    546,541,537,532,528,524,520,516,512,508
        dc.w    504,500,496,492,489,485,481,478,474,471
        dc.w    468,464,461,458,455,451,448,445,442,439
        dc.w    436,434,431,428,425,422,420,417,414,412
        dc.w    409,407,404,402,399,397,394,392,390,387
        dc.w    385,383,381,378,376,374,372,370,368,366
        dc.w    364,362,360,358,356,354,352,350,348,346
        dc.w    344,343,341,339,337,336,334,332,330,329
        dc.w    327
