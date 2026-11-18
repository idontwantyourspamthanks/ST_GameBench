; Nebulus input: sticky fire latch (NebInput2).  Blob at NI = $76d00 (inside the verified-zero gap $76b10..$77ec0; trainers use $76c00..$76c75).
; The game keeps one "last IKBD byte" cell $38498 and samples it once per game loop (every 2 VBL).  A fire press whose release byte arrives
; before the next sample is lost.  stub1 (ACIA store hook) latches every joystick byte with fire; stub2 (fire-flag store inside the poll
; sub_03853a) ORs the latch into the fire flag once and clears it.  A held press behaves exactly as before (the latch is consumed by the
; first poll, the level keeps the flag); scancode bytes (bits 4-6 set) never latch.
NI      equ $76d00
        org NI
sticky: dc.w 0                      ; NI+0  latch (zero at boot: the gap is zero)
        dc.w 0                      ; NI+2  pad
stub1:                              ; NI+4  site $38514 (6 B): move.b d0,$38498.l  ->  jmp stub1 ; continues at $3851a
        move.b d0,$38498.l
        andi.b #$f0,d0              ; d0 is free here: $3851a restores it from the stack
        cmpi.b #$80,d0
        bne.s .n
        move.w #1,NI.l
.n:     jmp $3851a.l
        cnop 0,2
stub2:                              ; site $3855a (6 B): move.w d1,$338f0.l  ->  jsr stub2
        tst.w NI.l
        beq.s .s
        move.w #1,d1
        clr.w NI.l
.s:     move.w d1,$338f0.l
        rts
