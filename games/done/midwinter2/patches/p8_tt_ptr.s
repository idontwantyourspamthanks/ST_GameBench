; name: p8_tt_ptr
; default: yes
; site: $26ea2
; orig: 41f900ff8201
; data: $b4f80 2
; note: TT / Falcon (68020+): the menu pointer was invisible on the island MAP screens (Raids map, campaign Control map), see work/notes/map_pointer.md.
;       The game's pointer is drawn by the VBL handler's mode 0/1 routine ($264f0 -> $266d4) into the DISPLAYED buffer $67aa, and the 2D screens'
;       main loops flip with $26e98 (writes the new base to $ff8201/03 with `movep`, then swaps $770e/$7712 and sets $67a6/$67aa).  On an ST / STE
;       the shifter latches the base at the start of the next frame, so the buffer the VBL handler draws into IS the one displayed in that frame.
;       Hatari's TT/Falcon video takes the new base at once: when the map loop flips about once per frame (it does as soon as its fade-in /
;       "SELECT MISSION" caption phase is over) the display is switched to the buffer that holds no pointer yet, for the whole frame.
;       Fix, 68020+ only: before the base is written, run the pointer's restore + draw ($2684e, then the mode routine $264f0 = what the VBL
;       handler does, with $67aa := the buffer about to be shown) with the VBL masked (SR IPL 4, the handler's own level).  The pointer is then
;       already in the buffer when it goes on the display; the next VBL handler restores and redraws as usual (identical record handling).
;       Only in modes 0/1 ($700a < 2: the 2D screens); the 3D view (mode 2) takes the plain path.
;       The site is the first instruction `lea $ff8201.l,a0` of the base write (d0 = the buffer to be shown, not yet shifted); the blob re-executes it.
;       Machine test: the first call classifies the CPU with the index-register scale trick of cpulib.s `cl_detect` (a 68000/68010 ignores the scale
;       bits of a brief extension word, a 68020+ applies them; no exception, no cookie jar: on a HD boot HAGA remaps low RAM on a TT so $5a0 must
;       not be read).  On a 68000/68010 (ST, STE, Mega STE) the blob writes the 6 original bytes back to the site, so those machines run the
;       unpatched flip after the first call (0 cycles, byte-identical).  TT_F ($b4f80 byte): 0 not probed, 1 68000/68010, 2 68020+.
TT_F    equ     $b4f80

        org     $26ea2
        jsr     $b4f00.l

        org     $b4f00
tt_ptr: movem.l d0-d7/a0-a6,-(a7)       ; d0 (= the buffer to be shown) is at (a7)
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
        move.l  #$41f900ff,$26ea2.l     ; 68000 / 68010: put the original `lea $ff8201.l,a0` back, the flip runs unpatched from now on
        move.w  #$8201,$26ea6.l
        bra.s   .out
.tt:    cmpi.w  #2,$700a.w              ; modes 0/1 = the 2D screens with the menu pointer
        bcc.s   .out
        move.w  sr,-(a7)
        ori.w   #$0400,sr               ; VBL / HBL cannot interleave (the handler's own level); ACIA / MFP still can, as in the handler
        move.l  2(a7),$67aa.w           ; the pointer is drawn into the buffer that is about to be shown (the flip sets the same value next)
        tst.w   $6fc2.w                 ; the VBL handler's own sequence: restore the saved lines ...
        beq.s   .nr
        jsr     $2684e.l
        clr.w   $6fc2.w
.nr:    jsr     $264f0.l                ; ... then the mode 0/1 routine: sets $6fc2, clamps, saves and draws (ends in rts)
        move.w  (a7)+,sr
.out:   movem.l (a7)+,d0-d7/a0-a6
        lea     $ff8201.l,a0            ; displaced
        rts
