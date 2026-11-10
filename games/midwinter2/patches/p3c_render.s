; name: p3c_render
; default: yes
; site: $3158c
; orig: 4eb850b04a786298
; note: Render side of the p3c / p3cp scheduler (replaces tick_render; work/notes/vehicles_p3b.md). Original code at the
;       render gate: `jsr $50b0.w` (HUD gauge draw $19f54), `tst.w $6298.w`; then
;       `beq.b $3159c` (clr $7020, view setup, renderer, ...).
;       The gauge draw must run once per PRESENTED frame, not once per logic pass:
;       $1a706 sets the dirty counters ($1812a-$18138) to 2 (one per screen buffer)
;       and every $19f54 call draws into the current back buffer and decrements
;       them. So:
;         SKIP ($b42ec, word +12 of the scheduler's block D) = 1 (another pass owed) and $6298 = 0:
;           no render, no gauge draw; clr $7020 as tick_render did, and back to the loop head.
;         otherwise: gauge draw as the original, flags set for the original beq.
;       The extra passes' renders (PH 2-5) enter here from the head via `jmp $3158c`.
SKIP    equ     $b42ec
        org     $3158c
        jsr     $b4102.l
        nop

        org     $b4102
        tst.w   SKIP.l
        beq.s   .draw
        tst.w   $6298.w
        bne.s   .draw                   ; the $6298 path presents a frame anyway
        clr.w   $7020.w                 ; displaced (game waits rely on it)
        addq.l  #4,a7                   ; drop our return address
        jmp     $31486.l                ; next pass, no render
.draw:  jsr     $50b0.w                 ; displaced
        tst.w   $6298.w                 ; displaced; flags for the beq.b at $31594
        rts
