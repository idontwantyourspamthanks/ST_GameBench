; name: jag_btn
; default: yes
; site: $665e
; orig: 141002420003
; note: Jaguar pad support, part 3 of 4 (see jag_vbl; work/notes/jagpad.md).  $665e is the button entry of the input funnel (reached from the
;       mouse packet $664a, the joystick re-read $65c0 and the key poll $652e): `move.b (a0),d2 / andi.w #3,d2` = the IKBD button byte
;       (bit 1 left, bit 0 right) -> $24fba, with the latch $24fa0 cleared while no button is down.  A joystick-1 fire reaches this as the
;       right-button bit; the pad fire (PADBTN = 1, B) is OR-ed in the same way, so $24fa0 and the latches behave as for the real fire.
        org     $665e
        jsr     $b6c10.l

        org     $b6c10
        move.b  (a0),d2                 ; displaced
        or.b    $b6bf2.l,d2             ; PADBTN (jag_vbl)
        andi.w  #3,d2                   ; displaced; the flags are the ones `bne.b $666c` tests
        rts
