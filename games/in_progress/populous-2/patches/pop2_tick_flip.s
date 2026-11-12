; name: pop2_tick_flip
; default: yes
; site: $1278c
; orig: 4eb900001bfe4eb90002d4c84eb900029226
; note: Fixed-rate world tick, part 4 of 8 (needs pop2_tick; work/notes/timing.md).  The end of the render part of a pass: `jsr $1bfe` (flip: swap $392dc/$392e0, set the
; note: screen address, clear the VBL flag $392cc), `jsr $2d4c8` (an rts) and `jsr $29226` (the command executor: every player slot's command byte $1(a) is run through the
; note: table at $29300 - raise/lower land, effects, the pause toggle - and cleared; while paused only commands > $66 run).  Kind S (catch-up, flag SKIP): no flip, no UI;
; note: the commands run (they belong to turns) and the pass goes back to the loop top $1252a (which re-tests $39628/$39604 itself; the original back-edge $13340 tests
; note: $39604 too).  Kind R (RON): flip but no `jsr $29226`: a command (a held mouse button keeps writing its command every pass) executes once per TURN, not
; note: once per frame, so the player's actions per turn, and with them the balance against the opponent, no longer depend on the speed of the machine; the commands
; note: wait in their slot (the UI writes the same bytes again) until the next turn pass.  Kind T and P: the original three calls.
D       equ     PB+$2800
oSKIP   equ     14
oRON    equ     16
        org     $1278c
        jmp     PB+$2300.l

        org     PB+$2300
        tst.w   D+oSKIP.l
        bne.s   .s
        jsr     $1bfe.l
        jsr     $2d4c8.l
        tst.w   D+oRON.l
        bne.s   .r
        jsr     $29226.l
.r:     jmp     $1279e.l
.s:     jsr     $29226.l
        jmp     $1252a.l
