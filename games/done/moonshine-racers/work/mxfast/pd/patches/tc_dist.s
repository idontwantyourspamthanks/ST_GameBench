; name: tc_dist
; default: yes
; site: $e2e8
; orig: 41f82d807e1f
; doc: Object distance update $e2e8 (32 rolling slots, `$20 -= $130c`) unrolled 4x with the subtract done in memory (state identical).
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md).  Stock: per slot `btst #0,4(a0) / beq / move.w $20(a0),d0 / sub.w $130c.w,d0 / bpl / move.w d0,$20(a0) / ... lea / dbra` (88 cycles active, 44 inactive).
        org     $e2e8
        jmp     $B6A00.l

        org     $B6A00
SLOT    macro
        btst    #0,\1(a0)
        beq.s   .n\@
        sub.w   d0,\2(a0)
        bpl.s   .n\@
        add.w   d0,\2(a0)               ; negative: the stock code leaves $20 unchanged and only clears the active bit
        bclr    #0,\1(a0)
.n\@:
        endm
tc_dist:
        lea     $2d80.w,a0
        move.w  $130c.w,d0
        moveq   #7,d7
.u:     SLOT    4,$20
        SLOT    4+$38,$20+$38
        SLOT    4+$70,$20+$70
        SLOT    4+$a8,$20+$a8
        lea     $e0(a0),a0
        dbra    d7,.u
        rts
