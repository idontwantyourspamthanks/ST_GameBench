; trkhook2.s -- SCRATCH PROTOTYPE, variant "pointer" of the stage-2 hooks (MSRLoaderStudy): no copy, no 6144-byte cap.
;   site A  $72c4  jsr $76f4.l -> jsr hookA.l        (same as trkhook.s)
;   site B  $77da  12 B -> jmp hookB.l + 3 nops      hookB sets PTR = the custom block INSIDE THE STORE (or $58c00 after the stock load) and ends with jmp $77e6
;   site C  $fda2  lea.l $58c00.l,a0 (41f900058c00) -> movea.l PTR.l,a0 (2079 <PTR>)    the game's stream setup then parses the block where it is
STORE   equ     $110000
V_ACT   equ     $100f00
V_POS   equ     $100f02
PTR     equ     $100f10
SIGOK   equ     $c0008

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
        movem.l d0-d1/a0,-(a7)
        move.w  V_POS.l,d0
        lsl.w   #3,d0
        lea     STORE+8.l,a0
        tst.b   1(a0,d0.w)
        beq.s   .fall
        move.l  2(a0,d0.w),d1
        addi.l  #STORE,d1
        move.l  d1,PTR.l                ; the block is parsed in place inside the store
        clr.b   SIGOK.l
        movem.l (a7)+,d0-d1/a0
        jmp     $77e6.l
.fall:  movem.l (a7)+,d0-d1/a0
.stock: move.l  #$58c00,PTR.l           ; ACT = 0 or a stock entry: the game's own place
        lea     $58c00.l,a0
        jsr     $d6fa.l
        jmp     $77e6.l

; site D  $731e  `cmpi.w #$f,d0 / bcc.b $732c` (0c40000f 6408) -> jmp hookD.l : the campaign has COUNT entries (1..15), not always 15
        org     $100200
hookD:  cmp.w   COUNT.l,d0                  ; d0 = position + 1 (the value the campaign loop just computed)
        bcc.s   .end
        jmp     $7324.l                     ; next level ($7324: move.w d0,$102c / bra $725c)
.end:   jmp     $732c.l                     ; the ending ($75e8)

        org     V_ACT
        dc.b    1
COUNT   equ     $100f12
        org     COUNT
        dc.w    15
        org     PTR
        dc.l    $58c00
