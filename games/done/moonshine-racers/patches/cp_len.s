; name: cp_len
; default: yes
; site: $7926
; orig: 4eb90000edea
; gate: ram2mb
; requires: cp_title cp_fetch cp_ptr
; doc: Campaigns, race length per track: a campaign track with its own race length (MSTRACKS.TRK version 2) races with that length and a time limit that follows the pace of its scenery; on HD this hook also starts the track editor's test drive.
; note: Site $7926 = `jsr $edea.l` in the race setup $76f4 (HD and floppy builds): $edea is the last step (the race state variables and the time bar are initialised, the rings, the objects and the opponents already stand at unit 0).
; note: It replaces cp_td (same blob address $B8260: the editor's site test `cmpi.w #$4eb9,$7926.w` of c_td still matches).  hookl runs $edea, then, when V_RLEN (CPV+16: the campaign entry's race length word, set by cp_fetch; 0 = the
; note: base level's = every version 1 track, the stock game and every race without a campaign) is not 0: P = (Tb - 100) * L / Lb + 100 passes, Tb = $ff0000 / $10d2 (the passes the BASE level allows: $edea's
; note: `$10d2 = (100 + $102c) * $57890 / 200 + (10 - $edcc[$102c]) * 200` is proportional to the length, so a plain `$57890 = L` before $edea would give a long road LESS time), Lb = the base level's length ($57890 still
; note: holds it).  The pace of the scenery's own level is kept (a track as long as the original gets the original's time) and a fixed start of 100 passes is added (start lights 55 passes + getting up to speed).  The time bar
; note: rate becomes $ff0000 / P, at most $ffff (= 255 passes: shorter limits are floored at 255 passes).  $57890 word 0 = L from then on: the progress compare ($fbc4: `$5ff8 * 256 / len`, behind-schedule messages) is measured
; note: against the built length.  $57890 is reloaded by every race setup ($7792, before the track fetch), so the overwrite never reaches the next race.  The rest of $edea's state is untouched.
; note: HD build only: when V_TD (CPV+14, the editor's flag around its own call of the race, work/notes/editor_design.md 13) is set it then calls the overlay's td_ff (EDBASE+20), which fast-forwards the rings / the objects /
; note: the speech pointer to the cursor unit, sets `$5ff8` and the time bar, and installs the test-drive hooks.  Without either (every v1 campaign or stock race) the hook is `jsr $edea / movem / move.w / beq / movem / (tst.b / beq) / rts`.
V_RLEN  equ     CPV+16          ; w  the campaign entry's own race length (0 = the base level's), set by cp_fetch at every track fetch

        org     $7926
        jsr     $B8260.l

        org     $B8260
hookl:  jsr     $edea.l
        movem.l d0-d2,-(a7)
        move.w  V_RLEN.l,d1             ; this track's own length L (0: none)
        beq.s   .n
        move.l  #$ff0000,d0
        divu    $10d2.w,d0              ; Tb = the passes the base level allows (1184..1678 for the 15 levels)
        subi.w  #100,d0                 ; less the start allowance
        mulu    d1,d0
        divu    $57890.l,d0             ; (Tb - 100) * L / Lb  (at most 2455 for L <= 28000)
        addi.w  #100,d0                 ; P = the passes this race allows
        move.l  #$ff0000,d2
        divu    d0,d2                   ; the time bar's rate; overflows (V) for P < 255 ...
        bvc.s   .ok
        moveq   #-1,d2                  ; ... then the fastest bar a word holds: 255 passes
.ok:    move.w  d2,$10d2.w
        move.w  d1,$57890.l             ; progress is measured against the built length from here on
.n:     movem.l (a7)+,d0-d2
        ifeq    FLOPPY
        tst.b   CPV+14.l                ; V_TD: the editor's test drive
        beq.s   .x
        jsr     EDBASE+20.l
.x:     endc
        rts
