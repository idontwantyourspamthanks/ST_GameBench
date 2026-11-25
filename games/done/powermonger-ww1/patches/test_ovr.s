; name: test_ovr
; default: no
; site: $e7c
; orig: 4a390001d2ae
; note: TEST ONLY (tools/wwstress.py, master test_ovr / buserr.md re-sited, never shipped): counts IKBD ACIA overruns.  In the game's keyboard handler (`$e78: move.b 2(a1),d0` reads the received byte,
;       `$e7c: tst.b $1d2ae.l`) it reads the ACIA status AFTER the data read: the 6850 flags OVRN (bit 5) on the read that follows an overrun.  OVC.w ($ef900) = overruns seen, OVC+2.l = bytes received,
;       OVC+6.l = VBL counter ($71b7c) at the last overrun.  Applied live (HIGH reserve $ef900, never built).
OVC     equ     $ef900
        org     $e7c
        jmp     $ef920.l

        org     $ef920
ov:     addq.l  #1,OVC+2.l
        btst.b  #5,$fffffc00.w
        beq.s   .n
        addq.w  #1,OVC.l
        move.l  $71b7c.l,OVC+6.l
.n:     tst.b   $1d2ae.l
        jmp     $e82.l
