; name: jag_pad
; default: yes
; requires: jag_stick
; site: $c616
; orig: 08ad0003008f
; data: $8d9e0 32
; note: Atari Jaguar pad on the STE / Falcon enhanced joystick ports (reports/jaguar_pad_study.md, work/notes/jagpad.md).  Port A and port B
; note: are both read (one write+read serves both) and OR-ed, so a pad in either port works, together with the normal joystick.
; note: Needs jag_stick (the stick merge at $c64c); the two are one feature split over two splice sites.
; note: Splice: the VBL handler's `bclr.b #3,$8f(a5)` ($c616, end of the handler, after the sound tick) becomes `jmp JAG_VBL.l`; after the one-time probe
; note: the probe re-points it (the long at $c618) to jag_poll.  The blob replays the bclr, does its work and `jmp $c61c.l` back (a jmp pair costs 24 cycles, jsr/rts 36).  It runs outside the 3D-loop gate of hn_hz, so Pause still
; note: works while the game is paused.
; note: Cost design (Hunter's standing frames sit on a VBL boundary; every cycle can push a frame from 10 to 11 VBL): ONE ROW GROUP PER VBL, round robin
; note:   (group 4, 3, 2, 1: every group is read every fourth VBL, 80 ms at 50 Hz).  The select of a group is written at the end of one VBL and its data
; note:   read at the start of the next: the settle time is a whole VBL, so there is no wait loop and no pipelining; the group stays driven between polls.
; note:   Nothing is decoded unless the group's data changed since its last read (one compare), so an idle or held pad costs 180 cycles per VBL in this blob (measured), 212 with the two splices net of the code they replace.
; note: Detection (first VBL, lazily; every layer fails closed, a failed layer disables the pad for the whole session):
; note:   1. machine class, cookie-free: FLAGS bit0 (core.s probe: STE DMA sound answers, so not a plain ST/Mega ST) and a bus error on the
; note:      SCU `$ff8e01.b` (the Mega STE and the TT have the SCU; the STE and the Falcon have not).  On an ST/Mega ST/Mega STE/TT no pad
; note:      register is ever touched.  FLAGS bit3 (Falcon) is not used.
; note:   2. bus-error guarded `move.w #$ffff,$ff9202 / move.w $ff9202 / move.w $ff9200` (the $8 vector is swapped, a7 restored);
; note:   3. idle sanity with every group deselected: $ff9202 high byte = $ff and $ff9200 low nibble = $f (a Mega STE reads $fff9 there,
; note:      a TT $3f03, a stuck line 0).
; note:   Result in JAG_ST: 0 not probed, 1 pad ports present and idle, $ff no.  On a no the probe writes the ORIGINAL bytes back to both splice sites
; note:   ($c616, $c64c): the machine then runs exactly the unpatched code, at no cost.  A pad button held while the probe runs does not matter:
; note:   with every group deselected a button reads high.
; note: Reading: select $ffee/$ffdd/$ffbb/$ff77 = group 4/3/2/1 on port A and B together (one read serves both pads; never several groups at once, so
; note:   a Team Tap stays transparent), word accesses only (a byte read of $ff9200 bus-errors on a real STE).  Per group the pressed bits of
; note:   $ff9202 bits 8-15 and $ff9200 bits 0-3 are kept as one word; S1 (long, 1 = pressed, port A | port B): byte 3 = group 4 (bits 24-27 Up Down Left
; note:   Right), byte 2 = group 3 (16-19 `*` 7 4 1), byte 1 = group 2 (8-11 `0` 8 5 2), byte 0 = group 1 (0-3 `#` 9 6 3); S2 (word): group 4 bits 13 A,
; note:   12 Pause; group 3 bit 9 B; group 2 bit 5 C; group 1 bit 1 Option.
; note: Directions and fire: JAG_DIR (byte, the format of $d0: S=1 N=2 E=4 W=8 fire=$10) is OR-ed into $d0 by jag_stick; A or B = fire.
; note:   Without a pad (or nothing pressed) JAG_DIR is 0: the OR changes nothing.
; note: Buttons that stand for keys: on every change of such a bit the game's own key decoder is called ($b048, the entry after the IKBD packet
; note:   state test; d0 = scancode, bit 7 = break): make on press, break on release, ONE make per press (no repeat; a held key stays in the
; note:   game's key table, which is what its cursor Up/Down zoom reads).  Makes are injected only while the 3D loop runs or the game is paused
; note:   ($93 bit 7 or bit 5), never in menus or the name entry; breaks always, so no key can stay stuck.  A press must last 80 ms to be sure.
; note: BUTTON MAP (Hunter):
; note:   D-pad          stick (OR-ed with the real joystick)      A or B   fire
; note:   C              Return $1c   next weapon                  Option   Space $39   leave vehicle
; note:   Pause          P $19        pause                        `*`      Esc $01     game options
; note:   1  R $13 radar        2  Help $62 overlay map ("?")      3  L $26 log book
; note:   4  A $1e drone        5  F $21 flare                     6  C $2e clock
; note:   7  cursor Up $48 zoom (held)                              9  cursor Down $50 zoom (held)
; note:   `#`, 0, 8: unassigned.  The mouse-driven screens (drone map, game options, menus) still need the mouse.
JAG      equ    $8d9e0                  ; state block, a3 points here
J_ST     equ    0                       ; b: 0 = not probed, 1 = pad ports present, $ff = no
J_DIR    equ    4                       ; b: stick bits for $d0 (jag_stick), 0 = nothing
J_G      equ    8                       ; w: 4 * index of the group selected now (0 = group 4 ... 12 = group 1)
J_P      equ    10                      ; 4 longs: the masked raw data last read for each group (idle = $000fff00)
J_OLD1   equ    26                      ; l: S1 at the last change
J_OLD2   equ    30                      ; w: S2 at the last change
FLAGS    equ    $8bff0                  ; core.s: bit0 STE-class DMA sound answers
JAG_VBL  equ    $8d600                  ; the blob below (the site is assembled apart from it: it needs the absolute address)

        org     $c616
        jmp     JAG_VBL.l               ; replaces `bclr.b #3,$8f(a5)`

        org     $8d600
jag_vbl:                                ; first call(s): the site still points here; after a successful probe it points to jag_poll
        move.b  JAG.l,d0
        bgt.s   jag_poll
        bclr    #3,$8f(a5)              ; the displaced instruction
        lea     JAG.l,a3
        tst.b   d0
        beq.w   jag_probe
        jmp     $c61c.l                 ; (unreachable once the probe unpatched the site)
jag_poll:
        bclr    #3,$8f(a5)              ; the displaced instruction
        lea     JAG.l,a3
        lea     $ffff9200.w,a1
        move.l  (a1),d1                 ; $ff9200 (button lines) and $ff9202 (directions / keypad) of the group selected since the last VBL
        move.w  J_G(a3),d0
        move.w  d0,d7
        addq.w  #4,d7
        andi.w  #12,d7
        move.w  d7,J_G(a3)
        move.w  jag_sel+2(pc,d7.w),2(a1) ; select the next group; it settles for a whole VBL
        andi.l  #$000fff00,d1           ; the bits that carry pad data
        cmp.l   J_P(a3,d0.w),d1
        bne.w   jag_chg
        jmp     $c61c.l
jag_sel: dc.l   $0000ffee,$0000ffdd,$0000ffbb,$0000ff77 ; group 4, 3, 2, 1 on port A and B

; ---- one-time detection; d0-d4/a0-a2 scratch (the VBL handler saved d0-d7/a0-a4) -------------------------------------------
jag_probe:
        moveq   #-1,d4                  ; verdict: no
        move.l  FLAGS.l,d0
        movea.l a7,a2                   ; bus error guard (core.s probe pattern): the handler puts a7 back here
        movea.l $8.w,a1
        btst    #0,d0                   ; no STE DMA sound answer: plain ST / Mega ST
        beq.s   .done
        lea     .berr(pc),a0
        move.l  a0,$8.w
        moveq   #0,d3                   ; stage 0: the SCU read must fault
        tst.b   $ffff8e01.w             ; Mega STE and TT answer here; an STE and a Falcon (no SCU) bus-error
        bra.s   .done                   ; it answered: no pad ports
.berr:  movea.l a2,a7                   ; (entered by a bus error)
        tst.w   d3
        bne.s   .done                   ; fault in stage 1: the pad registers are not there
        moveq   #1,d3                   ; stage 1: the pad registers must answer
        move.w  #$ffff,$ffff9202.w      ; deselect every group
        move.w  $ffff9202.w,d1
        move.w  $ffff9200.w,d2
        andi.w  #$ff00,d1               ; idle sanity: all direction/keypad lines high ...
        cmpi.w  #$ff00,d1
        bne.s   .done
        andi.w  #$000f,d2               ; ... and all button lines high
        cmpi.w  #$000f,d2
        bne.s   .done
        moveq   #1,d4
        move.w  #$ffee,$ffff9202.w      ; group 4: read at the next VBL (a3 = JAG, J_G = 0)
        lea     J_P(a3),a0
        move.l  #$000fff00,(a0)+        ; idle (all lines high) for every group
        move.l  #$000fff00,(a0)+
        move.l  #$000fff00,(a0)+
        move.l  #$000fff00,(a0)+
        move.l  #jag_poll,$c618.l       ; the splice now jumps straight to the poll (a stale instruction cache still reaches it through jag_vbl)
.done:  move.l  a1,$8.w
        move.b  d4,J_ST(a3)
        bgt.s   .out
        move.l  #$08ad0003,$c616.l      ; no pad ports here: put the original bytes back at both sites, the game runs untouched
        move.w  #$008f,$c61a.l
        move.l  #$102d00d1,$c64c.l
        move.l  #$1b4000d0,$c650.l
.out:   jmp     $c61c.l

; ---- a group's data changed: rebuild S1/S2, the stick byte and the key events (rare) ---------------------------------------------
jag_chg:
        move.l  d1,J_P(a3,d0.w)
        lea     J_P(a3),a0
        moveq   #0,d3
        moveq   #0,d5
        moveq   #3,d7
.rb:    move.l  (a0)+,d2
        not.l   d2
        andi.l  #$000fff00,d2           ; pressed: $ff9200 nibble in bits 16-19, $ff9202 bits 8-15
        move.w  d2,d4                   ; d4 = bits 8-15: port A nibble 8-11, port B nibble 12-15
        swap    d2                      ; d2 = bits 0-3: Pause A, button A, Pause B, button B
        move.w  d2,d6
        lsr.w   #2,d6
        or.w    d2,d6
        andi.w  #3,d6                   ; bit1 button A|B, bit0 Pause A|B
        move.w  d4,d2
        lsr.w   #4,d2
        or.w    d4,d2
        lsr.w   #8,d2
        andi.w  #$f,d2                  ; Up Down Left Right / keypad column, port A | port B
        lsl.l   #8,d3
        or.b    d2,d3
        lsl.w   #4,d5
        or.w    d6,d5
        dbra    d7,.rb
        andi.w  #$3222,d5               ; S2: A, Pause (group 4), B, C, Option
        ; stick: Up Down Left Right -> the $d0 format, A or B = fire
        move.l  d3,d0
        rol.l   #8,d0
        andi.w  #$f,d0
        lea     jag_dirs(pc),a0
        move.b  (a0,d0.w),d2
        move.w  d5,d0
        andi.w  #$2200,d0               ; A (bit 13) or B (bit 9)
        beq.s   .nf
        ori.b   #$10,d2
.nf:    move.b  d2,J_DIR(a3)
        ; keys: bits that changed since the last change
        move.l  J_OLD1(a3),d6
        move.l  d3,J_OLD1(a3)
        eor.l   d3,d6
        andi.l  #$000f0c0e,d6           ; only the bits that have a key
        move.w  J_OLD2(a3),d4
        move.w  d5,J_OLD2(a3)
        eor.w   d5,d4
        andi.w  #$1022,d4
        move.l  d6,d0
        or.w    d4,d0
        tst.l   d0
        beq.s   .ret
        lea     jag_map(pc),a2
.nx:    move.b  (a2)+,d7                ; bit number (32+ = S2), $ff ends the table
        bmi.s   .ret
        moveq   #0,d0
        move.b  (a2)+,d0                ; scancode
        cmpi.b  #32,d7
        bcc.s   .two
        btst    d7,d6
        beq.s   .nx
        btst    d7,d3
        bra.s   .dec
.two:   btst    d7,d4
        beq.s   .nx
        btst    d7,d5
.dec:   beq.s   .brk                    ; now released: break
        move.b  $93(a5),d1              ; make: only while the 3D loop runs (bit 7) or the game is paused (bit 5)
        andi.b  #$a0,d1
        beq.s   .nx
        bra.s   .send
.brk:   ori.b   #$80,d0
.send:  movem.l d3-d6/a2-a3,-(sp)
        jsr     $b048.l                 ; the game's key make/break decoder (entry after the IKBD packet-state test)
        movem.l (sp)+,d3-d6/a2-a3
        bra.s   .nx
.ret:   jmp     $c61c.l

jag_dirs:                               ; Up=1 Down=2 Left=4 Right=8 -> $d0: N=2 S=1 W=8 E=4
        dc.b    $00,$02,$01,$03,$08,$0a,$09,$0b,$04,$06,$05,$07,$0c,$0e,$0d,$0f
jag_map:                                ; S1 bit (0-31) or 32 + S2 bit, ST scancode
        dc.b    32+12,$19               ; Pause  -> P
        dc.b    32+5,$1c                ; C      -> Return
        dc.b    32+1,$39                ; Option -> Space
        dc.b    16,$01                  ; *      -> Esc
        dc.b    19,$13                  ; 1      -> R
        dc.b    11,$62                  ; 2      -> Help
        dc.b    3,$26                   ; 3      -> L
        dc.b    18,$1e                  ; 4      -> A
        dc.b    10,$21                  ; 5      -> F
        dc.b    2,$2e                   ; 6      -> C
        dc.b    17,$48                  ; 7      -> cursor Up
        dc.b    1,$50                   ; 9      -> cursor Down
        dc.b    $ff,0
