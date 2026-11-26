; name: p7_ck_fill
; default: no
; site: $38c6e
; orig: 48e7fffe41f90007b6b0
; note: P7 item 2 (work/notes/p7_cockpit_cull.md).  Span fill entry $38c6e (every polygon fill: terrain
;       $1face/$1fb44, objects $3bbc0).  Active inside a terrain pass only (EN, p7_ck_enter).  After
;       the edge walker has written the left/right edge tables ($7b6b0/$7b9d0, one {group offset.w,
;       mask.w} long per row) and the row range $180ee..$180ec, drops the bottom rows of the polygon
;       whose whole span lies under opaque cockpit pixels:
;         - row 200 (below the screen: the original fills it into the bytes after the buffer, which
;           nothing reads),
;         - rows from the bottom up while the row's span [L, R) lies inside one opaque run of the
;           cockpit (KEYS table of p7_ck_tab: absolute {offset, mask} keys of the run start and
;           end+1; for the same row the long {offset, mask} is strictly monotonic in x, so two long
;           compares decide it; a row with R <= L draws nothing and also counts as under),
;       and skips the fill call completely when no row is left.  Only whole rows are removed, a span
;       is never split or narrowed, so the 16-px group masks of the remaining rows are untouched.
;       Head rows (ymin upward) and rows in between are not trimmed: measured, their tests cost more
;       than they save.  Rows above KR0 have no table entry and stop the trimming.
EN      equ     $b5000
KEYS    equ     $b50e0
KR0     equ     176

        org     $38c6e
        jmp     $b56d2.l
        dcb.w   2,$4e71

        org     $b56d2
FILL:   movem.l d0-d7/a0-a6,-(a7)       ; displaced
        tst.w   EN.l
        beq.s   .go
        move.w  $180ec.l,d7             ; ymax
        cmp.w   #KR0,d7
        blt.s   .go
        cmp.w   #200,d7
        bgt.s   .go
        bne.s   .n
        subq.w  #1,d7                   ; row 200
.n:     move.w  $180ee.l,d5             ; ymin: lowest row to trim
        cmp.w   #KR0,d5
        bge.s   .l1
        move.w  #KR0,d5
.l1:    move.w  d7,d0
        addq.w  #1,d0
        lsl.w   #2,d0                   ; 4 * (y + 1)
        lea     $7b6b0.l,a3             ; one past the entry of row y: -(An) walks upwards
        adda.w  d0,a3
        lea     $7b9d0.l,a4
        adda.w  d0,a4
        lsl.w   #2,d0                   ; 16 * (y + 1)
        lea     KEYS-KR0*16.l,a5
        adda.w  d0,a5
.t:     move.l  -(a3),d0                ; L
        move.l  -(a4),d1                ; R
        lea     -16(a5),a5
        cmp.l   (a5),d0
        blt.s   .t1
        cmp.l   4(a5),d1
        ble.s   .tk
.t1:    cmp.l   8(a5),d0
        blt.s   .st
        cmp.l   12(a5),d1
        bgt.s   .st
.tk:    subq.w  #1,d7
        cmp.w   d5,d7
        bge.s   .t
        cmp.w   $180ee.l,d7
        blt.s   .none                   ; every row trimmed
.st:    move.w  d7,$180ec.l
.go:    lea     $7b6b0.l,a0             ; displaced (the 6-byte jmp covers movem.l + the first 2 bytes
        jmp     $38c78.l                ; of this lea): continue at lea $7b9d0.l,a1
.none:  movem.l (a7)+,d0-d7/a0-a6
        rts
