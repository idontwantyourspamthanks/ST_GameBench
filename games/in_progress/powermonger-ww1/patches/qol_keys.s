; name: qol_keys
; default: yes
; site: $13e70
; orig: 4eb900006c16
; data: $73000 204
; note: keyboard shortcuts for every command of the icon grid (master's qol_keys, games/done/powermonger/work/notes/qol.md has the key table; WW1's grid is
;       pixel-identical to master's: tools/wwgrid.py reads WW1's own tables $13bde / $13c58 / $1a89a / rects $13fc4 and every one of master's click points resolves to
;       the same icon id).  A key press is turned into the SAME click the mouse would have made: the click position words $2edae/$2edb0 are set to a point inside
;       the icon's cell, the left (or, for Shift + rotate / zoom, the right) button latch $2edb6 (or $2edb8 + $2edbe) is raised and $2ed94 gets the click-lifetime
;       stamp, exactly as the VBL handler does for a mouse click ($7e0-$7f6, $836-$852).  The game's own click code then runs unchanged in the same pass: windows
;       $6c16, map icons $13f5a, rotate / zoom rectangles $13fc4, the grid $1427a -> $14340.
;       Site: `jsr $6c16` ($13e70, the window / click dispatcher, right before the click dispatch), so the injected click is handled in the SAME pass.  The stamp is
;       read through the operand of `move.l $2ed90,d0` at $144b2 ($144b4): tick_click3 makes it the pass counter, without it it is $2ed90; either way the latch lives
;       exactly as long as a mouse click does.
;       Key presses are caught in the keyboard interrupt by qol_keys2 (site $f30): it sets PEND[scancode] = 1 (+ 2 if Shift is down) so that even a 50 ms tap cannot fall
;       between two passes.  This hook consumes PEND for the keys of table KT.  The game itself only uses the cursor keys (table $2ec8c, polled per pass).  Keys are
;       ignored (the press is swallowed) while typing ($d424), while any window is open ($74c0) and while paused ($5a856); a real mouse click that is still latched
;       ($2edb6 / $2edb8) postpones a key by a pass.
;       Shift + [ / ] / = / - (and keypad + -) = the RIGHT button on the rotate / zoom rectangles; Shift + [ or ] also repeats every pass while both keys stay down.
;       Keys that are not typed into the map view are not shortcuts (master work/notes/phantom_click.md): the pass hook stamps the VBL counter ($71b7c) into LASTV every
;       pass; qol_keys2 (the interrupt) only records a press while LASTV is at most WIN VBLs old, and the first pass after a longer gap (game start: the letters of the
;       name typed at the name prompt, a key pressed in a menu or during a disk access) flushes every key state before anything is replayed as an icon click.
;       Scan codes are physical key positions: [ and ] are the keys right of P (UK / US labels); the cursor keys keep scrolling, F1-F4 are the map icons, the number
;       row or the keypad 1-3 the posture.  The tooltip's key labels (pm_tooltip) are switched on by this hook writing 1 to KF every pass (the word lives in this patch's
;       own data block: without qol_keys it stays 0 and the tooltips show no labels).
D       equ     $73000                  ; KS: 1 byte per KT entry (right-button repeat armed); +$3e REP.w; +$40 OWN9E.w; +$42 ANY.w; +$44 PEND: 128 bytes by scan code; +$c4 LASTV.l
KS      equ     D
OWN9E   equ     D+$40
ANY     equ     D+$42                   ; a press is (or may be) pending: written by qol_keys2 after PEND
REP     equ     D+$3e                   ; some KS byte is set (a repeat is running)
PEND    equ     D+$44                   ; written by qol_keys2 (interrupt), consumed here
LASTV   equ     D+$c4                   ; VBL count ($71b7c) of the previous pass hook; read by qol_keys2
KF      equ     D+$c8                   ; .w, 1 once this hook has run: pm_tooltip shows the key labels (pm_tooltip's KF equ = $730c8)
WIN     equ     150                     ; a press counts while the loop's last pass is at most this many VBLs old (3 s at 50 Hz; a pass is 13-26 VBLs)
NK      equ     33

        org     $13e70
        jsr     $72c00.l

        org     $72c00
hook:   movem.l d0-d5/a0-a4,-(a7)
        move.w  #1,KF.l
        tst.w   OWN9E.l                 ; a right-button state this patch raised last pass: drop it before the dispatch
        beq.s   .o9
        clr.w   OWN9E.l
        clr.w   $2edbe.l
.o9:    move.l  $71b7c.l,d0             ; the stamp: this pass, and the gap since the previous one
        move.l  d0,d1
        sub.l   LASTV.l,d1
        move.l  d0,LASTV.l
        cmp.l   #WIN,d1
        bls.s   .run
        lea     KS.l,a0                 ; first pass after a gap (game start / a menu / a disk access): drop every key state recorded meanwhile
        moveq   #(LASTV-D)/4-1,d0
.fl:    clr.l   (a0)+
        dbra    d0,.fl
.run:   moveq   #0,d4                   ; d4 <> 0: swallow the presses (typing, window open, paused)
        tst.b   $d424.l
        bne.s   .inh
        tst.w   $74c0.l
        bne.s   .inh
        tst.w   $5a856.l
        beq.s   .ok
.inh:   moveq   #1,d4
.ok:    move.w  ANY.l,d0                ; nothing pending and no repeat running: done (the scan below costs ~3.5k cycles)
        or.w    REP.l,d0
        beq     .done
        clr.w   ANY.l
        moveq   #0,d5                   ; d5 <> 0: a KS byte is set
        moveq   #0,d2                   ; d2 <> 0: no (more) click this pass
        move.w  $2edb6.l,d0
        or.w    $2edb8.l,d0
        beq.s   .free
        moveq   #1,d2                   ; a real click is still latched: keys wait
.free:  lea     KT(pc),a0
        lea     KS.l,a1
        lea     $2ec8c.l,a2
        lea     PEND.l,a3
        moveq   #NK-1,d3
.k:     moveq   #0,d0
        move.b  (a0),d0
        move.b  (a3,d0.w),d1            ; pending press (bit 1 = Shift was down)
        beq.s   .nop
        tst.w   d4
        bne.s   .swal
        tst.w   d2
        bne.s   .bz                     ; busy: the press stays pending
        clr.b   (a3,d0.w)
        bsr.s   inject
        moveq   #1,d2
        clr.b   (a1)
        btst    #1,1(a0)                ; repeat flag (Shift + [ ])
        beq.s   .nx
        btst    #1,d1
        beq.s   .nx
        st      (a1)                    ; right button "held" while the key and Shift stay down
        moveq   #1,d5
        bra.s   .nx
.bz:    move.w  #1,ANY.l
        bra.s   .nx
.swal:  clr.b   (a3,d0.w)
        bra.s   .nx
.nop:   tst.b   (a1)
        beq.s   .nx
        moveq   #1,d5
        tst.b   (a2,d0.w)               ; key still down?
        beq.s   .rel
        tst.w   $2edaa.l                ; Shift still down?
        beq.s   .rel
        tst.w   d4
        bne.s   .nx
        tst.w   d2
        bne.s   .nx
        moveq   #2,d1
        bsr.s   inject
        moveq   #1,d2
        bra.s   .nx
.rel:   clr.b   (a1)
.nx:    addq.l  #6,a0
        addq.l  #1,a1
        dbra    d3,.k
        move.w  d5,REP.l
.done:  movem.l (a7)+,d0-d5/a0-a4
        jmp     $6c16.l

; a0 -> KT entry {sc.b, flags.b (1 = Shift gives the right button, 2 = repeat while held), x.w, y.w}; d1 bit 1 = Shift.  Clobbers a4.
inject: move.w  2(a0),$2edae.l
        move.w  4(a0),$2edb0.l
        btst    #0,1(a0)
        beq.s   .left
        btst    #1,d1
        beq.s   .left
        move.w  #1,$2edb8.l             ; right button: latch + held ($131f8 needs $2edbe for a right click)
        tst.w   $2edbe.l
        bne.s   .st                     ; the real right button is down: leave its state alone
        move.w  #1,$2edbe.l
        move.w  #1,OWN9E.l
        bra.s   .st
.left:  move.w  #1,$2edb6.l
.st:    movea.l $144b4.l,a4             ; operand of `move.l $2ed90,d0` at $144b2: $2ed90, or the pass counter with tick_click3
        move.l  (a4),$2ed94.l
        rts

key     macro                           ; scancode, flags, x, y
        dc.b    \1,\2
        dc.w    \3,\4
        endm
KT:     key     $02,0,92,135            ; 1 = passive (1 sword), icon 21
        key     $03,0,95,145            ; 2 = neutral, icon 20
        key     $04,0,97,157            ; 3 = aggressive, icon 19
        key     $6d,0,92,135            ; keypad 1, icon 21
        key     $6e,0,95,145            ; keypad 2, icon 20
        key     $6f,0,97,157            ; keypad 3, icon 19
        key     $1e,0,244,191           ; A attack, icon 6
        key     $20,0,142,193           ; D drop food, 9
        key     $12,0,298,157           ; E equip, 8
        key     $21,0,202,181           ; F get food, 3
        key     $22,0,300,183           ; G send captain, 1
        key     $23,0,100,170           ; H go home, 5
        key     $17,0,274,188           ; I invent, 7
        key     $26,0,73,161            ; L alliance, 15
        key     $32,0,275,163           ; M get men, 4
        key     $31,0,173,188           ; N drop items, 12
        key     $18,0,72,139            ; O option, 23
        key     $10,0,76,191            ; Q query, 22
        key     $13,0,252,168           ; R derank, 10
        key     $1f,0,228,175           ; S supply food, 13
        key     $14,0,74,176            ; T trade, 14
        key     $2d,0,103,187           ; X transfer men, 2
        key     $15,0,72,149            ; Y spy, 16
        key     $3b,0,8,2               ; F1..F4 map icons 24..27
        key     $3c,0,24,2
        key     $3d,0,40,2
        key     $3e,0,56,2
        key     $1a,3,28,158            ; [  rotate left  (rect 0 of $13250); Shift = right button, repeats
        key     $1b,3,37,165            ; ]  rotate right (rect 1)
        key     $0d,1,53,166            ; =  zoom in  (rect 2); Shift = right button (closest)
        key     $4e,1,53,166            ; keypad +
        key     $0c,1,53,185            ; -  zoom out (rect 3); Shift = farthest
        key     $4a,1,53,185            ; keypad -
KTE:
        ifne    (KTE-KT)/6-NK
        fail    "NK must be the number of KT entries"
        endc
