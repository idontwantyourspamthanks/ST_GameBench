; name: cp_fetch
; default: yes
; site: $77da
; orig: 41f900058c004eb90000d6fa
; media: hd
; gate: ram2mb
; requires: cp_wrap cp_title cp_ptr cp_end cp_start cp_hiscore
; doc: Campaigns, track fetch: a campaign race reads its track block from the campaign file instead of the game's disk image.
; note: Campaign feature, HD build (work/notes/campaign_hd.md).  Site $77da = `lea $58c00.l,a0 / jsr $d6fa.l` in the race setup: the load of the level's track block into $58c00 (12 bytes) -> `jmp hookb.l`.
; note: With a campaign active hookb does not load: it sets PTR (CPV+8) to the entry's block inside the campaign file (CPSTORE + the entry's offset) and invalidates rd_geom's standing-frame reuse (`clr.b $C0008.l`,
; note: SIGOK: the reuse key holds the six stream pointers and $102c, a different block with the same pointers must not be served from the saved frame), then continues at $77e6 (the loads of the base level's object frames etc.).
; note: Without a campaign it replays the stock load and sets PTR = $58c00.  cp_ptr makes the stream setup read PTR (blocks up to 8192 B parse in place; the six stream pointers are 32 bit).
        org     $77da
        jmp     $B8070.l

        org     $B8070
hookb:  tst.b   CPV.l
        beq.s   .stock
        move.w  CPV+4.l,d0
        mulu    #40,d0
        lea     CPSTORE+16.l,a0
        adda.l  d0,a0
        move.l  28(a0),d0               ; block offset in the file
        addi.l  #CPSTORE,d0
        move.l  d0,CPV+8.l
        clr.b   $C0008.l
        jmp     $77e6.l
.stock: move.l  #$58c00,CPV+8.l
        lea     $58c00.l,a0
        jsr     $d6fa.l
        jmp     $77e6.l
