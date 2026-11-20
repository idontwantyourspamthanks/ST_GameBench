; name: rd_geom
; default: no
; site: $10216
; orig: 48472238131c
; note: Run-time tables (NOT declared with `; data:`, which would stretch the payload image past IMG_MAX_LEN): $D0000-$DAFFF of the free RAM run $B2700-$E83FF (rendering.md section 3), initialised lazily behind the magic long RDG1 at $D0000.
; doc: Faster road geometry $100b4 (pixel-identical prototype): the slice loop (112 x 2 mulu.w, 32 unused slices, memory accumulators) becomes three tight passes and a product table.
; note: Moonshine Racers road study (work/notes/road.md).  Site $10216 = top of the per-slice loop of $100b4 (`swap d7 / move.l $131c.w,d1`, after the stripe/curve setup $101ba-$10214) -> `jmp $B4000.l`;
; note: the blob does the WHOLE rest of the routine (incl. `move.l a6,$4b84.w` and the rts) with the same memory results: $4804.. centre table, $1320, $4b84 and the record stream below $4f78.
; note: Pass A (112 slices): centre table C[k] = (k+1)*S>>16 + $a0 - hw[k] + X1[k] (S = $131c, X1 = $4724.., hw from a static table derived once from $4644).
; note: Pass B (80 slices): A = C + wR, B = C - wL, wL/wR = (profile byte * ($1316+k)) >> 4 read from a product table (mulu.w replaced; table of 80 rows x 256 words, rebuilt when $1316 changes).
; note: Pass C (80 slices): the stripe state machine and the record emission exactly as the stock loop.  The 32 near slices (counter < 32) never emit, so their lookups and products are skipped.
; note: Guards: $1316 + 79 <= 257 (product < 65536), else the stock loop runs.  Static tables ($4564/$4644 are generated from constants at level start) are derived on the first call (magic RDG1).
MAGIC   equ     $D0000
PM      equ     $D0004          ; cached $1316 + 1 (0 = product table not built)
CBASE   equ     $D0010          ; 112 words: $a0 - hw(W0[min(k,80)])
SCR     equ     $D0100          ; 80 x (A,B) words
PT      equ     $D1000          ; 80 rows x 256 words
        org     $10216
        jmp     $B4000.l

        org     $B4000
rd_loop3:
        move.w  $1316.w,d0
        cmp.w   #178,d0                 ; m0 + 79 <= 257, unsigned (also rejects negative)
        bhi.w   .stock
        cmp.l   #'RDG1',MAGIC.l
        beq.s   .st_ok
        movem.l d0-d7/a0-a6,-(a7)
        bsr.w   gen_static
        movem.l (a7)+,d0-d7/a0-a6
        move.w  $1316.w,d0
.st_ok: addq.w  #1,d0
        cmp.w   PM.l,d0
        beq.s   .pt_ok
        movem.l d0-d7/a0-a6,-(a7)
        subq.w  #1,d0
        bsr.w   gen_pt
        movem.l (a7)+,d0-d7/a0-a6
.pt_ok:
        ; ---- pass A: centre table, 112 slices.  keeps a0, a4, a6, d5, d6
        move.l  $131c.w,d4
        moveq   #0,d3                   ; accumulator ($1320)
        lea     $4724.w,a2
        lea     $4804.w,a5
        lea     CBASE.l,a1
        moveq   #111,d7
.a:     add.l   d4,d3
        move.l  d3,d0
        swap    d0
        add.w   (a1)+,d0
        add.w   (a2)+,d0
        move.w  d0,(a5)+
        dbra    d7,.a
        move.l  d3,$1320.w
        ; ---- pass B: left/right edge positions, 80 slices
        lea     $4644.w,a1              ; T1 descending
        lea     $4804.w,a2
        lea     SCR.l,a3
        lea     $13b0.w,a5
        lea     PT.l,a6
        move.w  $13ae.w,d4
        move.w  #$3ff,d0
        moveq   #79,d7
.b:     move.w  -(a1),d1
        add.w   d4,d1
        and.w   d0,d1
        moveq   #0,d2
        move.b  (a5,d1.w),d2
        add.w   d2,d2
        move.w  (a6,d2.w),d2            ; wL
        addi.w  #$400,d1
        moveq   #0,d3
        move.b  (a5,d1.w),d3
        add.w   d3,d3
        move.w  (a6,d3.w),d3            ; wR
        move.w  (a2)+,d1                ; C
        add.w   d1,d3                   ; A = C + wR
        sub.w   d2,d1                   ; B = C - wL
        move.w  d3,(a3)+
        move.w  d1,(a3)+
        lea     512(a6),a6
        dbra    d7,.b
        ; ---- pass C: stripes + records (stock logic)
        lea     $4644.w,a3
        lea     $4f78.w,a6
        lea     SCR.l,a5
        moveq   #0,d3                   ; run counter (stock d7.w)
        moveq   #79,d7
.c:     move.w  (a3)+,d0
        move.w  (a5)+,d1
        move.w  (a5)+,d2
        dbra    d3,.pop
        clr.w   d3
.m1:    move.b  d5,d3
        move.b  (a4),d5
        sub.b   d5,d3
        bne.s   .m2
        addi.w  #$2000,d6
        lea     -$10(a4),a4
        bra.s   .m1
.m2:    neg.b   d3
        subq.w  #1,d3
.pop:   move.w  -(a0),d4
        subq.w  #1,d4
        bmi.s   .nx
.em:    movem.w d0-d2/d6,-(a6)
        dbra    d4,.em
.nx:    addq.b  #2,d6
        dbra    d7,.c
        move.l  a6,$4b84.w
        rts
.stock: swap    d7
        move.l  $131c.w,d1
        jmp     $1021c.l

; gen_static: CBASE[k] = $a0 - hw(W0[min(k,80)]), hw(w) = ((w >> 8) + 1) >> 1
gen_static:
        lea     $4644.w,a0
        lea     CBASE.l,a1
        moveq   #79,d7
.l1:    move.w  (a0)+,d0
        bsr.s   .hw
        move.w  d1,(a1)+
        dbra    d7,.l1
        move.w  (a0),d0
        bsr.s   .hw
        moveq   #31,d7
.l2:    move.w  d1,(a1)+
        dbra    d7,.l2
        move.l  #'RDG1',MAGIC.l
        clr.w   PM.l
        rts
.hw:    lsr.w   #8,d0
        addq.w  #1,d0
        lsr.w   #1,d0
        move.w  #$a0,d1
        sub.w   d0,d1
        rts

; gen_pt: d0 = m0.  PT[r][b] = (b * (m0 + r)) >> 4 (low word), r = 0..79, b = 0..255
gen_pt:
        lea     PT.l,a0
        move.w  d0,d1
        addq.w  #1,d0
        move.w  d0,PM.l
        moveq   #79,d7
.row:   moveq   #0,d2
        move.w  #255,d6
.ent:   move.w  d2,d3
        lsr.w   #4,d3
        move.w  d3,(a0)+
        add.w   d1,d2
        dbra    d6,.ent
        addq.w  #1,d1
        dbra    d7,.row
        rts
