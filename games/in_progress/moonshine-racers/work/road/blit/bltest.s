; Blitter vs CPU row copy/shift cost test.  Load at $C0000, entered by jmp from the race loop ($7b74), runs with SR $2700 (no interrupts), then continues into $d1e4.
; Each test is bracketed by labels t<n>_s / t<n>_e (breakpoints read FrameCycles there).  Source rows: SRC ($C8000, 25 rows x 168 B, content irrelevant), destination DST ($CA000..).
SRC     equ     $C8000
DST     equ     $CC000
BLT     equ     $FF8A00
        org     $C0000
test:   movem.l d0-d7/a0-a6,-(a7)
        move    sr,-(a7)
        move.w  #$2700,sr
        ; fill SRC with a pattern
        lea     SRC,a0
        move.w  #(168*25)/4-1,d7
        move.l  #$a5c3f00f,d0
.f:     move.l  d0,(a0)+
        rol.l   #3,d0
        dbra    d7,.f
        ; ---- T0: empty loop overhead (80 rows)
t0_s:   moveq   #79,d7
.l:     nop
        dbra    d7,.l
t0_e:   nop
        ; ---- T1: CPU aligned copy 80 rows x 160 B, movem.l (13 regs: 3 x 52 + 4)
t1_s:   lea     DST,a1
        moveq   #79,d7
.r:     lea     SRC,a0
        movem.l (a0)+,d0-d6/a2-a6       ; 48 B  (12 regs)
        movem.l d0-d6/a2-a6,(a1)
        movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,48(a1)
        movem.l (a0)+,d0-d6/a2-a6
        movem.l d0-d6/a2-a6,96(a1)
        movem.l (a0)+,d0-d3             ; 16 B
        movem.l d0-d3,144(a1)
        lea     160(a1),a1
        dbra    d7,.r
t1_e:   nop
        ; ---- T2: CPU shifted copy, 80 rows x 160 B (80 words), shift s = row & 15 (1..15; 0 handled as copy), 32-bit [prev:cur] >> s per plane word
t2_s:   lea     DST,a1
        moveq   #79,d7
.r2:    move.w  d7,d5
        and.w   #15,d5                  ; s
        lea     SRC,a0
        moveq   #3,d6                   ; 4 planes
.p:     movea.l a0,a2
        movea.l a1,a3
        moveq   #0,d0                   ; prev word (low) in d0
        moveq   #19,d4                  ; 20 groups
.g:     move.w  (a2),d1                 ; cur
        swap    d0                      ; [prev:xx] -> shift register [prev:cur]
        move.w  d1,d0                   ; d0 = prev:cur
        lsr.l   d5,d0                   ; low word = out
        move.w  d0,(a3)
        swap    d0
        move.w  d1,d0                   ; keep cur as next prev (low word)  (d0 = x:cur)
        lea     8(a2),a2
        lea     8(a3),a3
        dbra    d4,.g
        addq.l  #2,a0
        addq.l  #2,a1
        dbra    d6,.p
        lea     160-8(a1),a1
        dbra    d7,.r2
t2_e:   nop
        ; ---- T3: blitter aligned copy (HOG), 80 rows, one blit per row: 4 plane-lines x 20 words
        lea     BLT,a2
        move.w  #8,$20(a2)              ; src xinc
        move.w  #-150,$22(a2)           ; src yinc (xcount 20: back to +2)
        move.w  #$ffff,$28(a2)
        move.w  #$ffff,$2a(a2)
        move.w  #$ffff,$2c(a2)
        move.w  #8,$2e(a2)              ; dst xinc
        move.w  #-150,$30(a2)           ; dst yinc
        move.w  #20,$36(a2)             ; xcount
        move.w  #$0203,$3a(a2)          ; HOP 2 (source), OP 3 (S)
t3_s:   lea     DST,a1
        lea     SRC,a0
        moveq   #79,d7
.r3:    move.l  a0,$24(a2)              ; src addr
        move.l  a1,$32(a2)              ; dst addr
        move.w  #4,$38(a2)              ; ycount = 4 planes
        move.b  #0,$3d(a2)              ; skew 0
        move.b  #$c0,$3c(a2)            ; go, HOG
        lea     160(a1),a1
        dbra    d7,.r3
t3_e:   nop
        ; ---- T4: blitter shifted copy: skew s = row & 15, FXSR set, xcount 21 (extra word)
        move.w  #-158,$22(a2)           ; xcount 21: yinc = 2 - 20*8
        move.w  #-158,$30(a2)
        move.w  #21,$36(a2)
t4_s:   lea     DST,a1
        lea     SRC,a0
        moveq   #79,d7
.r4:    move.w  d7,d0
        and.w   #15,d0
        or.w    #$40,d0                 ; FXSR
        move.l  a0,$24(a2)
        move.l  a1,$32(a2)
        move.w  #4,$38(a2)
        move.b  d0,$3d(a2)
        move.b  #$c0,$3c(a2)
        lea     160(a1),a1
        dbra    d7,.r4
t4_e:   nop
        ; ---- T5: blitter, one blit for the whole 80 rows (ycount 320): pure data-move cost, aligned
        move.w  #-150,$22(a2)
        move.w  #-150,$30(a2)
        move.w  #20,$36(a2)
t5_s:   lea     DST,a1
        lea     SRC,a0
        move.l  a0,$24(a2)
        move.l  a1,$32(a2)
        move.w  #320,$38(a2)
        move.b  #0,$3d(a2)
        move.b  #$c0,$3c(a2)
t5_e:   nop
        move.w  #$4a4a,$C4000           ; marker
        move.w  #$4e4f,$C4002
        move    (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $d1e4.l
