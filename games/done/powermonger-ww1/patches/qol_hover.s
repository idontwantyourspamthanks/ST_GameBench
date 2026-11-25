; name: qol_hover
; default: yes
; site: $13e2a
; orig: 4eb90001853a
; data: $73900 48
; note: village hover tooltip (master qol_hover / work/notes/qol.md, re-sited and adapted to WW1's build order).  Resting the pointer on a house of a town in the 3D view shows, in the
;       top-bar tooltip area (rows 0-5, columns 7-19, the same place and font as pm_tooltip), "<town name>: making <item>s (NN%)" = the town's current Build item (rifles, planes,
;       tanks, pikes ... the game's own item names from the table $9cd0) and how far its countdown has run.  REQUIRES pm_tooltip (uses its compose_sb / blit exports $73406 / $7340c and
;       its liveness word 'PTIP' at $7480e) AND qol_hover2 (the sprite hook at $12ee0 that finds the house under the pointer); without qol_hover2 nothing is ever shown.
;       Settlement record (table $53332, stride $20, offset = $e(house)): +0 owner byte (0 = unused), +2 first house, +4 word name seed (the name generator $a3be, the same name the
;       Query window prints), +$c word = item being made (0 = nothing yet; written by the build order $505a), +$10 word = countdown to the next item (-1 per work step, $5324; at 0 the
;       item is added to the stock +$18+n and the countdown restarts at T = [$5a914 + owner * $20 + 8] + 4, + $400 for plane / tank: $5340-$5354).  Progress = (T - countdown) * 100 / T,
;       clamped to 0..99.  Without an item: "<name>: workshop idle" when the chain of houses ($2(settlement), next = $8(house)) has a workshop (kind byte $7 = 7), else "<name>: no workshop".
;       While the Build icon is selected and waits for a target ($5a836 = $e) the hover says what Build would make HERE ("Build here: tanks (3 swords)", see `predict`).
;       How the house is found: the game's own object pick.  The sprite routine $12ee0 (called once per drawn object: d0/d1 = sprite top-left, a3 = the object record) compares the
;       pointer $2edb2/$2edb4 with the sprite square (tables $12e92 / $12ebe size by zoom, plus WW1's extra `cmpi.b #$e,$2c(a3)` -> 24) - that is what a Query click uses.  qol_hover2 (HVHOOK)
;       replaces its first instruction (`tst.w $5a836`) with a call to HVHOOK, which returns after doing that same instruction; unarmed it costs one `tst.w`.  Armed it runs the same square
;       test with the live pointer and remembers the LAST object that hits and lies in the house table $54234..$5574c (300 records of $12; the word at $5574c is the free-slot counter).
;       Armed only for ONE pass after the pointer and the view (scroll, heading, tilt, zoom words) have been still for 10 VBL (0.2 s): ARM = 1 is set by the pass hook, the next render's
;       sprite hook raises it to 2 and fills HIT, the pass hook after that render resolves it.  Every pass while a town is hovered: the text is blitted into the back buffer after the render
;       (pm_tooltip's BUF); it is recomposed only when the key (settlement, item, percent) changes.  An icon tooltip of pm_tooltip or an open window ($74c0) wins over the hover.
;       Site: `jsr $1853a` ($13e2a, the HUD call right after the landscape / object render $13e1e and the weather step $13e24): the pass hook; the sprite hook is qol_hover2.
;       State HS ($73900): +0 ARM.w +2 HIT.l +6 LX.w +8 LY.w +$A REST.l (VBL stamp of the last change) +$e RES.w +$10 HKEY.l +$14 SIG (7 words).
HS      equ     $73900
ARM     equ     0
HIT     equ     2
LX      equ     6
LY      equ     8
REST    equ     $a
RES     equ     $e
HKEY    equ     $10
SIG     equ     $14
S       equ     $74800                  ; pm_tooltip's state
sID     equ     4
sKEY    equ     6
sMAG    equ     $e
sHK     equ     $12
SB      equ     S+$290

        org     $13e2a
        jsr     $74b00.l                ; hpass

        org     $74b00
; ---- hpass (the pass hook at $13e2a) -------------------------------------------------------------------------------------------------
sg      macro                           ; \1 = a camera word; d2 <> 0 when it differs from the stored copy (which is updated)
        move.w  \1.l,d3
        cmp.w   (a0),d3
        beq.s   .s\@
        moveq   #1,d2
        move.w  d3,(a0)
.s\@:   addq.l  #2,a0
        endm

hpass:  movem.l d0-d7/a0-a6,-(a7)
        cmpi.l  #$50544950,S+sMAG.l     ; pm_tooltip is alive (its hook ran this pass)
        bne     .out
        lea     HS.l,a6
        cmpi.w  #2,ARM(a6)
        bne.s   .na                     ; ARM 2 = the sprite hook ran in this pass's render: HIT is filled
        clr.w   ARM(a6)
        move.w  #1,RES(a6)
.na:    moveq   #0,d2                   ; d2 <> 0: pointer or view changed
        move.w  $2edb2.l,d0
        cmp.w   LX(a6),d0
        beq.s   .x
        moveq   #1,d2
        move.w  d0,LX(a6)
.x:     move.w  $2edb4.l,d0
        cmp.w   LY(a6),d0
        beq.s   .y
        moveq   #1,d2
        move.w  d0,LY(a6)
.y:     lea     SIG(a6),a0
        sg      $50fd4
        sg      $50fd6
        sg      $1040a
        sg      $10406
        sg      $10408
        sg      $1040c
        sg      $5a860
        tst.w   d2
        beq.s   .still
        move.l  $71b7c.l,REST(a6)       ; moved: forget the pick, the clock restarts
        clr.w   RES(a6)
        clr.l   HIT(a6)
        clr.w   ARM(a6)
        bra     .out
.still: tst.w   S+sID.l                 ; an icon tooltip owns the bar / a window covers the view: no hover
        bne     .out
        tst.w   $74c0.l
        bne     .out
        tst.w   RES(a6)
        bne.s   .have
        move.l  $71b7c.l,d3             ; not picked yet: arm for the next render once the pointer has rested 10 VBL
        sub.l   REST(a6),d3
        cmp.l   #10,d3
        blo     .out
        clr.l   HIT(a6)
        move.w  #1,ARM(a6)              ; the next RENDERED pass fills HIT (a pass without a render leaves ARM at 1)
        bra     .out
.have:  move.l  HIT(a6),d0
        beq     .out
        movea.l d0,a3
        tst.b   5(a3)                   ; house still in use
        ble     .out
        moveq   #0,d0
        move.w  $e(a3),d0               ; settlement offset
        cmp.w   #$f00,d0                ; WW1: 120 settlement records of $20 from $53332
        bhs     .out
        lea     $53332.l,a2
        adda.w  d0,a2
        tst.b   (a2)
        beq     .out
        cmpi.w  #$e,$5a836.l            ; the Invent icon is selected and waits for a target: say what Build would make HERE
        beq     .pred
        ; ---- workshop info: item code d5 (0 none, 1 = idle workshop, 2..$10 an item) and percent d4
        moveq   #0,d4
        moveq   #0,d5
        move.w  $c(a2),d5
        beq.s   .noitem
        cmp.w   #$10,d5
        bhi.s   .noitem
        btst    #0,d5
        bne.s   .noitem
        moveq   #0,d1                   ; T = [$5a914 + owner * $20 + 8] + 4 (+ $400 for plane / tank: $5324-$5354)
        move.b  (a2),d1
        lsl.w   #5,d1
        lea     $5a914.l,a0
        move.w  8(a0,d1.w),d1
        addq.w  #4,d1
        cmp.w   #$e,d5
        blo.s   .t
        add.w   #$400,d1
.t:     moveq   #0,d2
        move.w  $10(a2),d2              ; countdown
        cmp.w   d1,d2
        bhi.s   .pc0                    ; above T (stale): 0 %
        tst.w   d1
        beq.s   .pc0
        moveq   #0,d3
        move.w  d1,d3
        sub.l   d2,d3
        mulu.w  #100,d3                 ; (T - countdown) * 100: <= 820600
        divu.w  d1,d3
        move.w  d3,d4
        cmp.w   #99,d4
        bls.s   .wk
        moveq   #99,d4
        bra.s   .wk
.pc0:   moveq   #0,d4
        bra.s   .wk
.noitem:moveq   #0,d5
        moveq   #0,d4
        move.w  2(a2),d1                ; first house of the settlement: is there a workshop (kind 7) in the chain?
        beq.s   .wk
        lea     $54234.l,a0
.w:     cmpi.b  #7,7(a0,d1.w)
        beq.s   .ws
        move.w  8(a0,d1.w),d1
        bne.s   .w
        bra.s   .wk
.ws:    moveq   #1,d5
.wk:    move.w  d5,d3                   ; W = code << 7 | percent
        lsl.w   #7,d3
        or.w    d4,d3
        bra.s   .key
.pred:  bsr     predict                 ; W = $8000 | reason << 12 | item A << 6 | item B
.key:   moveq   #0,d6                   ; key = settlement offset << 16 | W
        move.w  $e(a3),d6
        swap    d6
        move.w  d3,d6
        cmp.l   HKEY(a6),d6
        bne.s   .comp
        tst.w   S+sHK.l                 ; BUF still holds this text
        bne.w   .blit
.comp:  move.l  d6,HKEY(a6)
        move.w  d3,-(a7)                ; W
        move.w  4(a2),-(a7)             ; name seed
        lea     SB.l,a4
        moveq   #15,d0
        move.l  #$20202020,d1
.f:     move.l  d1,(a4)+
        dbra    d0,.f
        lea     SB.l,a4
        move.w  (a7)+,d0
        tst.w   (a7)
        bmi.s   .ptxt                   ; Build here: no village name
        jsr     $a3be.l                 ; the game's name generator: appends the village name at a4, returns d1 = length
        move.w  (a7)+,d3
        move.w  d3,d5
        lsr.w   #7,d5                   ; code
        and.w   #$7f,d3                 ; percent
        cmp.w   #2,d5
        bhs.s   .make
        lea     sIdle(pc),a0
        tst.w   d5
        bne.s   .one
        lea     sNone(pc),a0
.one:   bsr     cpy
        bra     .go
.make:  lea     sMake(pc),a0
        bsr     cpy
        move.w  d5,d0
        bsr     item
        lea     sPar(pc),a0
        bsr     cpy
        cmp.w   #10,d3
        blo.s   .u
        moveq   #0,d0
        move.w  d3,d0
        divu.w  #10,d0
        add.b   #$30,d0
        move.b  d0,(a4)+
        swap    d0
        move.w  d0,d3
.u:     add.b   #$30,d3
        move.b  d3,(a4)+
        lea     sPct(pc),a0
        bsr     cpy
        bra     .go
.ptxt:  move.w  (a7)+,d3
        lea     sInv(pc),a0
        bsr     cpy
        move.w  d3,d5
        lsr.w   #6,d5
        and.w   #$1f,d5                 ; item
        bne.s   .pa
        lea     sNoWs(pc),a0
        bsr     cpy
        bra     .go
.pa:    lsr.w   #8,d3
        lsr.w   #4,d3
        and.w   #7,d3                   ; reason 1..3
        move.w  d5,d0
        bsr     item
        lea     sPar(pc),a0
        bsr     cpy
        lea     rtab(pc),a0
        add.w   d3,d3
        move.w  -2(a0,d3.w),d0          ; reason n: word n-1 of rtab = offset of its string
        adda.w  d0,a0
        bsr     cpy
        lea     sPct2(pc),a0
        bsr     cpy
.go:    ; the generator / strings left their NULs inside SB: turn every 0 into a space
        lea     SB.l,a0
        moveq   #51,d0
.z:     tst.b   (a0)
        bne.s   .zn
        move.b  #$20,(a0)
.zn:    addq.l  #1,a0
        dbra    d0,.z
        jsr     $73406.l                ; pm_tooltip compose_sb: SB -> BUF
        clr.w   S+sKEY.l                ; BUF is no longer an icon text
        move.w  #1,S+sHK.l
.blit:  jsr     $7340c.l                ; BUF -> the back buffer
.out:   movem.l (a7)+,d0-d7/a0-a6
        jmp     $1853a.l

; a0 = string, a4 = destination: appends it (without its NUL)
cpy:    move.b  (a0)+,d0
        beq.s   .d
        move.b  d0,(a4)+
        bra.s   cpy
.d:     rts

; d0 = item code 2..$10: appends the game's own name ($9cd0 + $14 + [$9cd0 + code]: "Pike", "Plough", ...) lower-cased + "s" at a4
item:   lea     $9cd0.l,a0
        move.w  (a0,d0.w),d0
        lea     $14(a0,d0.w),a0
        move.b  (a0)+,d0
        or.b    #$20,d0
        move.b  d0,(a4)+
.n:     move.b  (a0)+,d0
        beq.s   .e
        move.b  d0,(a4)+
        bra.s   .n
.e:     move.b  #$73,(a4)+
        rts

; ---- predict: what the game's own build order ($505a, called from $51e0 when the Build icon's target is clicked) would make in this settlement ----------------------------
; READ-ONLY.  WW1's order is much simpler than Powermonger's invention order (no wood / iron / forest rules): no workshop (house kind 7 in the settlement's chain
; $2(a2) / $8(house)) -> the order does nothing; otherwise `$505a` sets the settlement's item word to the table word $510c + 2 * p, p = the selected captain's posture - 2 ($259e):
; p = 0 (3 swords, aggressive) $10 tank, 1 (2 swords) $e plane, 2 (1 sword, passive) $6 rifle.  The table is read from the game's own code.
; a2 = settlement record.  Out: d3 = W = $8000 | reason << 12 | item << 6   (reason 1..3 = p + 1 = 3 / 2 / 1 swords; item 0 = no workshop).  Clobbers d0, d4, d7, a0.
predict:move.w  2(a2),d0
        lea     $54234.l,a0
.ws:    beq.s   .nows
        cmpi.b  #7,7(a0,d0.w)
        beq.s   .hasws
        move.w  8(a0,d0.w),d0
        bra.s   .ws
.nows:  move.w  #$8000,d3               ; no workshop: item 0
        rts
.hasws: moveq   #1,d7                   ; p: the selected captain's posture word, as pm_tooltip reads it (neutral unless the word says otherwise)
        move.w  $5a834.l,d0
        lea     $5574e.l,a0
        move.w  $3c(a0,d0.w),d0
        cmp.w   #2,d0
        blo.s   .pp
        cmp.w   #4,d0
        bhi.s   .pp
        subq.w  #2,d0
        move.w  d0,d7
.pp:    lea     $510c.l,a0              ; the game's own table (inside its build order): $10, $e, $6
        move.w  d7,d3
        addq.w  #1,d3
        lsl.w   #8,d3
        lsl.w   #4,d3                   ; reason << 12
        or.w    #$8000,d3
        add.w   d7,d7
        move.w  (a0,d7.w),d4
        lsl.w   #6,d4
        or.w    d4,d3
        rts

sMake:  dc.b    ": making ",0
sPar:   dc.b    " (",0
sPct:   dc.b    "%)",0
sIdle:  dc.b    ": workshop idle",0
sNone:  dc.b    ": no workshop",0
sInv:   dc.b    "Build here: ",0
sNoWs:  dc.b    "no workshop here",0
sPct2:  dc.b    ")",0
sR1:    dc.b    "3 swords",0
sR2:    dc.b    "2 swords",0
sR3:    dc.b    "1 sword",0
        even
rtab:   dc.w    sR1-rtab,sR2-rtab,sR3-rtab
