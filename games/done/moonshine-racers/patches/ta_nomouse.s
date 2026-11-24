; name: ta_nomouse
; default: yes
; site: $d486
; orig: 4eb90000d138
; doc: VBL handler: no IKBD mouse-position query (command $0D, six reply bytes through the ACIA interrupt) while the race itself runs (the game's own race flag $1028 is set); the race never reads the mouse variables.
; note: v1.0.1: v1.0 gated on the mode byte $1021 == 2, but $1021 is also 2 in the spare-parts shop after a race and on the title/"Hi I'm Ike" screen, so the pointer froze there and the shop's EXIT could not be used (confirmed in Hatari on the shipped zips and on the user's MiSTer).  The stock game sets $1028 at $72c0 (`st.b`) and clears it at $72d0 (`clr.b`) around the race call `jsr $76f4` (pause included); its only other reader is $11f8a.  Gating on $1028 keeps the race saving and gives every other screen its mouse back (MSRShopMouse: shop pointer moves and EXIT works on HD/floppy STE, Mega STE, ST; race pace equal to v1.0).
; note: Tighten wave A (work/notes/tighten_a.md).  Site $d486: the first instruction of the VBL's body `jsr $d138.l` (`move.b #$d,d0` -> $d19a: wait for the IKBD transmit buffer, write the command byte).  The blob skips it while $1028 is set (race) and otherwise tail-jumps to $d138.
; note: Evidence that the race does not read the mouse state: the only readers of $6106/$6108/$610f-$6114 are the menu/cursor routines ($169de $16b5c $16bca $17172); a memory-read trace over 2400 emulated race passes (levels 0/5/14, 2 inputs) shows zero reads of $6106-$6114.
; note: Risk (not proven absent): the IKBD stays in absolute-mouse mode but is not interrogated; a reply to the last query before the switch is complete within its own VBL.  Joystick/keyboard packets are independent of the query.
        org     $d486
        jsr     $BE500.l

        org     $BE500
nomouse:
        tst.b   $1028.w
        beq.s   .q
        rts
.q:     jmp     $d138.l
