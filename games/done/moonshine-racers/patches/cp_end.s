; name: cp_end
; default: yes
; site: $731e
; orig: 0c40000f6408
; gate: ram2mb
; requires: cp_wrap cp_title cp_fetch cp_ptr cp_start cp_hiscore
; doc: Campaigns, end of the campaign: after the last track of a shorter campaign the game's own ending runs.
; note: Campaign feature (HD and floppy builds).  Site $731e = `cmpi.w #$f,d0 / bcc.b $732c` in the campaign loop (d0 = the finished position + 1): 15 tracks -> next level $7324, else the ending $732c ($75e8 the ending picture, $ef46,
; note: then the title).  With a campaign active the limit is its track count; without one it is 15, as the stock game.
        org     $731e
        jmp     $B8220.l

        org     $B8220
hookd:  moveq   #15,d1
        tst.b   CPV.l
        beq.s   .s
        move.w  CPV+2.l,d1
.s:     cmp.w   d1,d0
        bcc.s   .end
        jmp     $7324.l
.end:   jmp     $732c.l
