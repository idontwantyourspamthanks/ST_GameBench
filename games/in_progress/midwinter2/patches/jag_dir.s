; name: jag_dir
; default: yes
; site: $26b66
; orig: 7000720014280001
; note: Atari Jaguar pad, part 2 of 3 (work/notes/jagpad.md; poll in jag_poll).  Joystick re-read $26b58 (J mode only: `tst.w $eb76 / beq rts` is its
;       first instruction): `moveq #0,d0 / moveq #0,d1 / move.b 1(a0),d2` (a0 = $75a8, d2 = the IKBD joystick byte: bit0 up, 1 down, 2 left, 3 right)
;       becomes `jsr jag_dir.l / nop`; the blob replays the three instructions and ORs the pad directions PADJ ($b9ee1, written once per VBL
;       by jag_poll, zero without it) into d2. The ramps $75b2..$75be, and through them $6fb6/$6fba, then treat the pad exactly like the stick.
;       $26b58 is also called from the IKBD ISR (it saves only d0-d3/a0): the blob touches d0-d2 only and reads one byte.
PADJ    equ     $b9ee1
        org     $26b66
        jsr     $b9e00.l
        nop

        org     $b9e00
        moveq   #0,d0                   ; displaced
        moveq   #0,d1
        move.b  1(a0),d2
        or.b    PADJ.l,d2
        rts
