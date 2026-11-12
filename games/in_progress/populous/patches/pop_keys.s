; name: pop_keys
; default: no
; prog: populous
; site: $bb7c
; orig: 303900021d8e
; data: $c8000 32
; note: Keyboard shortcuts for the icons (PopUI).  Take all four: pop_keys (this: pass hook + tables), pop_keys2 (key recorder in the ACIA
; note: interrupt), pop_keys3 (typed-text guard) and pop_keys4 (dialog guard).
; note: A key does what a left click (a right click for the magnet and building views) on the icon's cell does: this hook calls the game's own icon
; note: handler `$c420(left?)` with the click position set to the cell centre, exactly as the main loop's `jsr $c420` at $bbc4 does
; note: after a click ($bba6-$bbca), so mana checks, greyed icons, pointer-mode changes, orders (the 3 bytes at $21e4a + $2e * player) and the
; note: icon flash are the game's own.  Site $bb7c = `move.w $21d8e.l,d0`, the common point every pass reaches after the keypad scroll;
; note: the displaced instruction runs last.
; note: Why not just latch a click ($3d566 := 0, position) and let the main loop find it: the VBL routine $16c96 copies the live pointer
; note: into $3c556/$3c55a at every VBL while a latch is idle (0 skips, 1 and 2 copy), so a latched position is overwritten within a pass
; note: (observed: 2 of 21 scripted clicks acted at the pointer instead); and in raise / lower mode the land handler $11a24 acts on the
; note: position of a latched click.  Here both latches are 0 only for the length of the call ($16c96 then copies nothing), the click
; note: position is set first, and afterwards the latches are what a real click leaves ($c420's end $d09a makes a 0 latch 2; the idle one
; note: gets the main loop's `(word == 2) ? 2 : 1` rule from $bbcc-$bbf2).
; note: Blob map: hook $c7000-$c71ff, KT $c7200, ACT $c7240-$c72bd; pop_keys2 $c7300, pop_keys3 $c7380, pop_keys4 $c73c0; pop_tooltip $c7400-$c7fff.
; note: Keys are only counted while the map loop runs: every pass stamps LASTV (KD+0) with the VBL counter $16d2a; pop_keys2 drops a press
; note: that comes more than WIN VBLs after the last stamp; the first pass after a gap clears the queue and the Armageddon arm; and
; note: pop_keys3 empties the queue on every poll of the text input $200a6 that does not come from the main loop and pop_keys4 on every
; note: poll of the dialog button test $1a508, so typed text (name, save requester) and keys pressed in a dialog never act (work/notes/ui_impl.md, Powermonger phantom_click.md).
; note: At most one order at a time: a key waits while the local player's command byte ($21e4a + $2e * $3b03c) is still non-zero, i.e. until
; note: $1e750 has executed (and cleared) the order of the click before; a second click would overwrite it.  (Not a turn counter: a paused world
; note: does not advance $3c506, and Space has to un-pause.)
; note: A real click that is latched ($3d566 or $3c514 = 0) goes first; the key waits a pass.
; note: Armageddon needs the key twice within AWIN VBLs (any other key in between cancels); the first press only arms (pop_tooltip shows it).
; note: Data block KD ($c8000): +0 LASTV.l  +4 ARMT.l (arm stamp + 1, 0 = none)  +8 spare.w
; note:                       +10 QH.b  +11 QT.b  +12 Q[16] ring of action numbers (1-based row of ACT)
KD      equ     $c8000
WIN     equ     150
AWIN    equ     150
ACT     equ     $c7240
        org     $bb7c
        jsr     $c7000.l

        org     $c7000
hook:   movem.l d0-d7/a0-a6,-(sp)
        move.l  $16d2a.l,d0             ; the VBL counter
        move.l  d0,d1
        sub.l   KD.l,d1                 ; gap since the last pass
        move.l  d0,KD.l
        cmp.l   #WIN,d1
        bls.s   .run
        clr.w   KD+10.l                 ; first pass after a gap (game start, a dialog, a disk access): forget keys and the arm
        clr.l   KD+4.l
.run:   move.l  KD+4.l,d1
        beq.s   .q
        sub.l   d0,d1                   ; (stamp + 1) - now
        neg.l   d1
        addq.l  #1,d1                   ; now - stamp
        cmp.l   #AWIN,d1
        bls.s   .q
        clr.l   KD+4.l                  ; the arm ran out
.q:     move.b  KD+10.l,d1
        cmp.b   KD+11.l,d1
        beq.w   .out                    ; no key waiting
        tst.w   $3d566.l
        beq.w   .out                    ; a real left click is latched: it goes first
        tst.w   $3c514.l
        beq.w   .out                    ; ... or a right click
        move.w  $3b03c.l,d2             ; this player's order record: command byte at $21e4a + $2e * player
        mulu.w  #$2e,d2
        lea     $21e4a.l,a0
        tst.b   (a0,d2.w)
        bne.w   .out                    ; an earlier click's order has not been executed yet ($1e750 clears it): wait
        moveq   #0,d2
        move.b  d1,d2
        lea     KD+12.l,a0
        moveq   #0,d3
        move.b  (a0,d2.w),d3            ; action number (1-based)
        addq.b  #1,d1
        andi.b  #15,d1
        move.b  d1,KD+10.l              ; pop
        subq.w  #1,d3
        mulu.w  #6,d3
        lea     ACT.l,a0
        adda.w  d3,a0                   ; the row: kind.b pad.b x.w y.w
        moveq   #0,d4
        move.b  (a0),d4                 ; 0 left click, 1 right click, 2 Armageddon (left, second press)
        cmp.b   #2,d4
        bne.s   .go
        tst.l   KD+4.l
        bne.s   .twice
        move.l  $16d2a.l,d1
        addq.l  #1,d1
        move.l  d1,KD+4.l               ; first press: arm and wait
        bra.s   .out
.twice: moveq   #0,d4                   ; second press: the click on the Armageddon cell
.go:    clr.l   KD+4.l                  ; any other key cancels the arm
        move.w  $3d566.l,d5             ; the latches before: the idle one is renormalised below
        move.w  $3c514.l,d6
        clr.w   $3d566.l                ; both 0: the VBL's idle position copy is off for the length of the call
        clr.w   $3c514.l
        move.w  2(a0),$3c556.l          ; the click position: the cell centre
        move.w  4(a0),$3c55a.l
        moveq   #1,d0                   ; the argument of $c420: 1 left click, 0 right click
        tst.b   d4
        beq.s   .arg
        moveq   #0,d0
.arg:   move.w  d0,-(sp)
        jsr     $0c420.l
        addq.l  #2,sp
        tst.b   d4
        bne.s   .rclick
        moveq   #1,d0                   ; left click: the left latch is 2 ($d09a), the right one idles: 2 if it was 2, else 1
        cmp.w   #2,d6
        bne.s   .sr
        moveq   #2,d0
.sr:    move.w  d0,$3c514.l
        bra.s   .out
.rclick:moveq   #1,d0                   ; right click: the right latch is 2, the left one idles
        cmp.w   #2,d5
        bne.s   .sl
        moveq   #2,d0
.sl:    move.w  d0,$3d566.l
.out:   movem.l (sp)+,d0-d7/a0-a6
        move.w  $21d8e.l,d0             ; the displaced instruction
        rts

; key table: scan code, action number (1-based row of ACT); 0 ends.  Scan codes are physical key positions (a US / UK layout's
; letters; a German keyboard's Z and Y are swapped, a French one's A Q Z W M differ).
        org     $c7200
kt:     dc.b    $13,1                   ; R raise / lower
        dc.b    $10,2                   ; Q query
        dc.b    $19,3                   ; P papal magnet mode
        dc.b    $32,4                   ; M walkers go to the magnet
        dc.b    $1f,5                   ; S settle
        dc.b    $22,6                   ; G gather
        dc.b    $14,7                   ; T fight
        dc.b    $12,8                   ; E earthquake
        dc.b    $11,9                   ; W swamp
        dc.b    $25,10                  ; K knight
        dc.b    $2f,11                  ; V volcano
        dc.b    $21,12                  ; F flood
        dc.b    $1e,13                  ; A (twice) Armageddon
        dc.b    $26,14                  ; L view the leader
        dc.b    $2c,15                  ; Z view the magnet (right click on the leader cell)
        dc.b    $30,16                  ; B view a battle
        dc.b    $31,17                  ; N view a knight
        dc.b    $23,18                  ; H view an own building (right click on the knight cell)
        dc.b    $39,19                  ; Space pause
        dc.b    $16,20                  ; U music
        dc.b    $2d,21                  ; X effects
        dc.b    0,0

; action rows: kind (0 left click, 1 right click, 2 Armageddon), pad, click x, click y (the centre of the icon's diamond, ui.md)
        org     $c7240
act:    dc.b    0,0
        dc.w    96,184                  ; 1  raise / lower
        dc.b    0,0
        dc.w    112,176                 ; 2  query
        dc.b    0,0
        dc.w    80,192                  ; 3  papal magnet mode
        dc.b    0,0
        dc.w    16,176                  ; 4  go to the magnet
        dc.b    0,0
        dc.w    32,184                  ; 5  settle
        dc.b    0,0
        dc.w    48,192                  ; 6  gather
        dc.b    0,0
        dc.w    16,192                  ; 7  fight
        dc.b    0,0
        dc.w    48,144                  ; 8  earthquake
        dc.b    0,0
        dc.w    16,160                  ; 9  swamp
        dc.b    0,0
        dc.w    32,152                  ; 10 knight
        dc.b    0,0
        dc.w    16,144                  ; 11 volcano
        dc.b    0,0
        dc.w    16,128                  ; 12 flood
        dc.b    2,0
        dc.w    32,136                  ; 13 Armageddon
        dc.b    0,0
        dc.w    128,184                 ; 14 view the leader
        dc.b    1,0
        dc.w    128,184                 ; 15 view the magnet
        dc.b    0,0
        dc.w    112,192                 ; 16 view a battle
        dc.b    0,0
        dc.w    144,192                 ; 17 view a knight
        dc.b    1,0
        dc.w    144,192                 ; 18 view an own building
        dc.b    0,0
        dc.w    272,192                 ; 19 pause
        dc.b    0,0
        dc.w    256,184                 ; 20 music
        dc.b    0,0
        dc.w    240,192                 ; 21 effects
