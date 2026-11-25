; name: tb_post
; default: yes
; site: $15a4e
; orig: 4a4666000028
; requires: tb_blit
; conflicts: sb_bar
; doc: STE blitter for the vertical-stretched 3-plane post/stem renderer $15a4e (pixel-identical): uses ENDMASK1/ENDMASK3 as the 16-bit sprite mask for 1-pass (D & ~M) | (S & M) blits (4 blits total vs CPU loop).
; note: $15a4e ($37c8) stamps one 3-plane 16-px row (a1: p0.w, p1.w, p3.w) d7 times vertically at a3 with x-shift d6 (x = d0).  On STE (BST == 1 from tb_blit), when d6 != 0, 0 <= d0 < $130, d7 >= 4:
; note: pre-shifts the single row once on CPU into 12 bytes at PST ($B5820, unused gap in tb_blit's $B5800+512 data block before TMP $B5880), then uses ENDMASK1 = M_left and ENDMASK3 = M_right with
; note: HOP=2 LOP=3 (planes 0,1,3; SRC_XINC=2 SRC_YINC=-2) and HOP=0 LOP=0 (plane 2, no source read).  1-column fast path when M_left == 0 or M_right == 0.  Timer-B guarded when TBCR == 8.
BL      equ     $ffff8a00
BST     equ     $B5800                  ; from tb_blit: 1 = STE blitter present
PST     equ     $B5820                  ; 12 bytes: p0_L, p0_R, p1_L, p1_R, p3_L, p3_R (inside tb_blit's $B5800..$B587F gap)
GTH     equ     3

        org     $15a4e
        jmp     $B6020.l

        org     $B6020
tb_post:
        cmpi.b  #1,BST.l
        bne.w   .fb
        tst.w   d6
        beq.w   .fb
        tst.w   d0
        bmi.w   .fb
        cmpi.w  #$130,d0
        bge.w   .fb
        cmpi.w  #4,d7
        blt.w   .fb
        ; shift the 3 source words once by d6 (exact match to stock $15aa0-$15ab6):
        ; low word = left column (p >> d6), high word = right column (p << (16 - d6))
        moveq   #0,d1
        moveq   #0,d2
        moveq   #0,d3
        move.w  (a1)+,d1
        move.w  (a1)+,d2
        move.w  (a1)+,d3
        ror.l   d6,d1
        ror.l   d6,d2
        ror.l   d6,d3
        move.l  d1,d0
        or.l    d2,d0
        or.l    d3,d0                   ; d0.w = M_left, d0.hi = M_right
        beq.w   .ret                    ; completely transparent row: nothing to draw
        lea     PST.l,a0
        move.w  d1,(a0)+                ; p0_L
        swap    d1
        move.w  d1,(a0)+                ; p0_R
        move.w  d2,(a0)+                ; p1_L
        swap    d2
        move.w  d2,(a0)+                ; p1_R
        move.w  d3,(a0)+                ; p3_L
        swap    d3
        move.w  d3,(a0)+                ; p3_R
        move.w  d0,d1                   ; d1 = M_left
        swap    d0                      ; d0 = M_right
        clr.b   BL+$3d.w                ; skew = 0
        move.w  #$ffff,BL+$2a.w         ; endmask 2
        tst.w   d0
        beq.s   .oneL                   ; right column empty -> XCOUNT = 1 (left only)
        tst.w   d1
        beq.s   .oneR                   ; left column empty -> XCOUNT = 1 (right only)
        ; ---- 2-column masked 1-pass blit (XCOUNT = 2, ENDMASK1 = M_left, ENDMASK3 = M_right)
        move.w  d1,BL+$28.w             ; endmask 1 = M_left
        move.w  d0,BL+$2c.w             ; endmask 3 = M_right
        move.l  #$0002fffe,BL+$20.w     ; src xinc = +2, yinc = -2 (repeats the 2 words every row)
        move.l  #$00080098,BL+$2e.w     ; dst xinc = +8, yinc = 152 (160 - 8)
        move.w  #2,BL+$36.w             ; xcount = 2
        lea     PST.l,a0
        bra.s   .run
.oneR:  addq.l  #8,a3                   ; right column only: advance dest by 8 bytes, src by +2
        move.w  d0,d1
        lea     PST+2.l,a0
        bra.s   .one1
.oneL:  lea     PST.l,a0
.one1:  move.w  d1,BL+$28.w             ; endmask 1 = mask
        clr.l   BL+$20.w                ; src xinc = 0, yinc = 0 (repeats the 1 word every row)
        move.l  #$000800a0,BL+$2e.w     ; dst xinc = +8, yinc = 160
        move.w  #1,BL+$36.w             ; xcount = 1
.run:   cmpi.b  #8,$fffffa1b.w
        beq.s   .tb
        ; ---- Timer B stopped: 4 unguarded HOG blits (planes 0, 1, 2, 3)
        move.w  #$0203,BL+$3a.w         ; HOP=source, LOP=S
        move.l  a0,BL+$24.w             ; plane 0
        move.l  a3,BL+$32.w
        move.w  d7,BL+$38.w
        move.b  #$c0,BL+$3c.w
        addq.l  #4,a0
        addq.l  #2,a3
        move.l  a0,BL+$24.w             ; plane 1
        move.l  a3,BL+$32.w
        move.w  d7,BL+$38.w
        move.b  #$c0,BL+$3c.w
        addq.l  #2,a3
        clr.w   BL+$3a.w                ; plane 2: HOP=0, LOP=0 (zeroes masked by ENDMASK, no source read!)
        move.l  a3,BL+$32.w
        move.w  d7,BL+$38.w
        move.b  #$c0,BL+$3c.w
        addq.l  #4,a0
        addq.l  #2,a3
        move.w  #$0203,BL+$3a.w         ; plane 3
        move.l  a0,BL+$24.w
        move.l  a3,BL+$32.w
        move.w  d7,BL+$38.w
        move.b  #$c0,BL+$3c.w
.ret:   rts
.fb:    tst.w   d6                      ; stock $15a4e
        bne.s   .fb1
        jmp     $15a54.l
.fb1:   jmp     $15a7a.l
        ; ---- Timer B running: chunk at 32 rows with TB guard
.tb:    move.w  d7,d2
        cmpi.w  #32,d2
        ble.s   .t1
        moveq   #32,d2
.t1:    move.w  #$0203,BL+$3a.w
        move.l  a0,BL+$24.w
        move.l  a3,BL+$32.w
        move.w  d2,BL+$38.w
        bsr.s   .pass
        lea     4(a0),a2
        lea     2(a3),a4
        move.l  a2,BL+$24.w
        move.l  a4,BL+$32.w
        move.w  d2,BL+$38.w
        bsr.s   .pass
        addq.l  #2,a4
        clr.w   BL+$3a.w
        move.l  a4,BL+$32.w
        move.w  d2,BL+$38.w
        bsr.s   .pass
        addq.l  #4,a2
        addq.l  #2,a4
        move.w  #$0203,BL+$3a.w
        move.l  a2,BL+$24.w
        move.l  a4,BL+$32.w
        move.w  d2,BL+$38.w
        bsr.s   .pass
        sub.w   d2,d7
        ble.s   .ret
        mulu.w  #160,d2
        adda.l  d2,a3
        bra.s   .tb
.pass:  cmpi.b  #8,$fffffa1b.w
        bne.s   .go
        cmpi.b  #GTH,$fffffa21.w
        bcc.s   .go
        move.w  #400,d0
.gw:    cmpi.b  #8,$fffffa1b.w
        bne.s   .go
        cmpi.b  #GTH,$fffffa21.w
        bcc.s   .go
        dbra    d0,.gw
.go:    move.b  #$c0,BL+$3c.w
        rts
