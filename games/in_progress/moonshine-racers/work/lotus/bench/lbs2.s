; Lotus-style blitter sprite microbenchmark (own code; models what $c6f2c..$c7402 of the exemplar does, parameters taken from
; the exemplar's own `info blitter` trace): mask word + P plane words interleaved per source word (stride 2*(P+1)), 4 AND passes
; (HOP=2 LOP=1, src = mask) + P OR passes (LOP=7, src = plane), HOG ($c0), fixed ~8-word blits ("rows per blit" k = max(1, 8/n)) issued
; from an unrolled pair chain `move.w d1,(a2) / move.b d6,(a6)` (a2 = ycount, a6 = control); registers persist between blits.
; Case table at $30000: n.w, then n * (cols.w rows.w x.w np.w reps.w pad.w).  Markers m_case / m_end (cycle counter timestamps).
BL      equ     $ffff8a00
SCR     equ     $50000
DAT     equ     $40000
CASES   equ     $30000
        org     $20000
start:  move.w  #$2700,sr
        lea     CASES.l,a0
        move.w  (a0)+,d7                ; number of cases
        subq.w  #1,d7
        move.l  a0,casep
nextcase:
        movea.l casep,a0
        move.w  (a0)+,vcols
        move.w  (a0)+,vrows
        move.w  (a0)+,vx
        move.w  (a0)+,vnp
        move.w  (a0)+,d6                ; reps
        addq.l  #2,a0
        move.l  a0,casep
        subq.w  #1,d6
        move.w  d7,-(a7)
m_case: nop
.rep:   move.w  vx,d0
        move.w  #60,d1
        bsr.w   draw
        dbra    d6,.rep
m_end:  nop
        move.w  (a7)+,d7
        dbra    d7,nextcase
        move.l  #$444f4e45,$20ff0.l     ; 'DONE'
.spin:  bra.s   .spin

; d0 = x, d1 = y ; vcols, vrows, vnp.   Table-driven setup (no mulu/divu): what a production kernel would do.
draw:   movem.l d2-d7/a0-a6,-(a7)
        move.w  d0,d2
        and.w   #15,d2                  ; s
        lsr.w   #4,d0
        lsl.w   #3,d0                   ; word column * 8
        move.w  d1,d3
        lsl.w   #5,d3
        move.w  d3,d4
        add.w   d3,d3
        add.w   d3,d3                   ; y * 128
        add.w   d4,d3                   ; y * 160
        add.w   d0,d3
        lea     SCR.l,a1
        adda.w  d3,a1                   ; dst
        lea     BL.l,a3
        move.w  vcols,d3                ; c
        move.w  d3,d4                   ; n
        move.w  vnp,d5
        add.w   d5,d5
        addq.w  #2,d5                   ; stride
        move.w  d5,$20(a3)              ; src xinc
        move.w  d2,d6
        add.w   d6,d6                   ; 2s
        tst.w   d2
        beq.s   .al
        addq.w  #1,d4                   ; n = c + 1
        clr.w   $22(a3)                 ; src yinc = 0 (n = c + 1)
        move.b  d2,d0
        or.b    #$40,d0
        move.b  d0,$3d(a3)              ; skew | FXSR
        bra.s   .sk
.al:    move.w  d5,$22(a3)              ; src yinc = stride
        clr.b   $3d(a3)
.sk:    lea     em1(pc),a0
        move.w  (a0,d6.w),$28(a3)
        move.w  #$ffff,$2a(a3)
        lea     em3(pc),a0
        move.w  (a0,d6.w),$2c(a3)
        move.w  #8,$2e(a3)              ; dst xinc
        add.w   d4,d4                   ; 2n
        lea     ytab(pc),a0
        move.w  (a0,d4.w),$30(a3)       ; dst yinc = 160 - 8 (n - 1)
        lea     ktab(pc),a0
        move.w  (a0,d4.w),d3            ; log2 rows per blit
        lsr.w   #1,d4
        move.w  d4,$36(a3)              ; xcount
        move.w  vrows,d0
        move.w  d0,d7
        lsr.w   d3,d0                   ; chunks
        moveq   #1,d1
        lsl.w   d3,d1                   ; k
        move.w  d1,d4
        subq.w  #1,d4
        and.w   d4,d7                   ; remainder
        lea     chain_end(pc),a4
        add.w   d0,d0
        add.w   d0,d0
        suba.w  d0,a4                   ; chain entry
        lea     $38(a3),a2              ; ycount
        lea     $3c(a3),a6              ; control
        lea     $24(a3),a0              ; src addr reg
        lea     $32(a3),a5              ; dst addr reg
        moveq   #0,d6
        move.b  #$c0,d6
        lea     DAT.l,a3
        move.l  a3,d3                   ; mask word of word 0
        move.w  #$0201,$ffff8a3a.w      ; AND
        moveq   #3,d5
        movea.l a1,a3
.mp:    move.l  d3,(a0)
        move.l  a3,(a5)
        bsr.w   pass
        addq.l  #2,a3
        dbra    d5,.mp
        move.w  #$0207,$ffff8a3a.w      ; OR
        movea.l a1,a3
        move.l  d3,d5
        addq.l  #2,d5
        move.w  vnp,d3
        subq.w  #1,d3
.dp:    move.l  d5,(a0)
        move.l  a3,(a5)
        bsr.w   pass
        addq.l  #2,d5
        addq.l  #2,a3
        dbra    d3,.dp
        movem.l (a7)+,d2-d7/a0-a6
        rts

em1:    dc.w    $ffff,$7fff,$3fff,$1fff,$0fff,$07ff,$03ff,$01ff,$00ff,$007f,$003f,$001f,$000f,$0007,$0003,$0001
em3:    dc.w    $ffff,$8000,$c000,$e000,$f000,$f800,$fc00,$fe00,$ff00,$ff80,$ffc0,$ffe0,$fff0,$fff8,$fffc,$fffe
ytab:   dc.w    0,160,152,144,136,128,120          ; index 2n: dst yinc  (n=1..5: 160,152,144,136,128)
ktab:   dc.w    0,3,2,1,0,0,0                      ; index 2n: log2(rows per blit): n=1:8, 2:4, 3:2, 4:1, 5:1

pass:   jsr     (a4)                    ; chain of full-size blits (d1 = rows per blit)
        tst.w   d7
        beq.s   .nr
        move.w  d7,(a2)
        move.b  d6,(a6)
.nr:    rts

chain:  rept    64
        move.w  d1,(a2)
        move.b  d6,(a6)
        endr
chain_end:
        rts

casep:  dc.l    0
vcols:  dc.w    0
vrows:  dc.w    0
vx:     dc.w    0
vnp:    dc.w    0
