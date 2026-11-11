; name: pop2_clamp
; default: no
; site: $1cc6
; orig: 13f90000202500002023
; data: PB+$6f10 4
; note: Item 4 (work/notes/display.md): safety net for the IKBD packet parser, ported from Powermonger's p4_clamp.  The game polls the IKBD every VBL
; note: (`move.b #$0d,$fc02.w` at $1a0a, absolute mouse mode set up with `$09 $013f $00c7` = x 0..319, y 0..199 from $1d22) and the reply `$f7 btn xh xl yh yl`
; note: is parsed byte by byte by the ACIA handler $1c42/$1c68 (state $2022: `$f7` -> 5, data bytes stored at $2025+(5-state), at 0 the packet is complete:
; note: $1cc6 `move.b $2025,$2023` (buttons), $1cd0 `move.w $2026,$393fa` (x), $1cda `move.w $2028,$393fc` (y)).  A lost byte (ACIA overrun: the
; note: interrupt waited longer than one 1.28 ms byte, e.g. behind a long blitter burst) shifts the packet and the position words become garbage; the VBL
; note: pointer draw then adds y*160 to the buffer address and writes there (bus error).  This hook runs the displaced instruction, then drops a packet whose
; note: x > 319 or y > 199 (unsigned) by putting the last committed position $393fa/$393fc back into the packet words, so the two copies that follow are no-ops.
; note: Every position the IKBD can send is in range: nothing changes in normal use.

CLAMP   equ     PB+$6400
DROPS   equ     PB+$6f10                ; long: packets dropped (a counter for the proof; read it with the debugger)
        org     $1cc6
        jsr     CLAMP.l
        nop
        nop

        org     PB+$6400
clamp:  move.b  $2025.l,$2023.l         ; the displaced instruction
        cmpi.w  #319,$2026.l
        bhi.s   .bad
        cmpi.w  #199,$2028.l
        bls.s   .ok
.bad:   addq.l  #1,DROPS.l
        move.w  $393fa.l,$2026.l        ; keep the last good position
        move.w  $393fc.l,$2028.l
.ok:    rts
