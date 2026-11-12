; name: pop2_tick_anim
; default: no
; site: $20c3e
; orig: 584241f9000329024a7020006e04d47020003742000a
; note: Fixed-rate world tick, part 8 of 8 (needs pop2_tick; work/notes/timing.md).  The one place where DRAWING advances an animation: the draw routine for object kind $0a
; note: (entry $20c00 of the kind table at $2073e, offset 20) steps the frame word `$a(a3)` by 4 through the table at $32902 every time the object is drawn:
; note: $20c3e `addq.w #4,d2` / `lea $32902.l,a0` / `tst.w 0(a0,d2.w)` / `bgt.b $20c50` / `add.w 0(a0,d2.w),d2` (wrap) / $20c50 `move.w d2,$a(a3)`, then `jsr $20f38` draws frame d2.
; note: (The only other stores of the draw code into object records are `bset #0/#1,$4b(player)`, $2081a $20914 $20aa0: visibility bits.)  Originally one draw per pass = one
; note: step per turn.  With render-only passes (R) the object would step once per FRAME, so the animation speed would follow the machine, and with catch-up passes (S: no draw) it
; note: would stall.  A render-only pass now draws the frame the turn pass stored (d2 = $a(a3)) without advancing it; turn passes (and the paused game) run the original
; note: instructions.  No kind-$0a object exists in busy1 or game_start (kinds seen: 2, 4, 18, and 22 in the third list); the gate (p2tick.py ab --both-poke) turns a building record
; note: into kind $0a to exercise this path: `tools/p2tick.py ab busy1 16 60 --both-poke 400ee:0a`.
D       equ     PB+$2800
oRON    equ     16
        org     $20c3e
        jmp     PB+$2600.l
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop

        org     PB+$2600
        tst.w   D+oRON.l
        beq.s   .t
        move.w  $a(a3),d2               ; render-only pass: the stored frame, not advanced
        jmp     $20c54.l
.t:     addq.w  #4,d2
        lea     $32902.l,a0
        tst.w   0(a0,d2.w)
        bgt.s   .st
        add.w   0(a0,d2.w),d2
.st:    move.w  d2,$a(a3)
        jmp     $20c54.l
