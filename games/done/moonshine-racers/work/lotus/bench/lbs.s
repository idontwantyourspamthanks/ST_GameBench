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

; d0 = x, d1 = y ; vcols, vrows, vnp
draw:   movem.l d0-d7/a0-a6,-(a7)
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
        move.w  vcols,d3                ; c
        move.w  d3,d4                   ; n = c (+1 if shifted)
        tst.w   d2
        beq.s   .al
        addq.w  #1,d4
.al:    move.w  vnp,d5
        add.w   d5,d5
        addq.w  #2,d5                   ; stride = 2 * (np + 1)
        lea     BL.l,a3
        move.w  d5,$20(a3)              ; src xinc
        move.w  d5,d0
        mulu.w  d3,d0                   ; stride * c
        move.w  d4,d1
        subq.w  #1,d1
        mulu.w  d5,d1                   ; stride * (n - 1)
        sub.w   d1,d0
        move.w  d0,$22(a3)              ; src yinc
        moveq   #-1,d0
        lsr.w   d2,d0                   ; em1 = $ffff >> s
        move.w  d0,$28(a3)
        move.w  #$ffff,$2a(a3)
        moveq   #-1,d0
        tst.w   d2
        beq.s   .em3
        moveq   #16,d1
        sub.w   d2,d1
        lsl.w   d1,d0                   ; em3 = $ffff << (16 - s)
.em3:   move.w  d0,$2c(a3)
        move.w  #8,$2e(a3)              ; dst xinc
        move.w  d4,d0
        subq.w  #1,d0
        lsl.w   #3,d0
        move.w  #160,d1
        sub.w   d0,d1
        move.w  d1,$30(a3)              ; dst yinc = 160 - 8 (n - 1)
        move.w  d4,$36(a3)              ; xcount
        move.w  d2,d0
        beq.s   .sk
        or.w    #$40,d0                 ; FXSR
.sk:    move.b  d0,$3d(a3)              ; skew
        ; rows per blit k = max(1, 8 / n), chunks, remainder
        moveq   #8,d0
        divu.w  d4,d0
        and.l   #$ffff,d0
        bne.s   .k1
        moveq   #1,d0
.k1:    move.w  d0,d1                   ; k
        move.w  vrows,d0
        ext.l   d0
        divu.w  d1,d0                   ; d0.w = chunks, d0 high = remainder
        move.w  d0,d3                   ; chunks
        swap    d0
        move.w  d0,d7                   ; remainder rows
        lea     chain_end(pc),a0
        add.w   d3,d3
        add.w   d3,d3                   ; 4 bytes per pair
        suba.w  d3,a0
        movea.l a0,a4                   ; a4 = chain entry
        lea     $38(a3),a2              ; a2 = ycount
        lea     $3c(a3),a6              ; a6 = control
        lea     $24(a3),a0              ; a0 = src addr reg  (a3 base kept)
        lea     $32(a3),a5              ; a5 = dst addr reg
        moveq   #0,d6
        move.b  #$c0,d6
        lea     DAT.l,a3                ; source: mask word of the first word
        move.l  a3,d3                   ; d3 = src base (mask)
        move.w  #$0201,$ffff8a3a.w      ; HOP 2 / LOP 1 (AND)
        moveq   #3,d5                   ; 4 mask passes
        movea.l a1,a3                   ; a3 = dst plane 0 (moved by 2 each pass)
.mp:    move.l  d3,(a0)
        move.l  a3,(a5)
        bsr.s   pass
        addq.l  #2,a3
        dbra    d5,.mp
        move.w  #$0207,$ffff8a3a.w      ; LOP 7 (OR)
        movea.l a1,a3
        move.l  d3,d5
        addq.l  #2,d5                   ; first plane word
        move.w  vnp,d3
        subq.w  #1,d3
.dp:    move.l  d5,(a0)
        move.l  a3,(a5)
        bsr.s   pass
        addq.l  #2,d5
        addq.l  #2,a3
        dbra    d3,.dp
        movem.l (a7)+,d0-d7/a0-a6
        rts

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
