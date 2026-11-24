; trkhook.s -- SCRATCH PROTOTYPE of the stage-2 hooks (MSRLoaderStudy).  Not product code: installed by hook_test.py through the debugger at >= 2 MB.
;   site A  $72c4  `jsr $76f4.l` (4eb9 000076f4)  -> `jsr hookA.l`        wraps the WHOLE race (setup + loop run inside $76f4, return at $7b70)
;   site B  $77da  `lea.l $58c00.l,a0 / jsr $d6fa.l` (41f900058c00 4eb90000d6fa, 12 B) -> `jmp hookB.l` + 3 nops   track-block fetch
; A swaps the campaign position into base-level terms for the duration of the race: $102c := base[pos] (every per-level table of the game then follows the BASE
; level), the position is kept in V_POS, and on return $102c := pos | (flags the race set: $80 time-out retry, $8000 game over).
; B copies the campaign entry's block into $58c00 (<= 6144 B, the stock capacity) instead of loading the stock block; an entry without a block loads the stock one.
; Store layout (scratch format): +0 'MSTK'; +4 count.w; +6 pad; entry i at +8+8*i: base.b flag.b(1 = custom block) off.l (from STORE) len.w
STORE   equ     $110000
V_ACT   equ     $100f00         ; byte: 1 = a campaign is active (set by whoever loaded the store)
V_POS   equ     $100f02         ; word: campaign position
SIGOK   equ     $c0008          ; rd_geom standing-frame reuse flag (patches/rd_geom.s)

        org     $100000
hookA:  tst.b   V_ACT.l
        beq.s   .stk
        move.w  $102c.w,d0
        andi.w  #$f,d0
        move.w  d0,V_POS.l
        lsl.w   #3,d0
        lea     STORE+8.l,a0
        moveq   #0,d1
        move.b  (a0,d0.w),d1
        move.w  d1,$102c.w
.stk:   jsr     $76f4.l
        tst.b   V_ACT.l
        beq.s   .x
        move.w  $102c.w,d0
        andi.w  #$8080,d0
        or.w    V_POS.l,d0
        move.w  d0,$102c.w
.x:     rts

        org     $100100
hookB:  tst.b   V_ACT.l
        beq.s   .stock
        movem.l d0-d3/a0-a2,-(a7)
        move.w  V_POS.l,d0
        lsl.w   #3,d0
        lea     STORE+8.l,a0
        tst.b   1(a0,d0.w)
        beq.s   .fall
        move.l  2(a0,d0.w),d1
        moveq   #0,d2
        move.w  6(a0,d0.w),d2
        lea     STORE.l,a1
        adda.l  d1,a1
        lea     $58c00.l,a2
        addq.w  #3,d2
        lsr.w   #2,d2
        subq.w  #1,d2
.c:     move.l  (a1)+,(a2)+
        dbra    d2,.c
        clr.b   SIGOK.l                 ; invalidate rd_geom's standing-frame reuse (the key could match a different block)
        movem.l (a7)+,d0-d3/a0-a2
        jmp     $77e6.l
.fall:  movem.l (a7)+,d0-d3/a0-a2
.stock: lea     $58c00.l,a0
        jsr     $d6fa.l
        jmp     $77e6.l

        org     V_ACT
        dc.b    1
