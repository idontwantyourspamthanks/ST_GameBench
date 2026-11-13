; name: pop2_tick_flip
; default: yes
; site: $1278c
; orig: 4eb900001bfe4eb90002d4c84eb900029226
; note: Fixed-rate world tick, part 4 of 8 (needs pop2_tick; work/notes/timing.md).  The end of the render part of a pass: `jsr $1bfe` (flip: swap $392dc/$392e0, set the
; note: screen address, clear the VBL flag $392cc), `jsr $2d4c8` (an rts) and `jsr $29226` (the command executor: every player slot's command byte $1(a) is run through the
; note: table at $29300 - raise/lower land, effects, the pause toggle - and cleared; while paused only commands > $66 run).  Kind S (catch-up, flag SKIP): no flip, no UI;
; note: the commands run (they belong to turns) and the pass goes back to the loop top $1252a (which re-tests $39628/$39604 itself; the original back-edge $13340 tests
; note: $39604 too).  Kind R (RON): flip but no executor: a command executes once per TURN, not once per frame, so the player's actions per turn, and with them the
; note: balance against the opponent, no longer depend on the speed of the machine.  Kind T and P: the original three calls.
; note: COMMAND QUEUE (work/notes/timing.md section 10).  The UI (keys, clicks; writers `movea.l $473c4.l,a0 / move.b #cmd,$1(a0) / move.b x,$2(a0) / move.b y,$3(a0)`, ~35 sites)
; note: writes the local player's slot at the END of a pass, the executor reads it in the NEXT pass (the executor comes before the UI in the loop, $12798).  The slot holds ONE
; note: command, and an R pass has no executor, so a second command written before the next turn pass overwrote the first.  Now every R pass ends with `harv` (PB+$1100,
; note: at the place of the executor it skips): a command found in the UI's slot is moved to a FIFO of QMAX = 8 entries (D+$60, 4 B each = command, x, y) and the slot is cleared,
; note: exactly what the executor does to it.  Every turn pass (T, S, P) calls `turn` (PB+$1180) instead of `jsr $29226`: if the queue is empty it runs the executor on the
; note: slot as before (so with no command ever queued the game is the stock game, byte for byte); otherwise it first moves the slot's command to the tail (order preserved),
; note: pops the HEAD into the slot and runs the executor: AT MOST ONE queued command per turn pass.  Why one per turn: the stock executor dispatches one command per
; note: slot per pass ($29230-$29250: `move.b $8(a0),d0 / jsr $29258(pc,d0.w)` -> $292dc executes $1(a0), `clr.b $1(a0)`, next slot) and a pass is a turn, so the game has
; note: never run two commands of one player in a turn at 8 MHz (and at 16 MHz it ran one per PASS, i.e. a second per turn, which the tick already removed); draining the
; note: whole queue in one turn would give a burst the stock game cannot produce (e.g. a behaviour change and the effect issued next to it in ONE turn).
; note: Repeats: a held key / mouse button mode ($13088 `tst.w $39406`, keys $63-$66 and $44) writes the same command again in every pass.  A command identical to the one
; note: queued last since the previous turn pass is NOT queued again (LASTH, cleared by every turn pass) - a held input stays one command per turn, as at 8 MHz.  Two
; note: separate clicks of the same command and cell inside one tick (< 0.16 s) are merged too, which is what the stock game does with them (the click latch $39402/$39404
; note: is a flag set at the button-down edge, $1956-$19e6, so two clicks within one pass leave one latch).  A DIFFERENT command is never merged.
; note: Overflow: QMAX = 8; a ninth pending command is dropped (the newest; counter QDROP at D+$50) - it needs more than 8 distinct commands queued, i.e. more than one new distinct
; note: command per turn sustained for 1.3 s.  Counters for the gates: QPUSH D+$48, QPOP D+$4c, QDROP D+$50 (long each).  Fields (control block D, zero in the image): QH.w D+$40,
; note: QN.w D+$42, LASTH.l D+$44, QPUSH D+$48, QPOP D+$4c, QDROP D+$50, queue D+$60..$7f.  Only the slot the UI writes through ($473c4, the local player) is queued; the other
; note: player's slot (written by the computer-player logic inside a turn pass and executed in the same pass) is untouched.  Link games ($29cd0) were not run.
D       equ     PB+$2800
oSKIP   equ     14
oRON    equ     16
oQH     equ     $40
oQN     equ     $42
oLASTH  equ     $44
oQPUSH  equ     $48
oQPOP   equ     $4c
oQDROP  equ     $50
oQ      equ     $60
QMAX    equ     8
HARV    equ     PB+$1100
TURNQ   equ     PB+$1180
        org     $1278c
        jmp     PB+$2300.l

        org     PB+$2300
        tst.w   D+oSKIP.l
        bne.s   .s
        jsr     $1bfe.l
        jsr     $2d4c8.l
        tst.w   D+oRON.l
        bne.s   .r
        jsr     TURNQ.l
.u:     jmp     $1279e.l
.r:     jsr     HARV.l
        bra.s   .u
.s:     jsr     TURNQ.l
        jmp     $1252a.l

; harvest (R pass, in place of the executor): the UI's slot -> the queue tail
        org     PB+$1100
        movem.l d0-d1/a0-a1,-(a7)
        lea     D.l,a0
        bsr.s   harv
        movem.l (a7)+,d0-d1/a0-a1
        rts

; a0 = D; uses d0, d1, a1
harv:   movea.l $473c4.l,a1
        tst.b   1(a1)
        beq.s   .none
        move.l  (a1),d1
        andi.l  #$00ffffff,d1           ; command, x, y
        clr.b   1(a1)                   ; what the executor does to the slot
        clr.w   2(a1)
        cmp.l   oLASTH(a0),d1
        beq.s   .none                   ; the held input of this tick again
        move.l  d1,oLASTH(a0)
        moveq   #0,d0
        move.w  oQN(a0),d0
        cmpi.w  #QMAX,d0
        bhs.s   .full
        add.w   oQH(a0),d0
        andi.w  #QMAX-1,d0
        lsl.w   #2,d0
        move.l  d1,oQ(a0,d0.w)
        addq.w  #1,oQN(a0)
        addq.l  #1,oQPUSH(a0)
.none:  rts
.full:  addq.l  #1,oQDROP(a0)
        rts

; turn pass (T, S, P): at most one queued command, then the game's executor
        ds.b    PB+$1180-*              ; pad to TURNQ (an assembler error if the code above grew past it)
        movem.l d0-d2/a0-a1,-(a7)
        lea     D.l,a0
        tst.w   oQN(a0)
        beq.s   .run                    ; empty: the slot runs as in the stock game
        bsr.s   harv                    ; the slot's command joins the tail
        movea.l $473c4.l,a1
        move.w  oQH(a0),d0
        move.w  d0,d2
        lsl.w   #2,d2
        move.l  oQ(a0,d2.w),d1          ; the head
        addq.w  #1,d0
        andi.w  #QMAX-1,d0
        move.w  d0,oQH(a0)
        subq.w  #1,oQN(a0)
        addq.l  #1,oQPOP(a0)
        move.b  d1,3(a1)
        lsr.l   #8,d1
        move.b  d1,2(a1)
        lsr.l   #8,d1
        move.b  d1,1(a1)
.run:   clr.l   oLASTH(a0)
        movem.l (a7)+,d0-d2/a0-a1
        jmp     $29226.l
