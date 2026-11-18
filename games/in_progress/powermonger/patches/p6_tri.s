; name: p6_tri
; default: yes
; stage: 2
; site: $ef62
; orig: 4a406b00029c
; note: PMPerf2, work/notes/hotpaths2.md.  Replacement for the terrain triangle setup `$ef62` + span filler `$e3e6` on the common path.
;       Needs p6_slope (the slope table, same range: $d5000-$d8fff, code from $d9000).  Same pixels, bit for bit; the original code stays in place for everything unusual.
;       What the original does per triangle (1363 cycles of setup + a 258 cycle filler head + 306 for the run reloads, then 464-578 per scanline):
;         3 x 2 signed range tests, a sort by y, per edge a signed |dx|, dy and one of two `divu` branches (7 per call at ~130 cycles),
;         a record of 12 words written to $f1e2 and read back by the filler, then per scanline a 4 instruction DDA with swaps for each edge,
;         two run counters, a 32 cycle pattern pointer step, two table lookups and a masked read-modify-write.
;       Here: one compare+branch pair per vertex bound; the divides come from a table (p6_slope, exact: see that file) whenever |dx| and dy
;       are < 64 and from the original `divu` code otherwise; nothing is written to $f1e2; the filler runs in "chunks" (scanlines between two
;       events: end of the short edge's run = slope change, pattern ring wrap) with a plain `add.l` DDA, the pattern pointer advanced by the
;       `(a5)+` reads, `S ^ ((S ^ P) & m)` for the masked store, and the chunk list kept in static templates (TL/TR below).
;       Falls back to the ORIGINAL code (`ofb`, which re-runs the range tests and then the original setup + filler, inputs untouched) only for
;         a vertex outside 0..199 / 0..$ff0000 (the clipper).  Flat top (two vertices on the top row: the original's $f13e path), flat bottom
;         (dy1 == dy2, no third run) and triangles that wrap the pattern ring several times (`tallb`: generic chunk list) are handled here.
;       Exactness facts (each checked by tools/pmfill_test.py against the original over thousands of random views with a whole-RAM compare):
;         * after the sort d0 holds the smallest y; d1, d2 are in either order; slopes s1 (d0->d1), s2 (d0->d2): s2 == s1 draws nothing,
;           s2 > s1 puts the record's byte 0 = $1c (pattern ring $1c instead of the colour) and edge 1 on the left, s2 < s1 swaps the edges;
;         * the edge with the smaller dy runs out first and continues with the slope of the edge between the two far vertices
;           ((dx_far - dx_near) / (dy_far - dy_near), table or divu) for dy_far - dy_near steps; the fill ends at step max(dy1, dy2) without
;           drawing that step; so the triangle is `lo + 1` scanlines with the first two slopes, then `c3 - 1` with the third (lo = min dy);
;         * the pattern pointer a5 advances by 8 per scanline (4 by the `(a5)+` read, 4 by the step) except that its low 7 bits wrap inside the
;           128 byte ring: a5 -= 128 after scanline j-1 for j = 16 - (a5 & 127) / 8 when (a5 & 7) < 4 (table jtab), then every 16 scanlines;
;         * record byte 1 ($f1e3) is never written by anything (it is 0), so the low byte of the ring pointer is (y0 * 16 + [$ffa5]) & 255.
OFB     equ     $d9000
TRI     equ     $d9012
SLOPE   equ     $d5000
        org     $ef62
        jmp     TRI.l

        org     $d9000
SLOPE_  macro
        move.l  \1,\3
        swap    \3
        ext.l   \3
        bpl.s   sp\4
        neg.l   \3
sp\4:   move.w  \3,\2
        or.w    \1,\2
        cmp.w   #63,\2
        bhi.w   sl\4
        move.w  \1,\2
        lsl.w   #8,\2
        add.w   \3,\3
        add.w   \3,\3
        add.w   \3,\2
        move.l  (a1,\2.w),\2
sq\4:   tst.l   \1
        bpl.s   sr\4
        neg.l   \2
sr\4:
        endm
SLOW_   macro
sl\4:   cmp.w   \3,\1
        ble.s   sb\4
        swap    \3
        divu.w  \1,\3
        andi.l  #$ffff,\3
        bra.s   se\4
sb\4:   lsl.l   #8,\3
        divu.w  \1,\3
        bvc.s   sc\4
        move.l  #$10000,\3
        bra.s   se\4
sc\4:   andi.l  #$ffff,\3
        lsl.l   #8,\3
se\4:   move.l  \3,\2
        bra.w   sq\4
        endm
; ---- the original code path (all inputs intact) -------------------------------------------------------------------
ofb:    tst.w   d0
        bmi.w   ofc
        jmp     $ef68.l
ofc:    jmp     $f202.l
; ---- range and tie tests ------------------------------------------------------------------------------------------
tri:    move.l  #$ff0000,d4
        cmp.l   d4,d0
        bhi.s   ofb
        cmp.l   d4,d1
        bhi.s   ofb
        cmp.l   d4,d2
        bhi.s   ofb
        cmp.w   #199,d0
        bhi.s   ofb
        cmp.w   #199,d1
        bhi.s   ofb
        cmp.w   #199,d2
        bhi.s   ofb
; ---- the original's sort ($efbe): d0 = lowest y, d1/d2 in either order -----------------------------------------------
        cmp.w   d0,d1
        bge.s   s1
        exg     d0,d2
        exg     d0,d1
        cmp.w   d0,d1
        bge.s   s9
        exg     d0,d2
        exg     d0,d1
        bra.s   s9
s1:     cmp.w   d0,d2
        bge.s   s9
        exg     d1,d2
        exg     d0,d1
; ---- pattern ring phase: j = scanlines before the first wrap ------------------------------------------------------
s9:     move.w  d0,d5
        lsl.w   #4,d5
        add.b   $ffa5.l,d5
        and.w   #$fc,d5
        lsr.w   #1,d5
        lea     jtab(pc),a2
        move.w  d0,-(a7)                ; y0
        move.w  (a2,d5.w),-(a7)         ; j (or $7fff = never)
        cmp.w   d0,d1
        beq.w   flat1                   ; two vertices on the top row
        cmp.w   d0,d2
        beq.w   flat2
; ---- edges ----------------------------------------------------------------------------------------------------
        sub.w   d0,d1
        sub.w   d0,d2
        clr.w   d0                      ; d0 = [x0 | 0]
        sub.l   d0,d1                   ; [dx1 | dy1]
        sub.l   d0,d2                   ; [dx2 | dy2]
        lea     SLOPE.l,a1
        SLOPE_  d1,d6,d7,1              ; s1
        SLOPE_  d2,d5,d7,2              ; s2
        cmp.l   d6,d5
        beq.w   nil
        bgt.s   oa
; orientation B: s2 < s1: left edge = edge 2
        movea.l d5,a3
        movea.l d6,a4
        move.w  d1,d4
        sub.w   d2,d4                   ; dy1 - dy2
        bmi.s   ob2
        lea     TL(pc),a0               ; edge 2 is the near (short) edge and on the left
        move.l  d1,d5
        sub.l   d2,d5                   ; [dx1 - dx2 | dy1 - dy2]
        move.w  d2,d7                   ; lo = dy2
        bra.s   o3
ob2:    lea     TR(pc),a0
        move.l  d2,d5
        sub.l   d1,d5
        move.w  d1,d7
        bra.s   o3
; orientation A: s2 > s1: byte 0 = $1c, left edge = edge 1
oa:     moveq   #$1c,d3
        movea.l d6,a3
        movea.l d5,a4
        move.w  d1,d4
        sub.w   d2,d4
        bmi.s   oa2
        lea     TR(pc),a0
        move.l  d1,d5
        sub.l   d2,d5
        move.w  d2,d7
        bra.s   o3
oa2:    lea     TL(pc),a0
        move.l  d2,d5
        sub.l   d1,d5
        move.w  d1,d7
; ---- plan: d5 = [dx3 | c3], d7 = lo, a0 = side templates -------------------------------------------------------------
o3:     movea.l d0,a2                   ; right edge starts at x0 as well
        move.w  (a7)+,d4                ; j
        cmp.w   #2,d5
        blo.w   c1                      ; c3 == 1: no third run
        SLOPE_  d5,d6,d1,3              ; s3
        move.w  d7,d2
        add.w   d5,d2                   ; H = lo + c3
        cmp.w   d2,d4
        blo.s   wi
; no wrap inside: chunk 1 = lo + 1 scanlines, then c3 - 1
        move.l  d6,4(a0)
        subq.w  #2,d5
        move.w  d5,8(a0)
        bra.w   go
; a wrap inside, c3 >= 2
wi:     move.w  d4,d1
        add.w   #16,d1
        cmp.w   d2,d1
        blo.w   tallb                   ; a second wrap inside: generic chunk list
        move.w  d7,d1
        addq.w  #1,d1                   ; N1 = lo + 1
        cmp.w   d1,d4
        blo.s   b1
        beq.s   b2
; j > N1: S first, then W   (TB3 at +48): ctrb = j - N1 - 1, ctrc = H - j - 1
        lea     48(a0),a0
        move.l  d6,4(a0)
        move.w  d4,d2
        sub.w   d1,d2
        subq.w  #1,d2
        move.w  d2,8(a0)
        move.w  d7,d2
        add.w   d5,d2
        sub.w   d4,d2
        subq.w  #1,d2
        move.w  d2,14(a0)
        bra.s   go
; j == N1: S and W together after N1 scanlines  (TB2 at +34)
b2:     lea     34(a0),a0
        move.l  d6,4(a0)
        subq.w  #2,d5
        move.w  d5,8(a0)
        bra.s   go
; j < N1: W first, then S  (TB1 at +14)
b1:     lea     14(a0),a0
        move.l  d6,10(a0)
        subq.w  #2,d5
        move.w  d5,14(a0)               ; ctrc = c3 - 2
        move.w  d7,d5
        sub.w   d4,d5                   ; lo - j = N1 - j - 1
        move.w  d5,4(a0)
        move.w  d4,d7
        subq.w  #1,d7                   ; first chunk: j scanlines
        bra.s   go
; c3 == 0 (flat bottom) or 1: no third run, H = lo + c3
c1:     move.w  d7,d2
        add.w   d5,d2                   ; H
        cmp.w   d2,d4
        blo.s   w1
        lea     tend(pc),a0
        move.w  d2,d7
        subq.w  #1,d7
        bra.s   go
w1:     move.w  d4,d1
        add.w   #16,d1
        cmp.w   d2,d1
        blo.w   tallb
        lea     tw(pc),a0               ; j < H: W then the rest
        move.w  d2,d1
        sub.w   d4,d1
        subq.w  #1,d1
        move.w  d1,4(a0)                ; H - j - 1
        move.w  d4,d7
        subq.w  #1,d7
; ---- row, pattern pointer, start ---------------------------------------------------------------------------------
go:     move.w  (a7)+,d1                ; y0
        lsl.w   #4,d1
        move.l  d0,d4
        move.l  a2,d5
        moveq   #0,d2
        move.b  d3,d2
        lsl.w   #8,d2
        add.l   $ffa2.l,d2
        add.b   d1,d2
        lsr.l   #1,d2
        movea.l d2,a5
        movea.l $e3e2.l,a1
        add.w   d1,d1
        adda.w  d1,a1
        add.w   d1,d1
        add.w   d1,d1
        adda.w  d1,a1
        moveq   #$1e,d6
        bra.s   rend
; ---- one scanline: step both edges, then render -------------------------------------------------------------------
iter:   add.l   a3,d4
        add.l   a4,d5
rend:   move.l  d4,d0
        swap    d0
        add.w   d0,d0                   ; 2 * xl
        move.l  d5,d1
        swap    d1
        add.w   d1,d1                   ; 2 * xr
        move.w  (a6,d1.w),d2            ; byte offset of the right group
        move.w  (a6,d0.w),d3            ; and of the left group
        lea     (a1,d3.w),a2
        sub.w   d3,d2
        bmi.s   done                    ; right group left of the left group: the original ends the fill here
        bne.s   multi
; -- both ends in one group
        and.w   d6,d0
        add.w   d0,d0
        move.l  -$80(a6,d0.w),d3
        and.w   d6,d1
        add.w   d1,d1
        and.l   -$40(a6,d1.w),d3
        move.l  (a5)+,d0
        move.l  (a2),d1
        eor.l   d1,d0
        and.l   d3,d0
        eor.l   d0,d1
        move.l  d1,(a2)+
        move.l  (a5)+,d0
        move.l  (a2),d1
        eor.l   d1,d0
        and.l   d3,d0
        eor.l   d0,d1
        move.l  d1,(a2)
        lea     $a0(a1),a1
        dbra    d7,iter
        movea.l (a0)+,a2
        jmp     (a2)
done:   rts
nil:    addq.l  #4,a7
        rts
; -- two adjacent groups
multi:  subq.w  #8,d2
        bne.w   gen
        and.w   d6,d0
        add.w   d0,d0
        move.l  -$80(a6,d0.w),d3
        move.l  (a5),d0
        move.l  (a2),d2
        eor.l   d2,d0
        and.l   d3,d0
        eor.l   d0,d2
        move.l  d2,(a2)+
        move.l  4(a5),d0
        move.l  (a2),d2
        eor.l   d2,d0
        and.l   d3,d0
        eor.l   d0,d2
        move.l  d2,(a2)+
        and.w   d6,d1
        add.w   d1,d1
        move.l  -$40(a6,d1.w),d3
        move.l  (a5)+,d0
        move.l  (a2),d2
        eor.l   d2,d0
        and.l   d3,d0
        eor.l   d0,d2
        move.l  d2,(a2)+
        move.l  (a5)+,d0
        move.l  (a2),d2
        eor.l   d2,d0
        and.l   d3,d0
        eor.l   d0,d2
        move.l  d2,(a2)
        lea     $a0(a1),a1
        dbra    d7,iter
        movea.l (a0)+,a2
        jmp     (a2)
; -- three or more groups (d2 = 8 * full groups)
gen:    and.w   d6,d0
        add.w   d0,d0
        move.l  -$80(a6,d0.w),d3
        move.l  (a5),d0
        move.l  (a2),d1
        eor.l   d1,d0
        and.l   d3,d0
        eor.l   d0,d1
        move.l  d1,(a2)+
        move.l  4(a5),d0
        move.l  (a2),d1
        eor.l   d1,d0
        and.l   d3,d0
        eor.l   d0,d1
        move.l  d1,(a2)+
        movem.l (a5),d0-d1
        lsr.w   #1,d2
        neg.w   d2
        jmp     cend(pc,d2.w)
        rept    18
        move.l  d0,(a2)+
        move.l  d1,(a2)+
        endr
cend:   move.l  d5,d1
        swap    d1
        add.w   d1,d1
        and.w   d6,d1
        add.w   d1,d1
        move.l  -$40(a6,d1.w),d3
        move.l  (a5)+,d0
        move.l  (a2),d1
        eor.l   d1,d0
        and.l   d3,d0
        eor.l   d0,d1
        move.l  d1,(a2)+
        move.l  (a5)+,d0
        move.l  (a2),d1
        eor.l   d1,d0
        and.l   d3,d0
        eor.l   d0,d1
        move.l  d1,(a2)
        lea     $a0(a1),a1
        dbra    d7,iter
        movea.l (a0)+,a2
        jmp     (a2)
; ---- flat top: two vertices on the top row (the original's $f13e path); d0/d1 = the pair, d2 = the third vertex ---------------------------
flat2:  exg     d1,d2
        exg     d0,d1
flat1:  cmp.w   d0,d2
        beq.w   nil                     ; all three on one row: nothing
        sub.w   d0,d2
        move.w  d2,d7                   ; dy
        swap    d0
        swap    d1
        swap    d2                      ; low words = x0, x1, x2
        cmp.w   d0,d1
        bge.s   f1a
        exg     d0,d1
        moveq   #$1c,d3
f1a:    lea     SLOPE.l,a1
        move.w  d2,d4
        sub.w   d0,d4
        swap    d4
        move.w  d7,d4                   ; [x2 - xl | dy]
        SLOPE_  d4,d6,d5,4
        movea.l d6,a3
        move.w  d2,d4
        sub.w   d1,d4
        swap    d4
        move.w  d7,d4                   ; [x2 - xr | dy]
        SLOPE_  d4,d6,d5,5
        movea.l d6,a4
        swap    d0
        clr.w   d0                      ; [xl | 0]
        swap    d1
        clr.w   d1
        movea.l d1,a2                   ; [xr | 0]
        move.w  (a7)+,d4                ; j
        moveq   #0,d5                   ; c3 = 0: H = dy
        lea     TL(pc),a0
        bra.w   c1
; ---- generic chunk list (a second pattern wrap inside the triangle): d4 = j, d7 = lo, d5.w = c3, d6 = s3 (c3 >= 2), d2 = H, a0 = side templates
tallb:  movem.l d0/d3,-(a7)
        move.l  34(a0),-(a7)            ; hSW
        move.l  (a0),-(a7)              ; hS
        lea     list2(pc),a1
        move.w  #$7fff,d1               ; next S
        cmp.w   #2,d5
        blo.s   tb0
        move.w  d7,d1
        addq.w  #1,d1                   ; N1
tb0:    moveq   #0,d5                   ; pos
        bsr.s   tbmin
        move.w  d3,d7
        subq.w  #1,d7                   ; first chunk
        move.w  d3,d5
tbl:    cmp.w   d2,d5
        beq.s   tbe
        cmp.w   d1,d5
        bne.s   tbw
        cmp.w   d4,d5
        bne.s   tbs
        move.l  4(a7),(a1)+             ; S and W together
        move.l  d6,(a1)+
        move.w  #$7fff,d1
        add.w   #16,d4
        bra.s   tbn
tbs:    move.l  (a7),(a1)+
        move.l  d6,(a1)+
        move.w  #$7fff,d1
        bra.s   tbn
tbw:    move.l  #hw,(a1)+
        add.w   #16,d4
tbn:    bsr.s   tbmin
        move.w  d3,d0
        sub.w   d5,d0
        subq.w  #1,d0
        move.w  d0,(a1)+
        move.w  d3,d5
        bra.s   tbl
tbe:    move.l  #hend,(a1)+
        lea     list2(pc),a0
        addq.l  #8,a7
        movem.l (a7)+,d0/d3
        bra.w   go
tbmin:  move.w  d1,d3                   ; d3 = min(d1, d4, d2)
        cmp.w   d4,d3
        bls.s   tbm1
        move.w  d4,d3
tbm1:   cmp.w   d2,d3
        bls.s   tbm2
        move.w  d2,d3
tbm2:   rts
; ---- table divides that miss the table: the original branches ---------------------------------------------------------
        SLOW_   d1,d6,d7,1
        SLOW_   d2,d5,d7,2
        SLOW_   d5,d6,d1,3
        SLOW_   d4,d6,d5,4
        SLOW_   d4,d6,d5,5
; ---- chunk handlers (a0 = list: handler, payload ...) ---------------------------------------------------------------
hsl:    movea.l (a0)+,a3
        move.w  (a0)+,d7
        bra.w   iter
hsr:    movea.l (a0)+,a4
        move.w  (a0)+,d7
        bra.w   iter
hw:     lea     -128(a5),a5
        move.w  (a0)+,d7
        bra.w   iter
hswl:   lea     -128(a5),a5
        movea.l (a0)+,a3
        move.w  (a0)+,d7
        bra.w   iter
hswr:   lea     -128(a5),a5
        movea.l (a0)+,a4
        move.w  (a0)+,d7
        bra.w   iter
hend:   rts
; ---- static chunk lists: per side TA(+0) TB1(+14) TB2(+34) TB3(+48), then tend / tw --------------------------------------------
TL:     dc.l    hsl,0
        dc.w    0
        dc.l    hend
        dc.l    hw
        dc.w    0
        dc.l    hsl,0
        dc.w    0
        dc.l    hend
        dc.l    hswl,0
        dc.w    0
        dc.l    hend
        dc.l    hsl,0
        dc.w    0
        dc.l    hw
        dc.w    0
        dc.l    hend
TR:     dc.l    hsr,0
        dc.w    0
        dc.l    hend
        dc.l    hw
        dc.w    0
        dc.l    hsr,0
        dc.w    0
        dc.l    hend
        dc.l    hswr,0
        dc.w    0
        dc.l    hend
        dc.l    hsr,0
        dc.w    0
        dc.l    hw
        dc.w    0
        dc.l    hend
tend:   dc.l    hend
tw:     dc.l    hw
        dc.w    0
        dc.l    hend
        even
jtab:
l0      set     0
        rept    64
        if      (l0&7)<4
        dc.w    16-(l0>>3)
        else
        dc.w    $7fff
        endif
l0      set     l0+2
        endr
list2:  ds.b    160
