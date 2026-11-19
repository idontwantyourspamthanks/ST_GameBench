; name: qol_hover
; default: yes
; stage: 2
; site: $130b6
; orig: 4eb900017878
; data: $cd5e0 48
; note: village hover tooltip (work/notes/qol.md).  Resting the pointer on a house of a settlement in the 3D view shows, in the top-bar tooltip
;       area (rows 0-5, columns 7-19, the same place and font as pm_tooltip), "<village name>: making <item>s (NN%)" = the settlement's
;       current invention and how far its countdown has run.  REQUIRES pm_tooltip (uses its compose / blit exports, checks its liveness
;       word) AND qol_hover2 (the sprite hook at $12138 that finds the house under the pointer); without qol_hover2 nothing is ever shown.
;       (qol_hover2 alone is harmless: it only writes HIT.)
;       Settlement record (table $4e514, stride $20, offset = $e(house)):  +0 owner byte (0 = unused), +4 word name seed (the game's name
;       generator $a9ce, the same name the Query window prints), +$c word = item being made (2 pike, 4 sword, 6 bow, 8 plough, $a boat,
;       $c pot, $e catapult, $10 cannon; 0 = nothing yet; written by the invention order $5cde, which villagers also run on their own: $15890),
;       +$10 word = countdown to the next item (-1 per villager work step in $60dc; at 0 the item is added to the stock +$18+n and the
;       countdown restarts at  T = [$580a6 + owner * $20 + 8] + 4  (+ $2000 for catapult / cannon, $60e4-$610c; the order sets it the same way: $5f0c-$5f2e).
;       Progress = (T - countdown) * 100 / T, clamped to 0..99.  Names of the items: the game's own strings at $a242 + $14 + [$a242 + code]
;       (the Mine window prints them: $a63a), lower-cased and pluralised here.  Without an item: "<name>: workshop idle" when the chain of houses
;       ($2(settlement), next = $8(house)) has a workshop (kind byte $7 = 7), else "<name>: no workshop".
;       How the house is found: the game's own object pick.  The sprite routine $12138 (called once per drawn object: d0/d1 = sprite
;       top-left, a3 = the object record) compares the pointer $2df92/$2df94 with the sprite square ($120ea / $12116 size by zoom) - that
;       is what a Query click uses.  qol_hover2 (which carries HVHOOK, at $cd560) replaces its first instruction (`tst.w $57fd4`) with a call to HVHOOK, which
;       returns after doing that same instruction; unarmed it costs one `tst.w` (about 60 cycles per call, ~55 calls per pass).  Armed it runs the
;       same square test with the live pointer and remembers the LAST object that hits and lies in the house table $4f916..$51536
;       (the last one drawn is the front one).  Armed only for ONE pass after the pointer and the view (scroll, heading, tilt, zoom words)
;       have been still for 10 VBL (0.2 s): ARM = 1 is set by the pass hook, the next render's sprite hook raises it to 2 and fills HIT, the pass hook after that render resolves it.
;       Every pass while a village is hovered: the text is blitted into the back buffer after the render (pm_tooltip's BUF); it is
;       recomposed only when the key (settlement, item, percent) changes.  An icon tooltip of pm_tooltip (S+sID) or an open window
;       ($7a36) wins over the hover.
;       Site: `jsr $17878` ($130b6, the HUD call right after the landscape / object render $130aa): the pass hook; the sprite hook is qol_hover2.
;       State HS ($cd5e0): +0 ARM.w +2 HIT.l +6 LX.w +8 LY.w +$A REST.l (VBL stamp of the last change) +$e RES.w +$10 HKEY.l +$14 SIG (7 words).
HS      equ     $cd5e0
ARM     equ     0
HIT     equ     2
LX      equ     6
LY      equ     8
REST    equ     $a
RES     equ     $e
HKEY    equ     $10
SIG     equ     $14
S       equ     $cdc00                  ; pm_tooltip's state
sID     equ     4
sKEY    equ     6
sMAG    equ     $e
sHK     equ     $12
SB      equ     S+$290

        org     $130b6
        jsr     $cfa80.l                ; hpass (bra.w at the start of the blob)

        org     $cfa80
        bra.w   hpass                   ; $cfa80: the pass hook (jsr $cfa80 at the site)
        bra.w   predict                 ; $cfa84: the read-only chooser replay (tools/pmqol_inv.py calls it through test_qolinv)
; ---- hpass (the pass hook at $130b6) -------------------------------------------------------------------------------------------------
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
        move.w  $2df92.l,d0
        cmp.w   LX(a6),d0
        beq.s   .x
        moveq   #1,d2
        move.w  d0,LX(a6)
.x:     move.w  $2df94.l,d0
        cmp.w   LY(a6),d0
        beq.s   .y
        moveq   #1,d2
        move.w  d0,LY(a6)
.y:     lea     SIG(a6),a0
        sg      $4bb3a
        sg      $4bb3c
        sg      $ff9a
        sg      $ff96
        sg      $ff98
        sg      $ff9c
        sg      $57ffc
        tst.w   d2
        beq.s   .still
        move.l  $6f304.l,REST(a6)       ; moved: forget the pick, the clock restarts
        clr.w   RES(a6)
        clr.l   HIT(a6)
        clr.w   ARM(a6)
        bra     .out
.still: tst.w   S+sID.l                 ; an icon tooltip owns the bar / a window covers the view: no hover
        bne     .out
        tst.w   $7a36.l
        bne     .out
        tst.w   RES(a6)
        bne.s   .have
        move.l  $6f304.l,d3             ; not picked yet: arm for the next render once the pointer has rested 10 VBL
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
        cmp.w   #$1400,d0
        bhs     .out
        lea     $4e514.l,a2
        adda.w  d0,a2
        tst.b   (a2)
        beq     .out
        cmpi.w  #$e,$57fd4.l            ; the Invent icon is selected and waits for a target: say what Invent would make HERE
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
        moveq   #0,d1                   ; T = [$580a6 + owner * $20 + 8] + 4 (+ $2000 for catapult / cannon)
        move.b  (a2),d1
        lsl.w   #5,d1
        lea     $580a6.l,a0
        move.w  8(a0,d1.w),d1
        addq.w  #4,d1
        cmp.w   #$e,d5
        blo.s   .t
        add.w   #$2000,d1
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
        lea     $4f916.l,a0
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
        bmi.s   .ptxt                   ; Invent here: no village name
        jsr     $a9ce.l                 ; the game's name generator: appends the village name at a4, returns d1 = length
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
        and.w   #$1f,d5                 ; item A
        bne.s   .pa
        lea     sNoWs(pc),a0
        bsr     cpy
        bra     .go
.pa:    move.w  d3,d4
        and.w   #$1f,d4                 ; item B (0 = none)
        lsr.w   #8,d3
        lsr.w   #4,d3
        and.w   #7,d3                   ; reason
        move.w  d5,d0
        bsr     item
        tst.w   d4
        beq.s   .pr
        lea     sOr(pc),a0
        bsr     cpy
        move.w  d4,d0
        bsr     item
        lea     sBoth(pc),a0
        bsr     cpy
        bra     .go
.pr:    lea     sPar(pc),a0
        bsr     cpy
        lea     rtab(pc),a0
        add.w   d3,d3
        move.w  -2(a0,d3.w),d0          ; reason n (1..4): word n-1 of sR = offset of its string
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
        jsr     $cd006.l                ; pm_tooltip compose_sb: SB -> BUF
        clr.w   S+sKEY.l                ; BUF is no longer an icon text
        move.w  #1,S+sHK.l
.blit:  jsr     $cd00c.l                ; BUF -> the back buffer
.out:   movem.l (a7)+,d0-d7/a0-a6
        jmp     $17878.l

; a0 = string, a4 = destination: appends it (without its NUL)
cpy:    move.b  (a0)+,d0
        beq.s   .d
        move.b  d0,(a4)+
        bra.s   cpy
.d:     rts

; d0 = item code 2..$10: appends the game's own name ($a242 + $14 + [$a242 + code]: "Pike", "Plough", ...) lower-cased + "s" at a4
item:   lea     $a242.l,a0
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

; ---- predict: the decision of the game's invention order $5cde, replayed READ-ONLY (no random numbers, nothing written) -----------------------
; a2 = settlement record; the selected captain's posture is read here.  Out: d3 = W = $8000 | reason << 12 | item A << 6 | item B  (B = 0: only A);
; reason 1 wood nearby, 2 iron mine, 3 builds an iron mine, 4 neither (pots); item A = 0: no workshop.  Clobbers d0-d2, d4-d7, a0, a1, a4, a5.
;   $5cec-$5cfe : no workshop (house kind $7 in the settlement's chain $2(a2) / $8(house)) -> the order does nothing
;   $5d08-$5d30 : d1 = OR of the profession flags $7(person) over all residents (houses -> $a(house) -> $18(person)): 1 farmer, 2 merchant, 4 fisher
;   $5d34-$5d7e : d5 = distance (Chebyshev, cells) to the nearest forest of the list $57f68 (8 B entries, word 0 = cell y << 6 | x, 0 = unused)
;   $5d80-$5da4 : H = terrain byte $3f86c + [$4(a2)];  p = posture - 2 (0 aggressive, 1 neutral, 2 passive; $30fe)
;   wood or iron: a mine exists [$12(a2)] -> iron;  H < $10 -> wood;  forest farther than $14 -> iron;  otherwise bit 0 of $57fed (the pass counter's low
;   byte, no random draw) decides: so on high ground near a forest it ALTERNATES: both are shown.
;   iron ($5db0-$5dc4): cannon if p = 0 and a merchant lives there, else sword; with no mine one is built by a farmer ($5dd8-$5e06; needs a free
;   house slot $51536 < $1c20) else the order falls back to pots ($5ee4)
;   wood ($5e80-$5ec0): forest farther than $14 -> pots; p = 0: catapult with a merchant else bow; p = 1: pike; p = 2: boat with a fisher else plough
predict:moveq   #0,d4                   ; --- workshop?
        move.w  2(a2),d0
        lea     $4f916.l,a0
.ws:    beq.s   .nows
        cmpi.b  #7,7(a0,d0.w)
        beq.s   .hasws
        move.w  8(a0,d0.w),d0
        bra.s   .ws
.nows:  move.w  #$8000,d3               ; no workshop: item A = 0
        rts
.hasws: moveq   #1,d7                   ; p: the selected captain's posture word, as pm_tooltip reads it
        move.w  $57fd2.l,d0
        lea     $51538.l,a0
        move.w  $3c(a0,d0.w),d0
        cmp.w   #2,d0
        blo.s   .pp
        cmp.w   #4,d0
        bhi.s   .pp
        subq.w  #2,d0
        move.w  d0,d7
.pp:    moveq   #0,d1                   ; --- F = OR of the residents' profession flags
        move.w  2(a2),d0
.hs:    beq.s   .hd
        lea     $4f916.l,a4
        adda.w  d0,a4
        move.w  $a(a4),d2
.ps:    beq.s   .pd
        lea     $51b66.l,a5
        adda.w  d2,a5
        or.b    7(a5),d1
        move.w  $18(a5),d2
        bra.s   .ps
.pd:    move.w  8(a4),d0
        bra.s   .hs
.hd:    move.w  4(a2),d3                ; --- D = distance to the nearest forest
        move.w  d3,d4
        and.w   #$3f,d3
        lsr.w   #6,d4
        move.w  #$7fff,d5
        lea     $57f68.l,a0
        moveq   #9,d2
.fl:    move.w  (a0),d0
        beq.s   .fn
        move.w  d0,d6
        and.w   #$3f,d6
        lsr.w   #6,d0
        sub.w   d3,d6
        bpl.s   .a1
        neg.w   d6
.a1:    sub.w   d4,d0
        bpl.s   .a2
        neg.w   d0
.a2:    cmp.w   d0,d6
        bge.s   .a3
        move.w  d0,d6
.a3:    cmp.w   d6,d5
        ble.s   .fn
        move.w  d6,d5
.fn:    addq.l  #8,a0
        dbra    d2,.fl
        moveq   #0,d0                   ; --- H and the wood / iron choice (d3 bit 0 wood, bit 1 iron)
        move.w  4(a2),d0
        lea     $3f86c.l,a0
        move.b  (a0,d0.w),d6
        and.w   #$ff,d6
        tst.w   $12(a2)
        bne.s   .iron
        cmp.w   #$10,d6
        blo.s   .wood
        cmp.w   #$14,d5
        bgt.s   .iron
        moveq   #3,d3
        bra.s   .ev
.wood:  moveq   #1,d3
        bra.s   .ev
.iron:  moveq   #2,d3
.ev:    moveq   #0,d4                   ; wood result: item d4, reason d6
        moveq   #0,d6
        moveq   #0,d2                   ; iron result: item d2, reason d5 (after the wood part has used d5)
        btst    #0,d3
        beq.s   .nw
        cmp.w   #$14,d5
        bgt.s   .pots
        moveq   #1,d6
        tst.w   d7
        bne.s   .w1
        moveq   #6,d4
        btst    #1,d1
        beq.s   .nw
        moveq   #$e,d4
        bra.s   .nw
.w1:    cmp.w   #1,d7
        bne.s   .w2
        moveq   #2,d4
        bra.s   .nw
.w2:    moveq   #8,d4
        btst    #2,d1
        beq.s   .nw
        moveq   #$a,d4
        bra.s   .nw
.pots:  moveq   #$c,d4
        moveq   #4,d6
.nw:    btst    #1,d3
        beq.s   .ns
        moveq   #4,d2
        tst.w   d7
        bne.s   .s1
        btst    #1,d1
        beq.s   .s1
        moveq   #$10,d2
.s1:    moveq   #2,d5
        tst.w   $12(a2)
        bne.s   .ns
        moveq   #3,d5
        btst    #0,d1
        beq.s   .np
        cmpi.w  #$1c20,$51536.l
        blo.s   .ns
.np:    moveq   #$c,d2
        moveq   #4,d5
.ns:    tst.w   d4                      ; combine: only iron -> it becomes A
        bne.s   .ca
        move.w  d2,d4
        move.w  d5,d6
        moveq   #0,d2
.ca:    cmp.w   d4,d2                   ; both give the same item (pots): one
        bne.s   .cb
        moveq   #0,d2
.cb:    tst.w   d2
        beq.s   .cd
        moveq   #5,d6                   ; two answers: "A or B (wood or iron)" (reason 5, shown as the pair)
.cd:    move.w  d6,d3
        lsl.w   #8,d3
        lsl.w   #4,d3                   ; reason << 12
        or.w    #$8000,d3
        lsl.w   #6,d4
        or.w    d4,d3
        or.w    d2,d3
        rts

sMake:  dc.b    ": making ",0
sPar:   dc.b    " (",0
sPct:   dc.b    "%)",0
sIdle:  dc.b    ": workshop idle",0
sNone:  dc.b    ": no workshop",0
sInv:   dc.b    "Invent here: ",0
sNoWs:  dc.b    "no workshop here",0
sOr:    dc.b    " or ",0
sBoth:  dc.b    " (wood or iron)",0
sPct2:  dc.b    ")",0
sR1:    dc.b    "wood nearby",0
sR2:    dc.b    "iron mine",0
sR3:    dc.b    "builds an iron mine",0
sR4:    dc.b    "no wood or iron",0
        even
rtab:   dc.w    sR1-rtab,sR2-rtab,sR3-rtab,sR4-rtab
