; name: tc_hit1
; default: yes
; site: $18bf4
; orig: 43f82d807e1f
; doc: Collision scan $18bf4-$18c80 (32 rolling slots, only slots with distance $12-$29 can react): a 4x unrolled one-test filter in front of the stock loop (state identical).
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md).  Stock loop per slot: `btst #0,4(a1) / beq / move.w $20(a1),d1 / cmpi #$12 / blt / cmpi #$29 / bgt` (44-90 cycles).  The filter tests only the distance
; note: ((dist - $12) unsigned <= $17, the same set as the two signed compares) and, on the first slot that passes, loads a1 and d7 as the stock loop would have them and jumps to the stock loop head $18bfa, which
; note: re-tests activity and runs the rest of the scan itself (0.3 hit per pass, so the rest at stock speed is rare).  A scan without hits ends in `rts` like the stock loop ($18c84).  d1-d3 are scratch in the stock loop.
        org     $18bf4
        jmp     $B6A80.l

        org     $B6A80
SCN     macro
        move.w  $20+\1(a1),d1
        sub.w   d2,d1
        cmp.w   d3,d1
        bls.s   \2
        endm
HTP     macro
\1:      lea     \2(a1),a1
        subi.w  #\3,d7
        jmp     $18bfa.l
        endm
tc_hit1:
        lea     $2d80.w,a1
        moveq   #$1f,d7
        moveq   #$12,d2
        moveq   #$17,d3
.u:     SCN     0,.h0
        SCN     $38,.h1
        SCN     $70,.h2
        SCN     $a8,.h3
        lea     $e0(a1),a1
        subq.w  #4,d7
        bpl.s   .u
        rts
        HTP     .h0,0,0
        HTP     .h1,$38,1
        HTP     .h2,$70,2
        HTP     .h3,$a8,3
