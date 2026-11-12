; name: p7_ck_poly
; default: yes
; site: $1fa9a
; orig: 4a416700000e
; phase: deferred
; note: P7 item 1 (work/notes/p7_cockpit_cull.md), part 4/5.  Terrain stream walker $1fa54, the
;       per-polygon decision after the outcode loop: `tst.w d1 ; beq.w $1faac` (d1 = OR, d2 = AND
;       of the vertex outcodes).  Rejects a clipped polygon that lies wholly under opaque cockpit
;       pixels BEFORE its edges are clipped, walked and filled.
;       Candidates: EN = 1 (p7_ck_enter) and OR = $0101 exactly (every outside vertex lies only
;       below the window bottom: -W <= X <= W, W > 0, Y' < -W; no vertex above, left, right or
;       behind), AND = 0.  Measured: the polygons wholly under the cockpit are the ones clipped at
;       the bottom edge (work/notes/p7_cockpit_cull.md); a polygon with a left/right/top outside
;       vertex always has pixels at x = 1/319 or above the cockpit, so skipping them loses nothing.
;       Test: bbox of the projected polygon in draw coordinates (x = 160 - sx, y = 129 - sy) from
;       the in-window vertices' stored (sx, sy) and, for the outside vertices, sx = X*159/W with the
;       game's own muls/divs ($1fa40-$1fa46; sy is irrelevant: they are below the bottom, the bbox
;       bottom is row 199).  Padded by PADX px left/right (rounding of the clip intersections, whose
;       y is exactly the bottom boundary; the top row is an in-window vertex's exact y, PADY = 0).
;       The polygon is culled iff [X0p, X1p] lies inside one run of the F table row Y0 (XTAB after
;       p7_ck_tab: the columns that are opaque in every row Y0..199) - one lookup instead of a row
;       loop.  Checked first with the in-window vertices only (no divide needed to reject), then with
;       the outside vertices added.  Rejects early if an in-window vertex lies above the first
;       dashboard row (sy > SYT) or Y0 < KR0.
;       Row 200 (below the window bottom) is not tested: the original also draws it (into the bytes
;       after the screen, $67d00 / $77d00) and nothing reads it.
;       Register use: d0-d6 and a6 (restored) are dead at $1fa9a (d5, d6 are only written later
;       on every path; d7, a4, a5 untouched).
EN      equ     $b5000
SYT     equ     $b5004
XTAB    equ     $b5020
KR0     equ     176
NR      equ     24
PADX    equ     2

        org     $1fa9a
        jmp     $b54ee.l

        org     $b54ee
FCHK    macro                           ; d5 = X0p, d6 = X1p (inclusive), d4 = F row offset
        lea     XTAB.l,a6               ; -> .rej unless inside one run
        adda.w  d4,a6
        cmp.w   (a6),d5
        blt.s   .m1\@
        cmp.w   2(a6),d6
        ble.s   .m2\@
.m1\@:  cmp.w   4(a6),d5
        blt.w   .rej
        cmp.w   6(a6),d6
        bgt.w   .rej
.m2\@:
        endm

POLY:   tst.w   d1
        beq.s   .in
        cmp.w   #$0101,d1
        beq.s   .cand
.fb:    jmp     $1faa0.l                ; original: tst.w d2 ; bne.w $1fa5e ; bra.w $1fad4
.in:    jmp     $1faac.l                ; original: beq.w $1faac
.cand:  tst.w   EN.l
        beq.s   .fb
        tst.w   d2
        bne.s   .fb
        bsr.s   test
        bne.s   .nc
        jmp     $1fa5e.l                ; culled: next polygon
.nc:    jmp     $1fad4.l                ; clipped, not culled: original path

; test: Z = 1 -> polygon wholly under the cockpit.  a6 preserved, d0-d6 clobbered.
test:   move.l  a6,-(a7)
        lea     2(a4,d7.w),a6
        move.w  SYT.l,d6
        move.w  #$7fff,d0               ; sxmin
        move.w  #-$8000,d1              ; sxmax
        move.w  #-$8000,d3              ; symax (topmost in-window vertex)
.v:     move.w  (a6)+,d4
        beq.s   .vd
        tst.w   4(a4,d4.w)
        bne.s   .v
        move.w  2(a4,d4.w),d2           ; in-window vertex: stored sy, sx
        cmp.w   d6,d2
        bgt.w   .rej                    ; above the first dashboard row
        cmp.w   d3,d2
        ble.s   .a
        move.w  d2,d3
.a:     move.w  (a4,d4.w),d2
        cmp.w   d0,d2
        bge.s   .b
        move.w  d2,d0
.b:     cmp.w   d1,d2
        ble.s   .v
        move.w  d2,d1
        bra.s   .v
.vd:    cmp.w   #$7fff,d0
        beq.w   .rej
        move.w  #129-KR0,d4
        sub.w   d3,d4                   ; Y0 - KR0
        bmi.w   .rej
        lsl.w   #3,d4                   ; F row offset
        cmp.w   #NR*8,d4                ; Y0 = 200 (sy = -71): no table row
        bcc.w   .rej
        move.w  #160-PADX,d5
        sub.w   d1,d5                   ; X0p
        bmi.w   .rej
        move.w  #160+PADX,d6
        sub.w   d0,d6                   ; X1p
        FCHK                            ; in-window vertices only
        lea     2(a4,d7.w),a6
.w:     move.w  (a6)+,d2
        beq.s   .wd
        tst.w   4(a4,d2.w)
        beq.s   .w
        move.w  $a(a4,d2.w),d3          ; outside vertex: W
        ble.w   .rej
        move.w  6(a4,d2.w),d2
        muls.w  $1fbd6.l,d2
        divs.w  d3,d2                   ; sx = X*159/W (|X| <= W: no overflow)
        cmp.w   d0,d2
        bge.s   .w1
        move.w  d2,d0
.w1:    cmp.w   d1,d2
        ble.s   .w
        move.w  d2,d1
        bra.s   .w
.wd:    move.w  #160-PADX,d5
        sub.w   d1,d5
        bmi.w   .rej
        move.w  #160+PADX,d6
        sub.w   d0,d6
        FCHK
        movea.l (a7)+,a6
        moveq   #0,d0
        rts
.rej:   movea.l (a7)+,a6
        moveq   #1,d0
        rts
