; name: qol_keys
; default: yes
; stage: 2
; site: $130fc
; orig: 4eb900007202
; data: $cd460 200
; note: keyboard shortcuts for every command of the toolbar / icon grid (work/notes/qol.md has the key table).  A key press is turned into the
;       SAME click the mouse would have made: the click position words $2df8e/$2df90 are set to a point inside the icon's cell, the left
;       (or, for Shift + rotate / zoom, the right) button latch $2df96 (or $2df98 + $2df9e) is raised and $2df74 gets the click-lifetime
;       stamp, exactly as the VBL handler does for a mouse click ($12ec-$1300, $1348-$135c).  The game's own click code then runs
;       unchanged in the same pass: windows $7202, map icons $131e6, rotate / zoom rectangles $13250, the grid $13506 -> $135cc.
;       Site: `jsr $7202` ($130fc, the window / click dispatcher, right before the click dispatch $1310e), so the injected click is
;       handled in the SAME pass (a click latched by the VBL during the pass would be handled one pass later).  The stamp is read through
;       the operand of `move.l $2df70,d0` at $1373c ($1373e): tick_click3 makes it the pass counter, without it it is $2df70; either way the
;       latch lives exactly as long as a mouse click does ($1373c clears it when the counter moved).
;       Key presses are caught in the keyboard interrupt by qol_keys2 (site $199c, the make-code path of the game's ACIA handler $18be): it sets
;       PEND[scancode] = 1 (+ 2 if Shift is down) so that even a 50 ms tap cannot fall between two passes (a pass takes 125-260 ms).  This hook
;       consumes PEND for the keys of table KT.  The game itself only uses the cursor keys ($2de6c, polled per pass; Shift + Ins/ClrHome/KP keys are dead
;       code: Shift never lands in its table), so nothing else is taken over.  Keys are ignored (the press is swallowed) while typing ($d03e), while any window
;       is open ($7a36: the option / query windows cover the icons) and while paused ($57ff2); a real mouse click that is still latched
;       ($2df96 / $2df98) postpones a key by a pass.
;       Shift + [ / ] / = / - (and keypad + -) = the RIGHT button on the rotate / zoom rectangles (fine step, closest / farthest zoom);
;       Shift + [ or ] also repeats every pass while both keys stay down, like holding the right button ($2df9e + $2df98 raised each pass).
;       The pm_tooltip key labels are switched on by writing 1 to its data word $cdc0a every pass (harmless when pm_tooltip is absent).
;       Scan codes are physical key positions: [ and ] are the keys right of P (labelled so on UK / US layouts, other letters elsewhere on
;       national layouts); the cursor keys keep scrolling, F1-F4 are the map icons, the number row or the keypad 1-3 the posture.
;       Click points: pmtt_grid.icon() centre of every cell (tools/qol_points.py regenerates and checks the table KT).
D       equ     $cd460                  ; KS: 1 byte per KT entry (right-button repeat armed); +$3e REP.w; +$40 OWN9E.w; +$42 ANY.w; +$44 PEND: 128 bytes by scan code
KS      equ     D
OWN9E   equ     D+$40
ANY     equ     D+$42                   ; a press is (or may be) pending: written by qol_keys2 after PEND
REP     equ     D+$3e                   ; some KS byte is set (a repeat is running)
PEND    equ     D+$44                   ; written by qol_keys2 (interrupt), consumed here
S_KF    equ     $cdc0a                  ; pm_tooltip: key labels on
NK      equ     33

        org     $130fc
        jsr     $cf860.l

        org     $cf860
hook:   movem.l d0-d5/a0-a4,-(a7)
        move.w  #1,S_KF.l
        tst.w   OWN9E.l                 ; a right-button state this patch raised last pass: drop it before the dispatch
        beq.s   .o9
        clr.w   OWN9E.l
        clr.w   $2df9e.l
.o9:    moveq   #0,d4                   ; d4 <> 0: swallow the presses (typing, window open, paused)
        tst.b   $d03e.l
        bne.s   .inh
        tst.w   $7a36.l
        bne.s   .inh
        tst.w   $57ff2.l
        beq.s   .ok
.inh:   moveq   #1,d4
.ok:    move.w  ANY.l,d0                ; nothing pending and no repeat running: done (the scan below costs ~3.5k cycles)
        or.w    REP.l,d0
        beq     .done
        clr.w   ANY.l
        moveq   #0,d5                   ; d5 <> 0: a KS byte is set
        moveq   #0,d2                   ; d2 <> 0: no (more) click this pass
        move.w  $2df96.l,d0
        or.w    $2df98.l,d0
        beq.s   .free
        moveq   #1,d2                   ; a real click is still latched: keys wait
.free:  lea     KT(pc),a0
        lea     KS.l,a1
        lea     $2de6c.l,a2
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
        tst.w   $2df8a.l                ; Shift still down?
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
        jmp     $7202.l

; a0 -> KT entry {sc.b, flags.b (1 = Shift gives the right button, 2 = repeat while held), x.w, y.w}; d1 bit 1 = Shift.  Clobbers a4.
inject: move.w  2(a0),$2df8e.l
        move.w  4(a0),$2df90.l
        btst    #0,1(a0)
        beq.s   .left
        btst    #1,d1
        beq.s   .left
        move.w  #1,$2df98.l             ; right button: latch + held ($131f8 needs $2df9e for a right click)
        tst.w   $2df9e.l
        bne.s   .st                     ; the real right button is down: leave its state alone
        move.w  #1,$2df9e.l
        move.w  #1,OWN9E.l
        bra.s   .st
.left:  move.w  #1,$2df96.l
.st:    movea.l $1373e.l,a4             ; operand of `move.l $2df70,d0` at $1373c: $2df70, or the pass counter with tick_click3
        move.l  (a4),$2df74.l
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
