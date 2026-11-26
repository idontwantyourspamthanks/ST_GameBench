; name: tc_hit2
; default: no
; site: $18c86
; orig: 41f82d807e1f
; doc: Hit-effect scan $18c86 (32 rolling slots, act on slots flagged active + bit 4 of $5): a 4x unrolled one-test filter in front of the stock loop (state identical).
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md).  Stock per slot: `btst #0,4(a0) / beq / btst #4,5(a0) / beq` (44-68 cycles incl. lea/dbra).  Flags $4/$5 read as one word: both bits set <=> (not w) & $0110 == 0.
; note: On the first slot that passes, a0 and d7 are loaded as the stock loop would have them and the stock loop head $18c8c takes over (it ends in the stock `rts`); no hit at all ends in `rts` here.  Only d0/d7/a0 are used (the stock loop clobbers those).
        org     $18c86
        jmp     $B6B40.l

        org     $B6B40
SCN     macro
        move.w  4+\1(a0),d0
        not.w   d0
        and.w   #$0110,d0
        beq.s   \2
        endm
HTP     macro
\1:      lea     \2(a0),a0
        subi.w  #\3,d7
        jmp     $18c8c.l
        endm
tc_hit2:
        lea     $2d80.w,a0
        moveq   #$1f,d7
.u:     SCN     0,.h0
        SCN     $38,.h1
        SCN     $70,.h2
        SCN     $a8,.h3
        lea     $e0(a0),a0
        subq.w  #4,d7
        bpl.s   .u
        rts
        HTP     .h0,0,0
        HTP     .h1,$38,1
        HTP     .h2,$70,2
        HTP     .h3,$a8,3
