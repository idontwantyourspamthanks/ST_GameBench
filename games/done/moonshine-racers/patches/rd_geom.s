; name: rd_geom
; default: yes
; site: $100b4
; orig: 41f8456443f81bbc
; conflicts: sb_bar
; ram: $C0000-$CAFFF  rd_geom tables (magic, cached $1316, standing-frame result, product table); zero at game start, built lazily behind the magic
; doc: Faster road geometry $100b4 (pixel-identical): per-slice loop split into tight passes, the two mulu.w per slice become one table lookup each, unused near slices are skipped.
; note: Moonshine Racers road study (work/notes/road.md).  Site $100b4 (the first two `lea`s of the road geometry routine) -> `jmp $B4004.l` ($B4000 = the pre-warm entry used by rd_init); the blob is the WHOLE routine (same memory results, same rts).
; note: Loop 1 (curve offsets $4724.., 112 slices) is unrolled 4x with a doubled static copy of $4564.  Loop 2 (hill list $49c4/$4aa4) indexes the $68000 map with a base pointer that advances 256 per slice.
; note: Loop 3 becomes three passes.  A (112 slices): centre table C[k] = ((k+1)*S >> 16) + $a0 - hw[k] + X1[k] with S = $131c, X1 = $4724.. and hw from a static table.
; note: B (80 slices): A = C + wR, B = C - wL, wL/wR = (profile byte * ($1316 + k)) >> 4 from a product table (replaces mulu.w; 80 rows x 256 words rebuilt when $1316 changes).
; note: C (80 slices): the stripe state machine and the record emission exactly as the stock loop.  The 32 nearest slices (counter < 32) never emit a record in the stock loop, so their lookups are skipped.
; note: Guard: $1316 + 79 <= 257 (product < 65536), else the stock code runs from $100bc.  The static tables ($4564, $4644: generated from constants at level start) are derived on the first call (magic RDG1).
; note: Standing frames ($130c = 0): the three track-table writers ($fe50, $ff76, $1003c: `move.w $130c.w,d0 / subq.w #1,d0 / bmi` at their entry) do nothing, so when the generator state (33 words: position, curve, hill and ring pointers) equals the
; note: state of the previous call, the whole output region ($4724-$4f77, $23c4, $131c, $1320) is copied back from a saved copy instead of being recomputed.
; note: Run-time tables are declared with `; ram:` (not `; data:`, which would stretch the payload image past IMG_MAX_LEN): $C0000-$CAFFF of the free RAM run $B2700-$E2BFF (rendering.md section 3; the top is $E2BFF, not $E83FF: live GEM/AES data of TOS 2.06 on a 1 MB Mega STE starts at $E2C50, integration.md section 10.3).
MAGIC   equ     $C0000          ; 'RDG1' once the static tables are built
PM      equ     $C0004          ; cached $1316 + 1 (0 = product table not built)
SIGOK   equ     $C0008          ; byte: SIGBUF/SAVE hold a valid standing-frame result
SAVEPEND equ    $C0009          ; byte: this call must save its result
SIGBUF  equ     $C0340          ; 33 words: generator state of the saved result
SIGNEW  equ     $C0390          ; 33 words: generator state at entry of the call being saved
SAVE    equ     $C0400          ; $4724-$4f77 (2132 B), $23c4 (word), $131c, $1320
CBASE   equ     $C0010          ; 112 words: $a0 - hw(W0[min(k,80)])
T2      equ     $C0100          ; 112 words: 2 * T1[j]
SCR     equ     $C0200          ; 80 x (A,B) words
PT      equ     $C1000          ; 80 rows x 256 words
        org     $100b4
        jmp     $B4004.l

        org     $B4000
; $B4000 = pre-warm entry (called once per race by rd_init): builds the static tables and the product table now instead of in the first road frame
        bra.w   rdg_init
rd_geom:
        move.w  $130c.w,d0
        bne.s   .moving
        tst.b   SIGOK.l
        beq.s   .cap
        lea     sigtab(pc),a0
        lea     SIGBUF.l,a1
        moveq   #32,d7
.s:     movea.w (a0)+,a2
        move.w  (a2),d1
        cmp.w   (a1)+,d1
        bne.s   .cap
        dbra    d7,.s
        ; same generator state as the saved standing result: copy it back
        lea     SAVE.l,a0
        lea     $4724.w,a1
.r:     movem.l (a0)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,(a1)
        lea     52(a1),a1
        cmpa.w  #$4f78,a1
        bne.s   .r
        move.w  (a0)+,$23c4.w
        move.l  (a0)+,$131c.w
        move.l  (a0)+,$1320.w
        rts
.cap:   lea     sigtab(pc),a0
        lea     SIGNEW.l,a1
        moveq   #32,d7
.cp:    movea.w (a0)+,a2
        move.w  (a2),(a1)+
        dbra    d7,.cp
        move.b  #1,SAVEPEND.l
        bra.s   .full
.moving: clr.b  SAVEPEND.l
.full:  move.w  $1316.w,d0
        cmp.w   #178,d0                 ; m0 + 79 <= 257, unsigned (also rejects negative)
        bhi.w   .stock
        cmp.l   #'RDG1',MAGIC.l
        beq.s   .st_ok
        bsr.w   gen_static
        move.w  $1316.w,d0
.st_ok: addq.w  #1,d0
        cmp.w   PM.l,d0
        beq.s   .pt_ok
        subq.w  #1,d0
        bsr.w   gen_pt
.pt_ok:
        ; ---- loop 1: X1[i] = (sum_{j<=i} (sin[(2*T1[j] + d3) & $7fe] - sin[d3])) >> 8, stored downward from $4804
        lea     T2.l,a0
        lea     $1bbc.w,a1
        lea     $4804.w,a2
        move.w  $1bba.w,d3
        move.w  (a1,d3.w),d4
        move.w  #$7fe,d6
        moveq   #0,d0
        moveq   #27,d7
.l1:    rept    4
        move.w  (a0)+,d1
        add.w   d3,d1
        and.w   d6,d1
        move.w  (a1,d1.w),d2
        sub.w   d4,d2
        ext.l   d2
        add.l   d2,d0
        move.l  d0,d1
        asr.l   #8,d1
        move.w  d1,-(a2)
        endr
        dbra    d7,.l1
        ; ---- loop 2: hill list ($49c4: 232 - height, $4aa4 lists)
        lea     $68000.l,a0
        lea     $4564.w,a1
        lea     $49c4.w,a3
        move.w  #$e8,d2
        lea     $4aa4.w,a4
        lea     $23c8.w,a5
        lea     $4aa4.w,a6
        move.w  $40(a1),d0
        move.w  $23c6.w,d5
        move.w  d5,d3
        add.w   d0,d5
        andi.w  #$3ff,d5
        move.b  (a5,d5.w),d4
        ext.w   d4
        move.w  d4,$23c4.w
        move.w  d3,d5
        add.w   (a1)+,d5
        andi.w  #$3ff,d5
        move.b  (a5,d5.w),d5
        sub.b   d4,d5
        ext.w   d5
        addi.w  #$80,d5
        moveq   #0,d6
        move.b  (a0,d5.w),d6
        move.w  d2,-(a3)
        move.w  #$ffff,-(a6)
        move.w  d2,d0                   ; d0 = $e8 for the loop
        move.w  d6,d1
        lea     $68080.l,a0             ; map base + 128, advances 256 per slice
        moveq   #$6e,d7
.l2:    move.w  d3,d5
        add.w   (a1)+,d5
        andi.w  #$3ff,d5
        move.b  (a5,d5.w),d5
        sub.b   d4,d5
        ext.w   d5
        moveq   #0,d6
        move.b  (a0,d5.w),d6
        move.w  d0,d2
        sub.w   d6,d2
        move.w  d2,-(a3)
        sub.w   d6,d1
        bcc.s   .hid
        move.w  d1,-(a6)
        exg     d1,d6
        neg.w   d6
        move.w  d6,(a4)+
        cmpi.w  #$8e,d1
        bcs.s   .nx
        subi.w  #$8e,d1
        sub.w   d1,-2(a4)
        moveq   #-1,d6
        subq.w  #1,d7
        bmi.s   .end
.f:     move.w  d6,(a4)+
        move.w  #$64,-(a6)
        dbra    d7,.f
        bra.s   .end
.hid:   move.w  d1,-(a6)
        add.w   d6,d1
        clr.w   (a4)+
.nx:    lea     256(a0),a0
        dbra    d7,.l2
.end:   move.w  #$ffff,(a4)+
        ; ---- stripe / curve setup (stock $101ba-$10214)
        movea.l a4,a0
        lea     $4724.w,a2
        lea     $4644.w,a3
        lea     $4563.w,a4
        move.b  (a4),d5
        move.w  $130a.w,d6
        move.w  $130c.w,d0
        add.w   $1308.w,d0
        cmpi.w  #$10,d0
        bcs.s   .p1
.p0:    subi.w  #$10,d0
        subi.w  #$2000,d6
        move.w  d6,$130a.w
        cmpi.w  #$10,d0
        bcc.s   .p0
.p1:    move.w  d0,$1308.w
        andi.w  #$e000,d6
        suba.w  d0,a4
        moveq   #0,d0
        move.w  $1318.w,d0
        swap    d0
        asr.l   #5,d0
        move.l  d0,$131c.w
        move.l  d0,d4                   ; S
        ; ---- pass A: centre table, 112 slices (unrolled 4x)
        moveq   #0,d3                   ; accumulator ($1320 at the end)
        lea     $4804.w,a5
        lea     CBASE.l,a1
        moveq   #27,d7
.a:     rept    4
        add.l   d4,d3
        move.l  d3,d0
        swap    d0
        add.w   (a1)+,d0
        add.w   (a2)+,d0
        move.w  d0,(a5)+
        endr
        dbra    d7,.a
        move.l  d3,$1320.w
        ; ---- pass B: left/right edge positions, 80 slices (unrolled 4x, a4 = $13b0+$400)
        move.l  a4,-(a7)
        lea     $4644.w,a1              ; T1 descending
        lea     $4804.w,a2
        lea     SCR.l,a3
        lea     $13b0.w,a5
        lea     $17b0.w,a4              ; $13b0 + $400 (eliminates addi.w #$400,d1)
        lea     PT.l,a6
        move.w  $13ae.w,d4
        move.w  #$3ff,d0
        moveq   #19,d7
.b:     rept    4
        move.w  -(a1),d1
        add.w   d4,d1
        and.w   d0,d1
        moveq   #0,d2
        move.b  (a5,d1.w),d2
        add.w   d2,d2
        move.w  (a6,d2.w),d2            ; wL
        moveq   #0,d3
        move.b  (a4,d1.w),d3
        add.w   d3,d3
        move.w  (a6,d3.w),d3            ; wR
        move.w  (a2)+,d1                ; C
        add.w   d1,d3                   ; A = C + wR
        sub.w   d2,d1                   ; B = C - wL
        move.w  d3,(a3)+
        move.w  d1,(a3)+
        lea     512(a6),a6
        endr
        dbra    d7,.b
        movea.l (a7)+,a4
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
        bmi.s   .nx2
.em:    movem.w d0-d2/d6,-(a6)
        dbra    d4,.em
.nx2:   addq.b  #2,d6
        dbra    d7,.c
        move.l  a6,$4b84.w
        tst.b   SAVEPEND.l
        beq.s   .done
        clr.b   SAVEPEND.l
        lea     $4724.w,a0
        lea     SAVE.l,a1
.sv:    movem.l (a0)+,d0-d7/a2-a6
        movem.l d0-d7/a2-a6,(a1)
        lea     52(a1),a1
        cmpa.w  #$4f78,a0
        bne.s   .sv
        move.w  $23c4.w,(a1)+
        move.l  $131c.w,(a1)+
        move.l  $1320.w,(a1)+
        lea     SIGNEW.l,a0
        lea     SIGBUF.l,a1
        moveq   #32,d7
.sg:    move.w  (a0)+,(a1)+
        dbra    d7,.sg
        st      SIGOK.l
.done:  rts
.stock: lea     $4564.w,a0
        lea     $1bbc.w,a1
        jmp     $100bc.l

; the 33 words that determine the geometry output while the car stands: position/curve/hill state and the ring generators' state (the table writers are idle at speed 0)
sigtab: dc.w    $1308,$130a,$130c,$1316,$1318,$13ae,$1bba,$1bb8,$23c6,$102c
        dc.w    $13a2,$13a4,$13a6,$13a8,$13aa,$13ac,$23bc,$23be,$27c8
        dc.w    $1bb0,$1bb2,$1bb4,$1bb6,$23c0,$23c2,$27da,$27dc,$27ca,$27cc,$27ce,$27d0,$27d2,$27d4

; rdg_init: the pre-warm entry ($B4000, from rd_init): the same generators the first road frame would run, now, once per race
rdg_init:
        movem.l d0-d7/a0-a6,-(a7)
        move.w  $1316.w,d0
        cmp.w   #178,d0
        bhi.s   .x
        cmp.l   #'RDG1',MAGIC.l
        beq.s   .st
        bsr.w   gen_static
        move.w  $1316.w,d0
.st:    addq.w  #1,d0
        cmp.w   PM.l,d0
        beq.s   .x
        subq.w  #1,d0
        bsr.w   gen_pt
.x:     movem.l (a7)+,d0-d7/a0-a6
        rts

; gen_static: CBASE[k] = $a0 - hw(W0[min(k,80)]), hw(w) = ((w >> 8) + 1) >> 1;  T2[j] = 2 * T1[j]
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
        lea     $4564.w,a0
        lea     T2.l,a1
        moveq   #111,d7
.l3:    move.w  (a0)+,d0
        add.w   d0,d0
        move.w  d0,(a1)+
        dbra    d7,.l3
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
