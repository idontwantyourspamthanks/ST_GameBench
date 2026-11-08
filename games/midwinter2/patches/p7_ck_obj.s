; name: p7_ck_obj
; default: yes
; site: $3bb6e
; orig: 48e7fffe33fcf000000180ec
; note: P7 item 1, object path (work/notes/p7_cockpit_cull.md).  Object polygon rasteriser $3bb6e (only
;       caller: the draw-queue pop loop $38b8c, a0-a3 = [$67f0]; polygon index at $17a60; the
;       polygon is a ring of half-edges: first edge = 2(a0,$17a60), next = 2(a1,e), vertex of edge e
;       = (a3, (a2, (a1,e))) = x.w, y.w in draw coordinates, already clipped by the object clip).
;       Skips a polygon that lies wholly under opaque cockpit pixels before its edges are walked and
;       filled.  Active only inside a terrain pass (EN, p7_ck_enter: objects are drawn from the terrain
;       stream, $1fbcc -> $1c3fc).  Walks the ring once; leaves at the first vertex above row KR0
;       (the common case: ~60 cycles), otherwise bbox [xmin-1, xmax+1] x [ymin, ymax] and the same one
;       lookup in the F table (XTAB) as p7_ck_poly.  A culled polygon still replays the state the
;       original leaves for the next one ($180ec = $f000, $180ee = $1000, $17a5e = 0; the next
;       polygon re-initialises them) and returns with all registers restored.
;       Displaces `movem.l d0-d7/a0-a6,-(a7) ; move.w #$f000,$180ec.l` (12 bytes) and rejoins at $3bb7a.
EN      equ     $b5000
XTAB    equ     $b5020
KR0     equ     176
NR      equ     24

        org     $3bb6e
        jmp     $b5620.l
        dcb.w   3,$4e71

        org     $b5620
        movem.l d0-d7/a0-a6,-(a7)       ; displaced
        move.w  #$f000,$180ec.l         ; displaced
        tst.w   EN.l
        beq.w   .go
        move.w  $17a60.l,d7
        move.w  2(a0,d7.w),d7           ; first half-edge, as $3bb8e
        move.w  d7,d6
        move.w  #$7fff,d0               ; xmin
        move.w  #-$8000,d1              ; xmax
        move.w  #$7fff,d2               ; ymin
.v:     move.w  (a1,d6.w),d5
        move.w  (a2,d5.w),d4
        move.w  2(a3,d4.w),d5           ; y
        cmp.w   #KR0,d5
        blt.w   .go                     ; above the first dashboard row: not wholly under
        cmp.w   d2,d5
        bge.s   .a
        move.w  d5,d2
.a:     move.w  (a3,d4.w),d5            ; x
        cmp.w   d0,d5
        bge.s   .b
        move.w  d5,d0
.b:     cmp.w   d1,d5
        ble.s   .c
        move.w  d5,d1
.c:     move.w  2(a1,d6.w),d6
        cmp.w   d6,d7
        bne.s   .v
        sub.w   #KR0,d2
        lsl.w   #3,d2                   ; F row offset of ymin
        cmp.w   #NR*8,d2
        bcc.w   .go
        subq.w  #1,d0                   ; X0p
        bmi.w   .go
        addq.w  #1,d1                   ; X1p
        lea     XTAB.l,a6
        adda.w  d2,a6
        cmp.w   (a6),d0
        blt.s   .m1
        cmp.w   2(a6),d1
        ble.s   .cull
.m1:    cmp.w   4(a6),d0
        blt.w   .go
        cmp.w   6(a6),d1
        bgt.w   .go
.cull:  move.w  #$1000,$180ee.l
        clr.w   $17a5e.l
        movem.l (a7)+,d0-d7/a0-a6
        rts
.go:    jmp     $3bb7a.l
