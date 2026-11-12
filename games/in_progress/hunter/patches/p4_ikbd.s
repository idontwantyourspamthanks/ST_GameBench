; name: p4_ikbd
; default: yes
; site: $c5fa
; note: item (c) (work/notes/p4_raster.md). The VBL handler ($c5f0) polls the joysticks every VBL: `moveq #$16,d0 / bsr.w $afbe`
; note: ($afbe stores the byte at $1d4(a5), then $afc4: wait for ACIA TDRE (btst #1,$fffc00), then a 200-iteration
; note: `nop/dbra` delay (2800 cycles = 350 us at 8 MHz, 2.4 % of ALL cycles), then `move.b (a0)+,$fffc02`).
; note: This site replaces the poll with the same store + the TDRE wait + the write, without the delay. The multi-byte
; note: command senders ($af72 init, $afaa) keep the original $afc4 with its delay. Safety argument: p4_raster.md section 2.
        org     $c5fa
        jsr     $8c000.l

        org     $8c000
        moveq   #$16,d0
        move.b  d0,$1d4(a5)
.w:     btst.b  #1,$7c00(a6)            ; ACIA TDRE (a6 = $ff8000 game-wide: $7c00(a6) = $fffc00)
        beq.s   .w
        move.b  d0,$7c02(a6)            ; $fffc02: IKBD "interrogate joysticks"
        rts
