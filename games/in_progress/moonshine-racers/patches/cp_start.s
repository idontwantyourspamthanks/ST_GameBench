; name: cp_start
; default: yes
; site: $7252
; orig: 4eb9000073b8
; media: hd
; gate: ram2mb
; requires: cp_wrap cp_title cp_fetch cp_ptr cp_end cp_hiscore
; doc: Campaigns, start of a game: "Play from track N" starts the campaign at track N.
; note: Campaign feature, HD build.  Site $7252 = `jsr $73b8.l` right after `clr.w $102c` at the start of a new game (title screen key exit): the stock call, then, with a campaign active, $102c := START (the track
; note: chosen in the menu, 0 = the first) and START is cleared.  The map screens and the race that follow then see the position as in a game that has reached that track.
        org     $7252
        jsr     $B8240.l

        org     $B8240
hooks:  jsr     $73b8.l
        tst.b   CPV.l
        beq.s   .x
        move.w  CPV+6.l,$102c.w
        clr.w   CPV+6.l
.x:     rts
