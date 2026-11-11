; name: p7_cell_cull
; default: yes
; site: $1d974
; orig: 117c00ff000a
; phase: deferred
; note: P7 item 4 (work/notes/p7_cell_cull.md), part 2/2.  Terrain classify $1d8d4, mode-1 land path:
;       `bpl.w $1d974` at $1d950 is reached only when the OR of the four corner heights (d0-d3 =
;       (a0), $10(a0), $200(a0), $210(a0)) has bit 15 clear, i.e. all four are >= 0, and $18768 != 0.
;       The original there is `move.b #$ff,$a(a0)` (class $ff) followed by four slot lookups and the
;       append of a0 to the polygen cell list.  This hook decides first whether polygen could emit
;       anything for the cell.  It cannot when all four corner vertices carry outcode bits $101
;       (Y' + W < 0, Y' = 2Y + (Y>>2): below the view window): the AND of the four slot outcodes
;       in $1ecba is then non-zero and it returns without a triangle, and the cell has no marker
;       ($6(a6) >= 0 -> $1ebfe skips the stream marker).  The test is a sound upper bound on 9Y + 4W
;       over the four corners (p7_cell_pre builds the tables, header there): UB = TC[col] + TR[row] +
;       ((KC*hmax)>>8) < 0 with hmax = largest of the four heights.  Cells with $6(a0) != 0 (object
;       hash link, negative when set) are never skipped, because the polygen loop emits their marker
;       even when the cell has no triangle.  Cells whose c/e fields are not a multiple of 8 inside
;       the table window (c+64 in 0..127), or whose hmax exceeds HI (HI = -1: disabled), keep the
;       original path.  Culled: nothing is written to the record and the loop continues at $1da48
;       (next list entry); kept: the displaced move.b and a jump to $1d97a.  d0-d3 and d6 are dead
;       after the hook ($1da66 reloads d0-d2; d3 is dead and d6 only held the OR for the sign test);
;       a2/a3 are scratch in $1da66.
D       equ     $b5c00
KC      equ     $b5c02
HI      equ     $b5c04
TC      equ     $b5c20
TR      equ     $b5ca0

        org     $1d974
        jmp     $b5b00.l

        org     $b5b00
        tst.w   6(a0)
        bne.s   keep
        cmp.w   d0,d1
        ble.s   .a
        move.w  d1,d0
.a:     cmp.w   d0,d2
        ble.s   .b
        move.w  d2,d0
.b:     cmp.w   d0,d3
        ble.s   .c
        move.w  d3,d0                   ; d0 = hmax
.c:     cmp.w   HI(pc),d0
        bgt.s   keep
        move.w  $c(a0),d1
        add.w   #64,d1
        move.w  d1,d2
        and.w   #$ff87,d2
        bne.s   keep
        move.w  $e(a0),d2
        add.w   #64,d2
        move.w  d2,d3
        and.w   #$ff87,d3
        bne.s   keep
        lea     TC(pc),a2
        move.l  (a2,d1.w),d6
        lea     TR(pc),a3
        add.l   (a3,d2.w),d6
        muls.w  KC(pc),d0
        asr.l   #8,d0
        add.l   d0,d6
        bmi.s   cull
keep:   move.b  #$ff,$a(a0)             ; displaced
        jmp     $1d97a.l
cull:   jmp     $1da48.l
