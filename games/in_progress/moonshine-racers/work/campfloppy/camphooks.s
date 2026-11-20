; camphooks.s -- SCRATCH PROTOTYPE (MSRCampFloppy): the redirect sites A-D of work/notes/trackloader.md (pointer variant) for the REAL campaign file format MSTK (trackformat.md section 4),
; store at STORE = $110000 (the file as camp_read left it).  VARS = campread.s `vars` (v_act at +$28, v_count at +$26), -D'd by the harness.  Floppy and HD builds have the same bytes at the four sites.
STORE   equ     $110000
V_ACT   equ     VARS+$28
COUNT   equ     VARS+$26
V_POS   equ     $100f02
PTR     equ     $100f10
SIGOK   equ     $c0008
        org     $100800
hookA:  tst.b   V_ACT.l
        beq.s   .stk
        move.w  $102c.w,d0
        andi.w  #$f,d0
        move.w  d0,V_POS.l                  ; the campaign position
        mulu.w  #40,d0
        lea     STORE+16.l,a0
        move.w  24(a0,d0.l),$102c.w         ; entry.base: every per-level table of the game now reads the BASE level
.stk:   jsr     $76f4.l                     ; race setup + race + exit
        tst.b   V_ACT.l
        beq.s   .x
        move.w  $102c.w,d0
        andi.w  #$8080,d0                   ; flags the race set (time-out replay $80, game over $8000)
        or.w    V_POS.l,d0
        move.w  d0,$102c.w                  ; back to position | flags for the campaign loop at $7306
.x:     rts

        org     $100900
hookB:  tst.b   V_ACT.l
        beq.s   .stock
        movem.l d0-d1/a0,-(a7)
        move.w  V_POS.l,d0
        mulu.w  #40,d0
        lea     STORE+16.l,a0
        move.l  28(a0,d0.l),d1              ; entry.offset
        addi.l  #STORE,d1
        move.l  d1,PTR.l                    ; the block is parsed in place inside the store (site C)
        clr.b   SIGOK.l                     ; rd_geom standing-frame reuse must not survive a different block
        movem.l (a7)+,d0-d1/a0
        jmp     $77e6.l
.stock: move.l  #$58c00,PTR.l
        lea     $58c00.l,a0
        jsr     $d6fa.l
        jmp     $77e6.l

        org     $100a00
hookD:  cmp.w   COUNT.l,d0                  ; d0 = position + 1
        bcc.s   .end
        jmp     $7324.l
.end:   jmp     $732c.l

