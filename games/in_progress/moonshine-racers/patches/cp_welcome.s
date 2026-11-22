; name: cp_welcome
; default: yes
; site: $7c04
; orig: 4a3860ff67f8
; gate: ram2mb
; requires: cp_wrap cp_title cp_fetch cp_ptr cp_end cp_start cp_hiscore
; doc: Campaigns: F10 on the "WELCOME PARTNERS ... PRESS A KEY" screen opens the campaign menu too, and the screen says so (a line F10 = CAMPAIGNS under PRESS A KEY).
; note: Campaign feature (HD and floppy builds).  Site $7c04 = the key wait of the first screen of the game's manual-question routine ($7bd0, called once after the credits; the question itself is bypassed in this conversion, `bra.w $7d18`):
; note: `tst.b $60ff.w / beq.b $7c02` (the loop adds 1 to d0 = the question's random seed) -> `jmp $B9F0C.l` (cp_title's e3: draws the hint line once per showing, F10 = the campaign menu, any other key = the stock exit $7c0a).
        org     $7c04
        jmp     $B9F0C.l
