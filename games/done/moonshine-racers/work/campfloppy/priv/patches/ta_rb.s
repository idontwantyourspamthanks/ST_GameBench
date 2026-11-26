; name: ta_rb
; default: yes
; site: $d5e6
; orig: 08f80000fa07
; data: $BEE00 128
; doc: Timer B raster list: interrupts whose only job is to write the colour the sky colour register already has are removed (4 of 8 per VBL on the first track); same colour on every scanline, same palette switch.
; note: Tighten wave A (work/notes/tighten_a.md).  Site $d5e6 = `bset.b #0,$fffffa07.w` (enable Timer B) at the end of the per-VBL raster-list builder $d57c-$d5e4 (list at $3d0e: pairs flag/count; flag 0 = write the next colour of the table at $3cbc to $825e, 1 = switch to palette B, 2 = both; count = lines to the next interrupt, 0 = end).
; note: The blob replays the bset, then replaces the list by a compact one: a flag-0 entry whose colour equals the colour already in $825e is dropped (its count is added to the distance of the next kept entry; the first kept distance goes to $fa21), the colours of the kept flag-0/2 entries go to a private table CT and $3cbc is pointed at it (the table at $3cc4 is rebuilt by the fades and is not changed).
; note: The stock ISR $d616 is untouched, so every remaining colour/palette write happens at exactly the instant it does in stock.  Cache: the compact list is a function of ($12fe,$1300) and the colour words $3cc4-$3cd5 (compared every VBL, 9 words); on a hit the cached list is copied (no recompute).
; note: Data $BEE00: +0 KEY long ($12fe/$1300), +4 KCOL 9 words, +22 FIRST word (first interrupt distance), +24 NL word (list length in longs - 1), +32 LST (<= 40 bytes), +80 CT (<= 16 bytes).
KEY     equ     $BEE00
KCOL    equ     $BEE04
FIRST   equ     $BEE16
NL      equ     $BEE18
LST     equ     $BEE20
CT      equ     $BEE50
        org     $d5e6
        jsr     $BE700.l

        org     $BE700
rbhook: bset.b  #0,$fffffa07.w              ; the displaced instruction
        move.l  $12fe.w,d0
        cmp.l   KEY.l,d0
        bne.s   .miss
        lea     $3cc4.w,a0
        lea     KCOL.l,a1
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.l  (a0)+,(a1)+
        bne.s   .miss
        cmpm.w  (a0)+,(a1)+
        bne.s   .miss
.hit:   move.b  FIRST+1.l,$fffffa21.w
        move.l  #CT,$3cbc.l
        lea     LST.l,a0
        lea     $3d0e.w,a1
        move.w  NL.l,d0
.cp:    move.l  (a0)+,(a1)+
        dbra    d0,.cp
        rts
.miss:  move.l  d0,KEY.l
        lea     $3cc4.w,a0
        lea     KCOL.l,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.w  (a0)+,(a1)+
        lea     $3d0e.w,a0              ; the stock list
        lea     LST.l,a1
        lea     CT.l,a2
        lea     $3cc6.w,a3              ; colour table, entry 1 (entry 0 is already in $825e)
        move.w  $3cc4.w,d3              ; colour on screen
        moveq   #0,d4
        move.b  $12ff.w,d4              ; distance to the first interrupt (the byte the stock code put into $fa21)
        lea     FIRST.l,a4              ; slot of the distance to the next kept entry
.lp:    move.w  (a0)+,d0                ; flag
        move.w  (a0)+,d1                ; count
        cmpi.w  #1,d0
        beq.s   .keep                   ; palette switch only: always kept
        move.w  (a3)+,d2                ; colour this entry would write
        tst.w   d0
        bne.s   .kc                     ; flag 2: kept
        cmp.w   d3,d2
        bne.s   .kc
        tst.w   d1
        beq.s   .kc                     ; the end marker entry (count 0) is always kept: it switches the timer off
        add.w   d1,d4                   ; same colour: drop, the distance goes on
        bra.s   .lp
.kc:    move.w  d2,d3
        move.w  d2,(a2)+
.keep:  move.w  d4,(a4)
        move.w  d0,(a1)+
        movea.l a1,a4
        move.w  d1,(a1)+
        move.w  d1,d4
        tst.w   d1
        bne.s   .lp
.fin:   move.l  a1,d0
        sub.l   #LST,d0
        addq.w  #3,d0
        lsr.w   #2,d0
        subq.w  #1,d0
        move.w  d0,NL.l
        bra.w   .hit
