; name: ta_ymw
; default: yes
; site: $8e2c
; orig: 41ee001243f900ff8800
; data: $BEF40 16
; doc: YM player: the 12 register writes of every VBL are skipped for the registers whose value did not change since the last VBL (3 of 12 change per VBL in the race); identical chip state.
; note: Tighten wave A (work/notes/tighten_a.md).  Site $8e2c inside the YM player $8c38, right after `ori.w #$700,sr`: `lea $12(a6),a0 / lea.l $ff8800.l,a1` (10 bytes) -> `jmp $BE400.l`; the blob does the rest of the player (the write loop $8e3e-$8e86: R0/R1 from the tone image + the $91f0 word, R2-R6, R7 read-modify-write
; note: keeping the I/O bits 6-7, R8-R11) and ends like the stock code (`move.w (a7)+,sr / rts`).  R12/R13 are never written by the player.  Each register is written only if its value differs from the shadow of the last value written (data $BEF40, 12 bytes + valid flag);
; note: the first call writes everything (shadow := complement of the image).  The player is the only YM writer of the game (hwscan, work/notes/rendering.md section 3); a register that equals the shadow already holds that value in the chip.
SH      equ     $BEF40                  ; +0 word R0/R1 value, +2 long image bytes 2-5, +6 long image bytes 6-9, +10 word image bytes 10-11
VALID   equ     $BEF4C
        org     $8e2c
        jmp     $BE400.l

        org     $BE400
ymw:    lea     $12(a6),a0
        lea     $ff8800.l,a1
        lea     2(a1),a2
        lea     SH.l,a3
        moveq   #0,d5
        move.b  (a0)+,d2
        move.b  (a0)+,d1
        andi.w  #$f,d1
        lsl.w   #8,d1
        or.b    d2,d1
        add.w   $91f0.l,d1              ; d1 = R1<<8 | R0, as the stock loop computes it
        tst.b   VALID.l
        bne.s   .v
        st      VALID.l                 ; first call: shadow := complement, so everything is written
        move.w  d1,d3
        not.w   d3
        move.w  d3,(a3)
        move.l  (a0),d3
        not.l   d3
        move.l  d3,2(a3)
        move.l  4(a0),d3
        not.l   d3
        move.l  d3,6(a3)
        move.w  8(a0),d3
        not.w   d3
        move.w  d3,10(a3)
.v:     cmp.w   (a3),d1
        beq.s   .gA
        move.w  d1,(a3)
        move.b  d5,(a1)                 ; R0
        move.b  d1,(a2)
        move.b  #1,(a1)                 ; R1
        lsr.w   #8,d1
        move.b  d1,(a2)
.gA:    move.l  (a0)+,d1                ; R2-R5
        cmp.l   2(a3),d1
        beq.s   .gB
        move.l  d1,2(a3)
        moveq   #2,d0
        moveq   #3,d2
.wA:    rol.l   #8,d1
        move.b  d0,(a1)
        move.b  d1,(a2)
        addq.b  #1,d0
        dbra    d2,.wA
.gB:    move.l  (a0)+,d1                ; R6-R9 (R7 keeps the I/O bits 6-7)
        move.l  6(a3),d4
        cmp.l   d4,d1
        beq.s   .gC
        move.l  d1,6(a3)
        eor.l   d1,d4                   ; non-zero byte = changed
        rol.l   #8,d1
        rol.l   #8,d4
        tst.b   d4
        beq.s   .u6
        moveq   #6,d0
        move.b  d0,(a1)
        move.b  d1,(a2)
.u6:    rol.l   #8,d1
        rol.l   #8,d4
        tst.b   d4
        beq.s   .u7
        moveq   #7,d0
        move.b  d0,(a1)
        move.b  (a1),d2
        andi.b  #$c0,d2
        move.b  d1,d3
        andi.b  #$3f,d3
        or.b    d3,d2
        move.b  d2,(a2)
.u7:    rol.l   #8,d1
        rol.l   #8,d4
        tst.b   d4
        beq.s   .u8
        moveq   #8,d0
        move.b  d0,(a1)
        move.b  d1,(a2)
.u8:    rol.l   #8,d1
        rol.l   #8,d4
        tst.b   d4
        beq.s   .gC
        moveq   #9,d0
        move.b  d0,(a1)
        move.b  d1,(a2)
.gC:    move.w  (a0)+,d1                ; R10-R11
        cmp.w   10(a3),d1
        beq.s   .done
        move.w  d1,10(a3)
        moveq   #10,d0
        move.b  d0,(a1)
        move.w  d1,d2
        lsr.w   #8,d2
        move.b  d2,(a2)
        move.b  #11,(a1)
        move.b  d1,(a2)
.done:  move.w  (a7)+,sr
        rts
