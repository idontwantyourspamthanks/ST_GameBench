; name: cp_wrap
; default: yes
; site: $72c4
; orig: 4eb9000076f4
; media: hd
; gate: ram2mb
; requires: cp_title cp_fetch cp_ptr cp_end cp_start cp_hiscore
; data: $B8E00 32
; doc: Campaigns, race wrapper: a race of a campaign runs with the base level's scenery, colours and tables.
; note: Campaign feature, HD build (work/notes/campaign_hd.md; design: work/notes/trackloader.md section 4).  Site $72c4 = `jsr $76f4.l` in the campaign loop, the whole race (setup, loop and exit all run inside $76f4, its only caller).
; note: With a campaign active the position ($102c & $f, the campaign loop's own count) is saved in POS and $102c is set to the entry's BASE level for the duration of the race: every per-level table of the game
; note: (scenery, colours, sky, object frames, race length, time limit, opponents, speech: 40 readers) then reads the base level.  After the race $102c is position | the flags the race set ($80 = time-out
; note: replay, $8000 = game over), so the campaign loop at $7306 (and the map screens, "LEVEL n") keep seeing the position.  Without a campaign (ACT = 0) it is the stock `jsr $76f4`.
; note: Variables (payload data, zero when the trampoline runs): CPV+0 ACT.b, +1 LOADED.b, +2 COUNT.w, +4 POS.w, +6 START.w, +8 PTR.l (block pointer, cp_fetch/cp_ptr).  The campaign file sits at CPSTORE ($110000): entry i at +16+40*i, base level word at +24.
        org     $72c4
        jsr     $B8022.l

        org     $B8022
hooka:  tst.b   CPV.l
        beq.s   .stk
        move.w  $102c.w,d0
        andi.w  #$f,d0
        move.w  d0,CPV+4.l
        mulu    #40,d0
        lea     CPSTORE+16+24.l,a0
        move.w  (a0,d0.w),$102c.w       ; the entry's base level
.stk:   jsr     $76f4.l
        tst.b   CPV.l
        beq.s   .x
        move.w  $102c.w,d0
        andi.w  #$8080,d0
        or.w    CPV+4.l,d0
        move.w  d0,$102c.w
.x:     rts
