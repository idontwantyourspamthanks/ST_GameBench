; name: ta_nomouse
; default: no
; site: $d486
; orig: 4eb90000d138
; doc: VBL handler: no IKBD mouse-position query (command $0D, six reply bytes through the ACIA interrupt) while the race runs ($1021 == 2); the race never reads the mouse variables.
; note: Tighten wave A (work/notes/tighten_a.md).  Site $d486: the first instruction of the VBL's body `jsr $d138.l` (`move.b #$d,d0` -> $d19a: wait for the IKBD transmit buffer, write the command byte).  The blob skips it when the mode byte $1021 is 2 (race) and otherwise tail-jumps to $d138.
; note: Evidence that the race does not read the mouse state: the only readers of $6106/$6108/$610f-$6114 are the menu/cursor routines ($169de $16b5c $16bca $17172); a memory-read trace over 2400 emulated race passes (levels 0/5/14, 2 inputs) shows zero reads of $6106-$6114.
; note: Risk (not proven absent): the IKBD stays in absolute-mouse mode but is not interrogated; a reply to the last query before the switch is complete within its own VBL.  Joystick/keyboard packets are independent of the query.
        org     $d486
        jsr     $BE500.l

        org     $BE500
nomouse:
        cmpi.b  #2,$1021.w
        bne.s   .q
        rts
.q:     jmp     $d138.l
