; name: test_ovr
; default: no
; stage: 2
; site: $18e8
; orig: 4a390001c48e
; data: $cef20 16
; note: TEST ONLY (PMBusErr, work/notes/buserr.md): counts IKBD ACIA overruns.  In the game's keyboard handler (`$18e4: move.b 2(a1),d0` reads
;       the received byte, `$18e8: tst.b $1c48e.l`) it reads the ACIA status AFTER the data read: the 6850 flags OVRN (bit 5) on the read that
;       follows an overrun.  OVC.w ($cef20) = overruns seen, OVC+2.l = bytes received, OVC+6.l = VBL counter ($6f304) at the last overrun.
OVC     equ     $cef20
        org     $18e8
        jmp     $cee00.l

        org     $cee00
ov:     addq.l  #1,OVC+2.l
        btst.b  #5,$fffffc00.w
        beq.s   .n
        addq.w  #1,OVC.l
        move.l  $6f304.l,OVC+6.l
.n:     tst.b   $1c48e.l
        jmp     $18ee.l
