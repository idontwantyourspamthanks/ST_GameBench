; name: p8_fill_fast
; default: yes
; site: $1b1ee
; orig: 30390001a942
; data: $b7400 1680
; note: Fast polygon span fill + flat non-dithered LOW detail mode.
; note: Two zero-overhead entry points (selected by p8_det_key patching $1b1f0):
; note:   $B7160 (HIGH/MEDIUM exact): single-pass solid fill for solid polys + once-per-poly dither mix for checkerboards.
; note:   $B7180 (LOW flat): maps every shade-table entry [A0,B0,A1,B1] to solid colour A1 -> single-pass solid filler!
; note: First call runs .do_init once, cloning the 16 specialized solid variants ($1aa44..$1b08b) to $B7400
; note: as single-pass fillers and self-patching the init check at $B7160/$B7180 to NOPs (0 cy overhead afterwards!).
CLONE   equ     $b7400
CLTAB   equ     $b7a50
SRC0    equ     $1aa44
SRCEND  equ     $1b08c
DELTA   equ     CLONE-SRC0

        org     $1b1ee
        jmp     $b71c0.l

        org     $b71c0
exact_entry:
        bsr.w   do_init                 ; self-patched to NOP,NOP on first call!
        move.w  $1a942.l,d0
        asl.w   #2,d0
        lea     $1b340.l,a5
        move.l  (a5,d0.w),d0            ; d0 = [A0,B0,A1,B1]
        bra.s   exact_body
        dcb.b   $b71e0-*,0
low_entry:
        bsr.w   do_init                 ; self-patched to NOP,NOP on first call!
        move.w  $1a942.l,d0
        asl.w   #2,d0
        lea     $1b340.l,a5
        move.l  (a5,d0.w),d0            ; d0 = [A0,B0,A1,B1]
        lsr.w   #8,d0                   ; take A1 (byte +2) as nearest solid colour
        and.w   #$f,d0
        bra.s   go_solid

exact_body:
        ; Check if solid: A0 == B0 == A1 == B1
        move.w  d0,d1
        swap    d0
        cmp.w   d0,d1
        bne.s   not_solid
        move.w  d0,d1
        lsr.w   #8,d1
        cmp.b   d0,d1
        bne.w   chk_swap
        and.w   #$f,d0
go_solid:
        move.w  $1a616.l,d7             ; ymax
        move.w  $1a618.l,d3             ; ymin
        sub.w   d3,d7                   ; d7 = nrows - 1
        move.w  d3,d2
        add.w   d2,d2
        movea.l $1a61a.l,a0
        adda.w  d2,a0                   ; a0 -> span table[ymin]
        movea.l $12d0a.l,a2
        mulu.w  #$a0,d3
        adda.l  d3,a2                   ; a2 -> screen row ymin
        lea     $1a9c4.l,a6
        add.w   d0,d0
        add.w   d0,d0
        lea     CLTAB.l,a5
        movea.l (a5,d0.w),a5
        jsr     (a5)
        jmp     $1b27a.l

not_solid:
        ; d0 was swapped above: high word = [A1,B1], low word = [A0,B0]
        ; Check checkerboard: A0 == B1 && B0 == A1
        rol.w   #8,d1                   ; d1.w = [B1,A1]
        cmp.w   d0,d1
        bne.w   chk_swap
        swap    d0                      ; d0 = [A0,B0,A1,B1]
        move.w  $1a618.l,d3             ; ymin
        btst    #0,d3
        beq.s   .no_odd
        swap    d0                      ; swap (A0,B0) <-> (A1,B1)
.no_odd:
        swap    d0                      ; low word = [A0,B0]
        move.w  d0,d1
        lsr.w   #8,d0
        and.w   #$f,d0                  ; d0 = A0
        and.w   #$f,d1                  ; d1 = B0
        asl.w   #3,d0
        asl.w   #3,d1
        lea     $1b280.l,a4
        movea.l a4,a5
        adda.w  d0,a4
        adda.w  d1,a5
        movem.l (a4),d2-d3              ; cA0, cA1
        movem.l (a5),d4-d5              ; cB0, cB1
        move.l  d2,d0
        eor.l   d4,d0                   ; cA0 ^ cB0
        move.l  d3,d1
        eor.l   d5,d1                   ; cA1 ^ cB1
        move.l  #$55555555,d6
        and.l   d6,d2
        and.l   d6,d3
        not.l   d6                      ; $AAAAAAAA
        and.l   d6,d4
        and.l   d6,d5
        or.l    d2,d4                   ; d4 = P_even0
        or.l    d3,d5                   ; d5 = P_even1
        eor.l   d4,d0                   ; d0 = P_odd0
        eor.l   d5,d1                   ; d1 = P_odd1
        move.w  $1a616.l,d6             ; ymax
        move.w  $1a618.l,d3             ; ymin
        sub.w   d3,d6
        addq.w  #1,d6                   ; total rows
        move.w  d6,d7
        lsr.w   #1,d6                   ; d6 = pass2 rows
        sub.w   d6,d7
        subq.w  #1,d7                   ; d7 = pass1 dbra count
        move.w  d3,d2
        add.w   d2,d2
        movea.l $1a61a.l,a0
        adda.w  d2,a0                   ; a0 -> span table[ymin]
        movea.l $12d0a.l,a2
        mulu.w  #$a0,d3
        adda.l  d3,a2                   ; a2 -> screen row ymin
        lea     $1a9c4.l,a6
        tst.w   d6
        beq.s   .cb_one
        movem.l d0-d1/d6/a0/a2,-(a7)    ; save P_odd0, P_odd1, pass2_rows, a0, a2
        jsr     $1b12c.l                ; pass 1 with d4,d5 = P_even
        movem.l (a7)+,d4-d5/d7/a0/a2    ; d4,d5 = P_odd, d7 = pass2_rows, a0, a2
        subq.w  #1,d7
        addq.l  #2,a0
        adda.w  #$a0,a2
.cb_one:
        jsr     $1b12c.l                ; pass 2 (or sole pass 1)
        jmp     $1b27a.l

chk_swap:
        swap    d0                      ; restore d0 = [A0,B0,A1,B1]
        move.l  d0,$1b1b8.l
        jmp     $1b204.l

do_init:
        movem.l d0-d3/a0-a2,-(a7)
        lea     SRC0.l,a0
        lea     CLONE.l,a1
        move.w  #(SRCEND-SRC0)/2-1,d0
.cp:    move.w  (a0)+,(a1)+
        dbra    d0,.cp
        lea     CLONE.l,a0
        lea     CLONE+(SRCEND-SRC0).l,a1
.scan:  cmpa.l  a1,a0
        bcc.s   .mktab
        move.w  (a0)+,d0
        cmpi.w  #$5888,d0
        bne.s   .chk140
        move.w  #$5488,-2(a0)
        bra.s   .scan
.chk140:
        cmpi.w  #$45ea,d0
        bne.s   .chka5
        cmpi.w  #$0140,(a0)
        bne.s   .scan
        move.w  #$00a0,(a0)+
        bra.s   .scan
.chka5: cmpi.w  #$4bf9,d0
        bne.s   .scan
        move.l  (a0),d1
        addi.l  #DELTA,d1
        move.l  d1,(a0)+
        bra.s   .scan
.mktab: lea     $1b300.l,a0
        lea     CLTAB.l,a1
        moveq   #15,d0
.mt:    move.l  (a0)+,d1
        addi.l  #DELTA,d1
        move.l  d1,(a1)+
        dbra    d0,.mt
        ; Self-patch both `bsr.w do_init` calls to NOP,NOP
        move.l  #$4e714e71,exact_entry.l
        move.l  #$4e714e71,low_entry.l
        movem.l (a7)+,d0-d3/a0-a2
        rts
