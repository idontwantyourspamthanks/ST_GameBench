; name: pop_tick_logic
; default: no
; site: $0b800
; orig: 4eb9 00012fc2
; note: Fixed-rate world tick, part 3 of 6 (needs pop_tick and pop_tick_dot; work/notes/timing.md).  `jsr $12fc2` is the first call of the world block of a pass ($b800 `jsr $12fc2` /
;       $b806 `jsr $db8a` / $b80c `bra.w $b8ec`; the paused and paint-mode path branch away at $b7f6/$b7fe).  A render-only pass (kind R, flag RON: ahead of real time) runs
;       none of it - not $12fc2 (objects), not $db8a (people, buildings, effects, the turn counter), not the block $b8ec-$b93a (shield countdown $3b03e, the event of turn
;       $1000) - so the world stays exactly where the last turn left it.  One thing in the world block is drawing, not logic: `$166f0` (called from $db8a and $12fc2 at $e964 $ec64
;       $ecdc $106c2 $13308) plots one minimap pixel per object into the back buffer through `$167b0`; pop_tick_dot records those calls in a turn pass and this hook replays the list
;       here, at the place of the skipped logic, so the minimap of every frame of a turn shows the same dots.  Execution continues at $b93a (`jsr $d4c0`: the shield display, which
;       draws).  Any other pass: the displaced `jsr $12fc2`, then $b806.
D       equ     $c6000
oRON    equ     16
oWPTR   equ     48
oDOTS   equ     $100
        org     $0b800
        jmp     $c5300.l

        org     $c5300
        tst.w   D+oRON.l
        bne.s   .r
        jsr     $12fc2.l
        jmp     $0b806.l
.r:     movem.l d3/a2,-(a7)
        lea     D+oDOTS.l,a2
        move.l  D+oWPTR.l,d3
.l:     cmpa.l  d3,a2
        bhs.s   .done
        move.w  4(a2),-(a7)             ; the three arguments of `$167b0(screen, x, y, colour)`, pushed as `$166f0` pushes them
        move.w  2(a2),-(a7)
        move.w  (a2),-(a7)
        move.l  $3c510.l,-(a7)
        jsr     $167b0.l
        lea     10(a7),a7
        addq.l  #6,a2
        bra.s   .l
.done:  movem.l (a7)+,d3/a2
        jmp     $0b93a.l
