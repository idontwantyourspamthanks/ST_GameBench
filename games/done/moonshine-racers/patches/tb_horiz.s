; name: tb_horiz
; default: yes
; site: $18318
; orig: 3a39000012f6
; requires: tb_blit
; conflicts: sb_bar
; doc: STE blitter for the horizon strip copy and solid sky fill $18318 (pixel-identical): replaces CPU movem.l loops with 1-2 blits for the horizon (8 cyc/word) and 1 HOP=0/LOP=15 solid fill for the sky (4 cyc/word).
; note: Uses BST ($B5800 from tb_blit).  When BST != 1, replays stock $18318 untouched.  When TBCR == 8 (Timer B running), chunks by 1 row (horizon) / 2 rows (sky) with TB guard; when TBCR != 8, unguarded single HOG blit.
BL      equ     $ffff8a00
BST     equ     $B5800
GTH     equ     3

        org     $18318
        jmp     $B6200.l

        org     $B6200
tb_horiz:
        cmpi.b  #1,BST.l
        bne.w   .fb
        move.w  $12f6.l,d5
        moveq   #$2f,d7
        sub.w   d5,d7
        bmi.w   .ret
        addq.w  #1,d7                   ; rows = 1..48
        movea.l $12f0.l,a0              ; dest end pointer (row 0 -> a0-160, row k -> a0-(k+1)*160)
        move.w  $12f8.l,d2
        moveq   #-$10,d1
        and.w   d2,d1
        lsr.w   #1,d1                   ; B = byte offset 0, 8, 16, ..., 152
        moveq   #$c,d6
        and.w   d2,d6
        lea     $1838e.l,a1
        movea.l (a1,d6.w),a1            ; pre-shifted horizon buffer ($66200/$64400/$62600/$60800)
        move.w  d5,d0
        add.w   d5,d5
        add.w   d5,d5
        add.w   d0,d5
        lsl.w   #5,d5                   ; d5 * 160
        adda.w  d5,a1
        moveq   #-1,d0
        move.l  d0,BL+$28.w             ; endmask 1, 2
        move.w  d0,BL+$2c.w             ; endmask 3
        clr.b   BL+$3d.w                ; skew = 0
        move.w  #$0203,BL+$3a.w         ; HOP=source, LOP=S
        ; ---- left part: W1 = (160 - B) / 2 words from (a1 + B) -> (a0 - 160), bottom-up in dest
        move.w  #160,d3
        sub.w   d1,d3
        lsr.w   #1,d3                   ; W1 (4..80)
        lea     (a1,d1.w),a2            ; src1
        lea     -160(a0),a3             ; dst1
        move.w  d3,d4
        bsr.w   hblit
        ; ---- right part (when B > 0): W2 = B / 2 words from a1 -> (a0 - B), bottom-up in dest
        tst.w   d1
        beq.s   .sky
        move.w  d1,d4
        lsr.w   #1,d4                   ; W2 (4..76)
        movea.l a1,a2                   ; src2
        movea.l a0,a3
        suba.w  d1,a3                   ; dst2 = a0 - B
        bsr.w   hblit
.sky:   ; advance a0 -= rows * 160 (matching stock $183ee)
        move.w  d7,d0
        mulu.w  #160,d0
        suba.l  d0,a0
        move.w  $1304.w,d7
        subi.w  #$41,d7
        ble.s   .ret
        ; fill d7 rows x 160 bytes with $FFFF at (a0 - d7*160 .. a0 - 1) using HOP=0, LOP=15 (4 cyc/word!)
        move.w  d7,d0
        mulu.w  #160,d0
        suba.l  d0,a0
        move.l  #$00020002,BL+$2e.w     ; dst xinc = 2, yinc = 2 (contiguous forward)
        move.w  #80,BL+$36.w            ; xcount = 80 words
        move.w  #$000f,BL+$3a.w         ; HOP=0, LOP=15 (all 1s, no source read!)
        cmpi.b  #8,$fffffa1b.w
        beq.s   .skytb
        move.l  a0,BL+$32.w
        move.w  d7,BL+$38.w
        move.b  #$c0,BL+$3c.w
.ret:   rts
.fb:    move.w  $12f6.l,d5
        jmp     $1831e.l
.skytb: move.w  d7,d2
        cmpi.w  #2,d2
        ble.s   .st1
        moveq   #2,d2
.st1:   move.l  a0,BL+$32.w
        move.w  d2,BL+$38.w
        bsr.w   tpass
        sub.w   d2,d7
        ble.s   .ret
        move.w  d2,d0
        mulu.w  #160,d0
        adda.l  d0,a0
        bra.s   .skytb

; hblit: copy d7 rows of d4 words from a2 (top-down, stride +160) to a3 (bottom-up, stride -160). Preserves d1, d7, a0, a1.
hblit:  move.w  d4,d0
        add.w   d0,d0                   ; 2*W
        move.w  #162,d2
        sub.w   d0,d2                   ; src yinc = 162 - 2*W
        move.l  #$00020000,d3
        move.w  d2,d3
        move.l  d3,BL+$20.w
        move.w  #-158,d2
        sub.w   d0,d2                   ; dst yinc = -158 - 2*W
        move.l  #$00020000,d3
        move.w  d2,d3
        move.l  d3,BL+$2e.w
        move.w  d4,BL+$36.w             ; xcount = W
        cmpi.b  #8,$fffffa1b.w
        beq.s   .htb
        move.l  a2,BL+$24.w
        move.l  a3,BL+$32.w
        move.w  d7,BL+$38.w
        move.b  #$c0,BL+$3c.w
        rts
.htb:   move.w  d7,d5
        moveq   #1,d6                   ; rows per TB-guarded chunk (budget ~900 cyc at 8 cyc/word)
        cmpi.w  #56,d4
        bhi.s   .hl
        moveq   #2,d6
        cmpi.w  #28,d4
        bhi.s   .hl
        moveq   #4,d6
        cmpi.w  #14,d4
        bhi.s   .hl
        moveq   #8,d6
.hl:    cmpi.b  #8,$fffffa1b.w          ; Timer B stopped mid-horizon? Finish all remaining rows in 1 HOG blit!
        bne.s   .hrem
        move.w  d6,d2
        cmp.w   d5,d2
        ble.s   .h1
        move.w  d5,d2
.h1:    move.l  a2,BL+$24.w
        move.l  a3,BL+$32.w
        move.w  d2,BL+$38.w
        bsr.s   tpass
        sub.w   d2,d5
        ble.s   .hdone
        move.w  d2,d0
        mulu.w  #160,d0
        adda.l  d0,a2
        suba.l  d0,a3
        bra.s   .hl
.hrem:  move.l  a2,BL+$24.w
        move.l  a3,BL+$32.w
        move.w  d5,BL+$38.w
        move.b  #$c0,BL+$3c.w
.hdone: rts

tpass:  cmpi.b  #8,$fffffa1b.w
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
