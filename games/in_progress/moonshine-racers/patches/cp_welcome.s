; name: cp_welcome
; default: yes
; site: $7c04
; orig: 4a3860ff67f8
; media: hd
; requires: cp_wrap cp_title cp_fetch cp_ptr cp_end cp_start cp_hiscore
; doc: Campaigns: F10 on the "WELCOME PARTNERS ... PRESS A KEY" screen opens the campaign menu too, and the screen says so (a line F10 = CAMPAIGNS under PRESS A KEY). At 1 MB the same screen says 2 MB: CAMPAIGNS + TRACK EDITOR and F10 is an ordinary key.
; note: Campaign feature (HD build; the floppy flow never shows this screen).  Site $7c04 = the key wait of the first screen of the game's manual-question routine ($7bd0, called once after the credits; the question itself is bypassed in this conversion, `bra.w $7d18`):
; note: `tst.b $60ff.w / beq.b $7c02` (the loop adds 1 to d0 = the question's random seed) -> `jmp $B9F0C.l` (cp_title's e3: draws the hint line once per showing, F10 = the campaign menu, any other key = the stock exit $7c0a).  The site is NOT gated: at 1 MB e3 takes its own path (cp_title tests the gate byte IB+4) and only prints `2 MB: CAMPAIGNS + TRACK EDITOR`; no campaign or editor code runs there.
        org     $7c04
        jmp     $B9F0C.l
