; name: pop2_tt_ptr
; default: yes
; site: $1c16
; orig: e04821c08200
; data: PB+$6fa0 1
; note: TT / Falcon (68020+): the pointer is invisible on the main menu and flickers elsewhere, work/notes/tt_pointer.md.
; note: The game's flip $1bfe swaps $392e0 / $392dc (the buffer just rendered becomes the shown one, $392dc) and writes the new base with `lsr.w #8,d0 /
; note: move.l d0,$8200.w` ($1c16-$1c1b).  The VBL handler $18fa draws the pointer into the shown buffer [$392dc].  An ST / STE / Mega STE latches the base at
; note: the next frame start, so the VBL's draw lands in the buffer shown in that frame.  Hatari's TT / Falcon video takes the new base at once: the buffer
; note: the flip switches to holds no pointer until the next VBL draws it, and the menu flips every VBL (241 flips per 250 VBL), so the picture never shows it.
; note: Fix, 68020+ only: this hook (all 15 callers of $1bfe pass through it) runs the VBL handler's own pointer code with the VBL masked, BEFORE the base is
; note: written: it keeps a copy of the save area $2032 and of the old rectangle ([$202e], stride $2234, rows $2232), draws the pointer into the new [$392dc]
; note: ($1a4e-$1b30, which also sets $202e / $2232 / $2234 / $2032 for the new rectangle), then writes the base (the displaced `lsr.w #8,d0 / move.l d0,$8200.w`) and
; note: only then restores the old rectangle from the copy.  (Restoring first, as the handler does, erased the pointer from the still shown buffer for the blob's
; note: ~0.3 ms: on the TT a screenshot of the panel caught one frame in 12 without it.)  The next VBL handler restores and redraws exactly as after any flip
; note: (pop2_ptr_a/b's skip test compares the screen against its record, so a draw made here is never mistaken).
; note: Skipped while the pointer is hidden ($2246 != 0, the handler's own test).  The handler's 60 Hz test ($1a68, pop2_ntsc2) is not copied.
; note: Machine test on the first call: the index-register scale trick of Midwinter 2's p8_tt_ptr (68000/68010 ignore the scale bits of a brief extension
; note: word, a 68020+ applies them; no exception, no cookie jar).  On a 68000 / 68010 (ST, STE, Mega STE) the first call writes the six original bytes back
; note: to the site, so those machines run the unpatched flip from then on.  TT_F byte at PB+$6fa0: 0 unprobed, 1 68000/68010, 2 68020+.
TT_F    equ     PB+$6fa0
TTP     equ     PB+$6600

        org     $1c16
        jsr     TTP.l

        org     PB+$6600
ttp:    movem.l d0-d7/a0-a6,-(a7)
        move.b  TT_F.l,d1
        bne.s   .known
        moveq   #1,d0                   ; first call: classify the CPU (cpulib.s cl_detect)
        dc.w    $41fb,$0200             ; lea     (0,pc,d0.w*2),a0
        dc.w    $43fb,$0000             ; lea     (0,pc,d0.w),a1  (4 bytes behind the first: a1-a0 = 4 when the scale is ignored, 3 with scale 2)
        suba.l  a0,a1
        move.l  a1,d1
        moveq   #1,d2                   ; 1 = 68000 / 68010
        cmp.l   #4,d1
        beq.s   .set
        moveq   #2,d2                   ; 2 = 68020+
.set:   move.b  d2,TT_F.l
        move.b  d2,d1
.known: cmp.b   #2,d1
        beq.s   .tt
        move.l  #$e04821c0,$1c16.l      ; 68000 / 68010: the original `lsr.w #8,d0 / move.l d0,$8200.w` back, unpatched from now on
        move.w  #$8200,$1c1a.l
        bra.w   .out
.tt:    tst.w   $2246.l                 ; pointer hidden: the handler draws nothing
        bne.w   .out
        move.w  sr,-(a7)
        ori.w   #$0400,sr               ; the VBL handler (level 4) cannot interleave
        movea.l $202e.l,a5              ; the old rectangle (in the buffer still shown), restored AFTER the base write: it keeps its pointer until then
        lea     -260(a7),a7             ; copy of the save area $2032 (256 B) + stride + rows of the old rectangle
        lea     $2032.l,a0
        movea.l a7,a1
        moveq   #63,d0
.cp:    move.l  (a0)+,(a1)+
        dbra    d0,.cp
        move.w  $2234.l,(a1)+
        move.w  $2232.l,(a1)+
.draw:  move.w  $393fa.l,d1             ; --- $1a4e-$1b30: save + draw into [$392dc]
        move.w  $393fc.l,d2
        move.w  #$f,d7
        subi.w  #$b8,d2
        ble.w   .y
        sub.w   d2,d7
.y:     move.w  d7,$2232.l
        move.w  #$90,d6
        cmpi.w  #$130,d1
        ble.w   .x
        move.w  #$98,d6
.x:     move.w  d6,$2234.l
        move.w  $393fc.l,d2
        movea.l $392dc.l,a4
        move.w  d1,d5
        andi.w  #$f,d5
        andi.w  #$fff0,d1
        lsr.w   #1,d1
        mulu.w  #$a0,d2
        ext.l   d1
        add.l   d1,d2
        adda.l  d2,a4
        move.l  a4,$202e.l
        lea     $682d0.l,a3
        move.w  $11d50.l,d0
        adda.w  d0,a3
        lea     $2032.l,a6
.pl:    moveq   #0,d1
        move.w  (a3)+,d1
        moveq   #0,d2
        move.w  (a3)+,d2
        moveq   #0,d3
        move.w  (a3)+,d3
        moveq   #0,d4
        move.w  (a3)+,d4
        ror.l   d5,d1
        ror.l   d5,d2
        ror.l   d5,d3
        ror.l   d5,d4
        move.l  d1,d0
        or.l    d2,d0
        or.l    d3,d0
        or.l    d4,d0
        not.l   d0
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d1,(a4)+
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d2,(a4)+
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d3,(a4)+
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d4,(a4)+
        cmpi.w  #$90,d6
        bne.w   .pn
        swap    d0
        swap    d1
        swap    d2
        swap    d3
        swap    d4
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d1,(a4)+
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d2,(a4)+
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d3,(a4)+
        move.w  (a4),(a6)+
        and.w   d0,(a4)
        or.w    d4,(a4)+
.pn:    adda.w  d6,a4
        dbra    d7,.pl
.bw:    move.l  262(a7),d0              ; the displaced base write (d0 = the buffer to be shown, as the movem pushed it)
        lsr.w   #8,d0
        move.l  d0,$ffff8200.w
        move.l  a5,d0                   ; --- $1a1a-$1a4a: restore the old rectangle (the buffer no longer shown) from the copy
        beq.w   .done
        movea.l a5,a4
        movea.l a7,a6
        move.w  256(a7),d6
        move.w  258(a7),d7
.rl:    move.l  (a6)+,(a4)+
        move.l  (a6)+,(a4)+
        cmpi.w  #$90,d6
        bne.w   .rn
        move.l  (a6)+,(a4)+
        move.l  (a6)+,(a4)+
.rn:    adda.w  d6,a4
        dbra    d7,.rl
.done:  lea     260(a7),a7
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        lsr.w   #8,d0                   ; the displaced `lsr.w #8,d0` (d0 as the original leaves it; the base is already written)
        rts
.out:   movem.l (a7)+,d0-d7/a0-a6
        lsr.w   #8,d0                   ; the displaced instructions (68000 / 68010 path, hidden pointer)
        move.l  d0,$ffff8200.w
        rts
