; name: mr_edge
; default: yes
; site: $17c4a
; orig: 49f90001058a
; doc: Faster road edge-colour routine (pixel-identical): the 16 tst/or tests of $1058a become one of 8 generated straight-line code slots per frame.
; note: Moonshine Racers render speed-up 1 (work/notes/render_patches.md).  Site: $17c4a `lea.l $1058a.l,a4` in the road span draw $17c42 -> `jsr $B3040.l`.
; note: $1058a (called ~153 times a frame through `jsr (a4)`) expands the colour table at (a5)=($135a) (6 colours x 4 plane words, tested with `tst.w`) into the four plane words
; note: d0/d2/d4/d6 of a 16-pixel group, selected by bits 15/13/14 of d7.  The table is static, so the hook builds, when ($135a) changes, 8 slots (one per bit combination of d7 bits
; note: 15,14,13) of 32 bytes behind the dispatcher: straight-line `move.l/or.l/moveq` code that computes the same four outputs, then flushes the 68020+ caches.  The hook sets a4 to the
; note: dispatcher ($B30xx) which indexes the slot by d7 and jumps into it.  The stock routine at $1058a is untouched (the reload `movea.l $1356.l,a4` at $18040 still gets it,
; note: together with a5 = ($135e): every path stays consistent).  Registers d1/d3/d5/d7 and a-regs are preserved exactly as the stock routine (only d0/d2/d4/d6 change).
        org     $17c4a
        jsr     $B3040.l

        org     $B3040
edgeinit:
        lea     fast(pc),a4             ; the displaced `lea $1058a.l,a4`, now the fast routine
        move.l  d0,-(a7)
        move.l  $135a.w,d0              ; the colour table pointer of this frame
        cmp.l   lastptr.l,d0
        beq.s   .done
        move.l  d0,lastptr.l
        movem.l d1-d7/a0-a3/a5/a6,-(a7)
        movea.l d0,a0
        bsr.s   gen
        bsr.w   cflush
        movem.l (a7)+,d1-d7/a0-a3/a5/a6
.done:  move.l  (a7)+,d0
        rts

; gen: a0 = colour table; writes the 8 slots.  trashes d0-d7/a1-a3/a5/a6
gen:    lea     slots(pc),a1
        moveq   #0,d6                   ; slot number c = bits 15,14,13 of d7
.slot:  movea.l a1,a2                   ; write pointer
        movea.l a0,a3                   ; A group: d7 bit 15 set -> +8
        btst    #2,d6
        beq.s   .a
        addq.l  #8,a3
.a:     lea     $10(a0),a5              ; C group: d7 bit 14 set -> $18 instead of $10
        btst    #1,d6
        beq.s   .c
        addq.l  #8,a5
.c:     lea     $20(a0),a6              ; B group: d7 bit 13 set -> $28 instead of $20
        btst    #0,d6
        beq.s   .b
        addq.l  #8,a6
.b:     move.w  #$2f01,(a2)+            ; move.l d1,-(a7)
        moveq   #0,d7                   ; output k = 0..3 (d0,d2,d1(=d4 later),d6)
.k:     moveq   #0,d1                   ; flags: bit0 A (in d4), bit1 B (d5), bit2 C (in d6)
        tst.w   (a3)+
        beq.s   .f1
        moveq   #1,d1
.f1:    tst.w   (a6)+
        beq.s   .f2
        or.b    #2,d1
.f2:    tst.w   (a5)+
        beq.s   .f3
        or.b    #4,d1
.f3:    moveq   #0,d2                   ; d2 = 0: first op must be an assignment
        move.w  d7,d0
        add.w   d0,d0
        move.w  rtab(pc,d0.w),d0        ; destination register number << 9
        cmp.w   #3,d7
        bne.s   .e
        btst    #2,d1                   ; output 6 is built in place in d6: its own colour is already there
        beq.s   .e
        moveq   #1,d2
        and.b   #3,d1
.e:     bsr.s   emit
        addq.w  #1,d7
        cmp.w   #4,d7
        bne.s   .k
        move.w  #$2801,(a2)+            ; move.l d1,d4
        move.w  #$221f,(a2)+            ; move.l (a7)+,d1
        move.w  #$4e75,(a2)+            ; rts
        lea     $20(a1),a1
        addq.w  #1,d6
        cmp.w   #8,d6
        bne.s   .slot
        rts
rtab:   dc.w    0,$400,$200,$c00        ; d0, d2, d1, d6

; emit: d0 = dest reg << 9, d1 = source flags, d2 = 1 if the dest already holds a source; a2 = write pointer.  trashes d3/d4
emit:   moveq   #4,d3                   ; source register: d4, d5, d6
.l:     lsr.b   #1,d1
        bcc.s   .n
        move.w  d3,d4
        tst.b   d2
        bne.s   .or
        or.w    #$2000,d4               ; move.l Ds,Dr
        or.w    d0,d4
        move.w  d4,(a2)+
        moveq   #1,d2
        bra.s   .n
.or:    or.w    #$8080,d4               ; or.l Ds,Dr
        or.w    d0,d4
        move.w  d4,(a2)+
.n:     addq.w  #1,d3
        cmp.w   #7,d3
        bne.s   .l
        tst.b   d2
        bne.s   .r
        move.w  d0,d4
        or.w    #$7000,d4               ; moveq #0,Dr
        move.w  d4,(a2)+
.r:     rts

; cflush: flush the 68020+ caches (same code as core.s: the slots were just written as data).  68000/68010: nothing.  Trashes d0-d2/a0-a1
cflush: moveq   #1,d0
        dc.w    $41fb,$0200             ; lea     (0,pc,d0.w*2),a0
        dc.w    $43fb,$0000             ; lea     (0,pc,d0.w),a1
        suba.l  a0,a1
        move.l  a1,d1
        cmp.l   #4,d1
        beq.s   .r                      ; 68000/68010
        move.l  $5a0.w,d1
        beq.s   .c030
        movea.l d1,a0
.ck:    move.l  (a0)+,d1
        beq.s   .c030
        move.l  (a0)+,d2
        cmp.l   #'_CPU',d1
        bne.s   .ck
        cmp.l   #40,d2
        blt.s   .c030
        dc.w    $f4f8                   ; cpusha  bc
        rts
.c030:  dc.w    $4e7a,$1002             ; movec   cacr,d1
        ori.l   #$0808,d1               ; CI + CD
        dc.w    $4e7b,$1002             ; movec   d1,cacr
.r:     rts

; dispatcher: d7 bits 15,14,13 pick the slot (32 B each, generated code, directly behind: the jump's index displacement is 8 bit)
fast:   move.w  d7,d0
        lsr.w   #8,d0
        and.w   #$e0,d0
        jmp     slots(pc,d0.w)
slots:  ds.b    256
lastptr: dc.l   0
