; Micro-benchmarks for the proposed HUD kernels (interrupts OFF, pure cycle counts), run with work/sprite/unit.py.
; Every m_* label is a marker; each block runs N calls between two markers.
N       equ     99                      ; dbra count -> 100 calls
SCR     equ     $C8000
STRIP   equ     $D0000
OUT     equ     $D8000
        org     $C0000
ROW     macro
        move.l  (a1)+,d0
        movep.l d0,\1(a0)
        endm
ROWB    macro                           ; byte-store variant: 4 move.b per row
        move.b  (a1)+,\1(a0)
        move.b  (a1)+,\1+2(a0)
        move.b  (a1)+,\1+4(a0)
        move.b  (a1)+,\1+6(a0)
        endm
start:  movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        move.w  #$2700,sr
        lea     STRIP.l,a0
        move.w  #4095,d0
        move.l  #$12345678,d1
.f:     move.l  d1,(a0)+
        add.l   #$01234567,d1
        dbra    d0,.f
        lea     SCR.l,a0
        move.w  #7999,d0
.g:     move.l  d1,(a0)+
        add.l   #$01234567,d1
        dbra    d0,.g
; ---- K1: 14-row movep glyph (odd byte address), jsr/rts + lea setup included
m_k1a:  nop
        moveq   #N,d7
.k1:    lea     STRIP.l,a1
        lea     SCR+161.l,a0
        jsr     g14
        dbra    d7,.k1
m_k1b:  nop
; ---- K2: 8-row movep glyph
m_k2a:  nop
        moveq   #N,d7
.k2:    lea     STRIP.l,a1
        lea     SCR+161.l,a0
        jsr     g8
        dbra    d7,.k2
m_k2b:  nop
; ---- K3: 14-row byte-store glyph
m_k3a:  nop
        moveq   #N,d7
.k3:    lea     STRIP.l,a1
        lea     SCR+160.l,a0
        jsr     g14b
        dbra    d7,.k3
m_k3b:  nop
; ---- K4: 16x16 dial copy (move.l pairs)
m_k4a:  nop
        moveq   #N,d7
.k4:    lea     STRIP.l,a1
        lea     SCR+8.l,a0
        jsr     dial
        dbra    d7,.k4
m_k4b:  nop
; ---- K5: word -> 5 decimal digits, 5 x divu #10
m_k5a:  nop
        moveq   #N,d7
.k5:    move.w  #$ff12,d0
        lea     OUT+8.l,a2
        jsr     bin5
        dbra    d7,.k5
m_k5b:  nop
; ---- K6: sky clear, rows of 160 B x 49 with movem (7840 B), once (not 100x)
m_k6a:  nop
        jsr     skyclr
m_k6b:  nop
; ---- K7: 2240 B copy with movem (load 14 regs, store 14 regs)
m_k7a:  nop
        jsr     copy2240
m_k7b:  nop
        move.w  #$2700,sr
        move.l  #'DONE',$C0FF0.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        move.l  #$4eb90000,$7b74.w
        move.w  #$d1e4,$7b78.w
        jmp     $d1e4.l
g14:
n       set     0
        rept    14
        ROW     n*160
n       set     n+1
        endr
        rts
g8:
n       set     0
        rept    8
        ROW     n*160
n       set     n+1
        endr
        rts
g14b:
n       set     0
        rept    14
        ROWB    n*160
n       set     n+1
        endr
        rts
dial:
        rept    16
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     152(a0),a0
        endr
        rts
bin5:   andi.l  #$ffff,d0
        moveq   #4,d3
.l:     divu    #10,d0
        swap    d0
        move.b  d0,-(a2)
        clr.w   d0
        swap    d0
        dbra    d3,.l
        rts
skyclr: movem.l d0-d7/a1-a6,-(a7)
        moveq   #-1,d0
        move.l  d0,d1
        move.l  d0,d2
        move.l  d0,d3
        move.l  d0,d4
        move.l  d0,d5
        move.l  d0,d6
        move.l  d0,d7
        move.l  d0,a1
        move.l  d0,a2
        move.l  d0,a3
        move.l  d0,a4
        move.l  d0,a5
        move.l  d0,a6
        lea     SCR+160*65.l,a0         ; fill downwards: -(a0)
        moveq   #139,d7                 ; 140 x 56 B = 7840 B  (d7 is also in the movem list: re-set)
        lea     .cnt(pc),a1
        move.w  #139,(a1)
.lp:    movem.l d0-d6/a2-a6,-(a0)       ; 12 regs = 48 B  (a1/d7 are used as counter pointers)
        subq.w  #1,(a1)
        bpl.s   .lp
        movem.l (a7)+,d0-d7/a1-a6
        rts
.cnt:   dc.w    0
copy2240:
        movem.l d0-d7/a1-a6,-(a7)
        lea     STRIP.l,a1
        lea     SCR.l,a0
        moveq   #39,d7
.c:     movem.l (a1)+,d0-d6/a2-a6       ; 12 regs = 48 B
        movem.l d0-d6/a2-a6,(a0)
        lea     48(a0),a0
        dbra    d7,.c
        movem.l (a7)+,d0-d7/a1-a6
        rts
