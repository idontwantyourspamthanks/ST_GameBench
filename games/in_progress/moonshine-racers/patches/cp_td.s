; name: cp_td
; default: yes
; site: $7926
; orig: 4eb90000edea
; gate: ram2mb
; media: hd
; requires: cp_title cp_fetch cp_ptr
; doc: Track editor test drive: a race the editor starts from the cursor begins at the cursor's unit instead of unit 0 (HD build, ST family with 2 MB or more).
; note: Site $7926 = `jsr $edea.l` in the race setup $76f4: $edea is the last step (the race state variables and the time bar are initialised, the rings, the objects and the opponents already stand at unit 0).  hooktd runs it, then, only
; note: when V_TD (CPV+14: the editor's flag, set around its own call of the race, work/notes/editor_design.md 13) is set, calls the overlay's td_ff (EDBASE+20), which fast-forwards the rings / the objects / the speech pointer to the
; note: cursor unit, sets `$5ff8` and the time bar, and installs the test-drive hooks.  Without the flag (every campaign or stock race) it is `jsr $edea / tst.b / beq / rts` (about 40 cycles per race).
        org     $7926
        jsr     $B8260.l

        org     $B8260
hooktd: jsr     $edea.l
        tst.b   CPV+14.l
        beq.s   .x
        jsr     EDBASE+20.l
.x:     rts
