; name: jag_stick
; default: yes
; requires: jag_pad
; site: $c64c
; orig: 102d00d11b4000d0
; note: Second splice of the Jaguar pad feature (jag_pad.s has the poll and the full note).  The VBL world block copies the IKBD joystick
; note: byte to the game's stick state: `move.b $d1(a5),d0 / move.b d0,$d0(a5)`, then `lsr.b #4,d0 / andi.b #1,d0 / move.b d0,$cf(a5)`
; note: (fire level from bit 4) and `jsr $355a` (camera / turn / accelerate ramps).  Here the pad's stick byte J_DIR (N=2 S=1 E=4 W=8
; note: fire=$10, 0 with no pad or nothing pressed) is OR-ed into the value, so every consumer ($cf, $355a, $26c0, the fire code) sees pad
; note: and joystick as one stick.  $d1 itself is never written (the IKBD packet decoder owns it).  The block runs on world ticks only
; note: (hn_hz), so the merge is gated exactly like the real stick.  `jmp` out and `jmp` back ($c654): +40 cycles per tick; the probe of
; note: jag_pad restores the original 8 bytes here on a machine without pad ports.
JAG_DIR  equ    $8d9e4                  ; JAG + J_DIR (jag_pad.s)
JAG_MERGE equ   $8d9c0

        org     $c64c
        jmp     JAG_MERGE.l             ; replaces `move.b $d1(a5),d0 / move.b d0,$d0(a5)` (8 bytes)
        nop                             ; (never executed: the blob returns to $c654)

        org     $8d9c0
jag_merge:
        move.b  $d1(a5),d0
        or.b    JAG_DIR.l,d0
        move.b  d0,$d0(a5)
        jmp     $c654.l
