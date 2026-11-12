; name: jag_poll
; default: yes
; site: $262f6
; orig: 4cdf7fff4e73
; blobedit: $b433a 123875a9
; data: $b9ea0 80
; note: Atari Jaguar pad on the STE / Falcon enhanced joystick ports, part 1 of 3 (work/notes/jagpad.md; gamebench reports/jaguar_pad_study.md).
;       Apply with jag_dir and jag_btn.  The design is Hunter's jag_pad (games/in_progress/hunter/patches/jag_pad.s): ONE row group per VBL,
;       round robin, the select written at the end of one VBL and its data read at the start of the next (the settle time is a whole VBL: no
;       wait loop, which is also what makes the Falcon's slower bus safe), nothing decoded unless the group's data changed, and the original
;       bytes written back at every site when the probe says no pad ports (a machine without them runs the unpatched code at 0 cycles).
;       SITE: the end of the VBL handler, `movem.l (a7)+,d0-d7/a0-a6 / rte` ($262f6, 6 B) becomes `jmp jag_end.l`; the blob does its work with every
;       register free (the handler has saved them all and restores them here), then replays the movem and the rte.  The pad is read AFTER this
;       VBL's joystick re-read: the pad is seen one VBL later than the stick would be.
;       p5_ctl_vbl: its sampler's `move.b $75a9.w,d1` ($b433a, 4 B) becomes `bsr.w jag_rd` (blobedit: tools/mw2patch.py rewrites those 4 bytes of
;       p5_ctl_vbl's blob only when that patch is in the set), so p5_ctl_vbl.s itself is byte-identical with or without the jag patches.
;       JOYSTICK MODE ONLY ($eb76 <> 0; M / K mode cost jmp + tst.w + beq = 38 cycles and the pad is never touched).
;       Data ($b9ea0, 80 B): JAG+0 J_ST.b (0 not probed, 1 pad ports present, $ff none), +2 J_G.w (4 * group selected now), +4 J_P 4 longs (the masked raw
;       $ff9200/$ff9202 data last accepted for group 4,3,2,1; idle = $000fff00; bit 31 = "look again" mark), +20 J_OLD.l (S at the last change),
;       +24 J_VC.b (free-running poll counter), +25 J_ET.b (J_VC at the Option press), +26 J_ED.b (Option break deferred).
;       PADJ $b9ee1: pad directions in the IKBD joystick byte layout (bit0 up, 1 down, 2 left, 3 right), OR-ed into $75a9 by jag_dir and by jag_rd;
;       PADBTN $b9ee2: bit0 = pad B (fire), OR-ed into the select/fire event by jag_btn.
;       DETECTION (first VBL in any mode, fail closed, cached in J_ST; the same layers as Hunter's, plus the CPU class only to find the vector table;
;       a 68020+ is refused unless FALCON equ 1, see below):
;         1. guarded `tst.b $ff8901` (DMA sound: ST / Mega ST bus-error = no) and guarded `tst.b $ff8e01` (the SCU: answers on a Mega STE and a TT = no,
;            bus-errors on an STE and a Falcon).  The bus-error vector is VBR+8 (VBR read with `movec` on a 68020+, 0 on a 68000), the handler puts a7 back.
;         2. guarded word write $ffff to $ff9202 and word reads of $ff9202 / $ff9200 with every group deselected: high byte $ff and low nibble $f
;            (a Mega STE reads $xxx9, a TT $xx03, a stuck line 0).
;         On a no the probe writes the ORIGINAL bytes back to $262f6, $26b66, $26bea and (if it was redirected) $b433a: the unpatched code runs.
;         On a yes it re-points the jmp at $262f8 straight to jag_poll.  (A stale 68030 instruction cache can still run the old jumps; every blob
;         handles the no case, so that is harmless.)
;       SCAN: select words `$ffee/$ffdd/$ffbb/$ff77` = group 4/3/2/1 on port A AND port B in one write (never several groups of one port: a Team
;       Tap decodes that differently), word accesses only (a byte read of $ff9200 bus-errors on a real STE; one `move.l` reads both registers).
;       State S, one byte per group (g4 in the top byte; a group byte = rows A|B, bit 4 = button A|B, bit 5 = Pause on group 4):
;         bits 31-24 g4: 24 up 25 down 26 left 27 right, 28 A, 29 Pause    bits 23-16 g3: 16 `*` 17 `7` 18 `4` 19 `1`, 20 B
;         bits 15-8  g2: 8 `0` 9 `8` 10 `5` 11 `2`, 12 C                   bits 7-0   g1: 0 `#` 1 `9` 2 `6` 3 `3`, 4 Option
;       Every group is read every 4th VBL (80 ms at 50 Hz, 67 ms at 60 Hz); the D-pad and fire share that period (the game acts on input at 5 Hz).
;       Key map (a changed bit makes its key on press and breaks it on release; one make per press, no auto-repeat; the game's repeat state $770a/$770c
;       is set like a real key press): A `,` $33 ("<" nose down / dive), C `.` $34 (">" nose up / climb), Option Esc $01 (leave vehicle; its break is held
;       back until ESCMIN = 16 VBLs after the press, because the game polls the key table once per 5 Hz logic tick), Pause P $19, keypad 1..9 F1..F9
;       $3b..$43, 0 F10 $44, `*` keypad-minus $4a (previous weapon), `#` keypad-plus $4e (next weapon).  B = fire (select event, no key).
;       The key bookkeeping mirrors the IKBD ISR $269fe (make) and $26a20 + HAGA $3ea + $26a28 (break) and runs with interrupts masked (the ISR saves only d0-d3/a0).
JAG     equ     $b9ea0
J_ST    equ     0
J_G     equ     2
J_P     equ     4
J_OLD   equ     20
J_VC    equ     24
J_ET    equ     25
J_ED    equ     26
PADJ    equ     $b9ee1
PADBTN  equ     $b9ee2
FALCON  equ     0                       ; 1 = let a Falcon (68020+, DMA sound, no SCU) use the pad. 0 because MW2 does not run on a Hatari Falcon at all
                                        ; (HD: black screen; floppy: the intro picture is garbled and the game never starts), so that path could not be tested
ESCMIN  equ     16                      ; 320 ms at 50 Hz, 267 ms at 60 Hz: longer than a 5 Hz tick (200 ms) plus the scheduler's 1-VBL slack
        org     $262f6
        jmp     $b9500.l                ; replaces `movem.l (a7)+,d0-d7/a0-a6 / rte` (6 B); the operand at $262f8 is re-pointed after a good probe

        org     $b433a
        bsr.w   $b9e40                  ; p5_ctl_vbl: `move.b $75a9.w,d1` -> stick | pad

        org     $b9e40
jag_rd: move.b  $75a9.w,d1
        or.b    PADJ.l,d1
        rts

        org     $b9500
jag_end:                                ; first calls; after a good probe the site jumps to jag_poll directly
        move.b  JAG.l,d0
        bgt.s   jag_poll
        beq     jag_probe
jag_exit:
        movem.l (a7)+,d0-d7/a0-a6       ; the displaced instructions
        rte

jag_poll:
        tst.w   $eb76.l
        beq.s   jag_exit                ; not joystick mode
        lea     JAG.l,a3
        lea     $ffff9200.w,a1
        move.l  (a1),d1                 ; $ff9200 (buttons) and $ff9202 (directions / keypad) of the group selected since the last VBL
        addq.b  #1,J_VC(a3)
        move.w  J_G(a3),d0              ; 4 * index of that group
        move.w  d0,d7
        addq.w  #4,d7
        andi.w  #12,d7
        move.w  d7,J_G(a3)
        move.w  jag_sel+2(pc,d7.w),2(a1) ; select the next group; it settles for a whole VBL
        andi.l  #$000fff00,d1           ; the bits that carry pad data
        cmp.l   J_P(a3,d0.w),d1
        bne.s   jag_chg
        movem.l (a7)+,d0-d7/a0-a6
        rte
jag_sel: dc.l   $0000ffee,$0000ffdd,$0000ffbb,$0000ff77 ; group 4, 3, 2, 1 on port A and B

; ---- a group's data changed (or the Option deferral wants another look): rebuild S, PADJ / PADBTN, the key events (rare) -------------------
jag_chg:
        move.l  d1,J_P(a3,d0.w)         ; (also clears the mark of this group)
        lea     J_P(a3),a0
        moveq   #0,d3
        moveq   #3,d7
.rb:    move.l  (a0)+,d2
        not.l   d2
        andi.l  #$000fff00,d2           ; pressed: $ff9200 nibble in bits 16-19, $ff9202 bits 8-15
        move.w  d2,d4
        lsr.w   #4,d4
        or.w    d2,d4
        lsr.w   #8,d4
        andi.w  #$f,d4                  ; rows Up Down Left Right / keypad column, port A | port B
        swap    d2                      ; bits 0-3: Pause A, button A, Pause B, button B
        move.w  d2,d6
        lsr.w   #2,d6
        or.w    d2,d6                   ; bit 1 button A|B, bit 0 Pause A|B
        btst    #1,d6
        beq.s   .nb
        bset    #4,d4
.nb:    cmpi.w  #3,d7
        bne.s   .np                     ; Pause only exists in group 4 (the first)
        btst    #0,d6
        beq.s   .np
        bset    #5,d4
.np:    lsl.l   #8,d3
        or.b    d4,d3
        dbra    d7,.rb
        ; d3 = S
        move.l  d3,d0
        rol.l   #8,d0
        andi.b  #$f,d0
        move.b  d0,PADJ.l               ; up / down / left / right
        moveq   #0,d0
        btst    #20,d3
        beq.s   .nf
        moveq   #1,d0
.nf:    move.b  d0,PADBTN.l             ; B = fire
        ; Option (Esc) is polled from the key table ($7687, `tst.b` + `clr.b` at $1b43a) once per 5 Hz logic tick, not latched like the other keys
        ; ($7684 / $75ac), so a tap shorter than a tick would be lost: its break is held back until ESCMIN VBLs after the press.  While a break is
        ; deferred, group 1's stored data carries bit 31, so the next read of group 1 differs and comes here again.
        tst.b   J_ED(a3)
        beq.s   .e0
        move.b  J_VC(a3),d0
        sub.b   J_ET(a3),d0
        cmpi.b  #ESCMIN,d0
        bcc.s   .eexp
        bset    #4,d3                   ; still inside the minimum hold: Option stays pressed
        bset    #7,J_P+12(a3)
        bra.s   .e0
.eexp:  clr.b   J_ED(a3)
.e0:    move.l  J_OLD(a3),d6
        eor.l   d3,d6                   ; d6 = changed bits
        btst    #4,d6
        beq.s   .e2
        btst    #4,d3
        beq.s   .erel
        move.b  J_VC(a3),J_ET(a3)       ; fresh Option press
        clr.b   J_ED(a3)
        bra.s   .e2
.erel:  move.b  J_VC(a3),d0
        sub.b   J_ET(a3),d0
        cmpi.b  #ESCMIN,d0
        bcc.s   .e2
        bset    #4,d3                   ; released too early: defer the break
        move.b  #1,J_ED(a3)
        bset    #7,J_P+12(a3)
        bclr    #4,d6
.e2:    move.l  d3,J_OLD(a3)
        andi.l  #$300fffff,d6           ; keep A (28), Pause (29) and the keypad/C/Option bits 0-19; drop directions (24-27) and B (20)
        beq     .ret
        move.w  sr,d5
        ori.w   #$700,sr                ; the IKBD ISR (IPL 6) edits the same variables
        lea     keymap(pc),a2
        lea     $7686.w,a1
.ml:    move.b  (a2)+,d7                ; bit number, $ff = end
        bmi.s   .fin
        moveq   #0,d0
        move.b  (a2)+,d0                ; scancode
        btst    d7,d6
        beq.s   .ml
        btst    d7,d3
        bne.s   .make
        ; break (ISR $26a20, HAGA $3ea, $26a28)
        ori.w   #$80,d0
        move.w  d0,$7684.w
        andi.w  #$7f,d0
        clr.b   (a1,d0.w)
        cmp.w   $770a.w,d0
        bne.s   .nr
        clr.w   $770a.w
        move.w  d0,$7708.w
.nr:    tst.w   $75ac.w
        bne.s   .ml
        clr.w   $7684.w
        bra.s   .ml
.make:  move.w  d0,$7684.w              ; make (ISR $269fe)
        move.b  #$ff,(a1,d0.w)
        move.w  #$ffff,$75ac.w
        move.w  d0,$770a.w
        clr.w   $770c.w
        bra.s   .ml
.fin:   move.w  d5,sr
.ret:   movem.l (a7)+,d0-d7/a0-a6
        rte

keymap: dc.b    28,$33                  ; A       ,  (<)
        dc.b    12,$34                  ; C       .  (>)
        dc.b    4,$01                   ; Option  Esc
        dc.b    29,$19                  ; Pause   P
        dc.b    19,$3b                  ; 1       F1
        dc.b    11,$3c                  ; 2       F2
        dc.b    3,$3d                   ; 3       F3
        dc.b    18,$3e                  ; 4       F4
        dc.b    10,$3f                  ; 5       F5
        dc.b    2,$40                   ; 6       F6
        dc.b    17,$41                  ; 7       F7
        dc.b    9,$42                   ; 8       F8
        dc.b    1,$43                   ; 9       F9
        dc.b    8,$44                   ; 0       F10
        dc.b    16,$4a                  ; *       keypad -
        dc.b    0,$4e                   ; #       keypad +
        dc.b    -1,0

; ---- one-time detection (first VBL, any mode); every register is free -----------------------------------------------------------
jag_probe:
        lea     JAG.l,a3
        moveq   #-1,d4                  ; verdict: no
        movea.l a7,a2                   ; bus error guard: the handler puts a7 back here
        moveq   #0,d5                   ; VBR (a 68000 has none)
        moveq   #1,d0
        suba.l  a0,a0
        dc.w    $43f0,$0200             ; lea (0,a0,d0.w*2),a1: 1 on a 68000, 2 on a 68020+
        cmpa.w  #1,a1
        beq.s   .v0
        ifeq    FALCON
        bra     .pfin                   ; 68020+ (TT, Falcon) = no pad (FALCON equ 0): no hardware is touched
        endc
        dc.w    $4e7a,$5801             ; movec vbr,d5 (68020+ only)
.v0:    move.w  sr,d6
        ori.w   #$700,sr
        movea.l d5,a1
        addq.l  #8,a1                   ; a1 = the bus error vector
        move.l  (a1),d7
        lea     .berr(pc),a0
        move.l  a0,(a1)
        moveq   #0,d3                   ; stage 0: the DMA sound register must answer (ST / Mega ST fault)
        tst.b   $ffff8901.w
        moveq   #1,d3                   ; stage 1: the SCU must fault (a Mega STE and a TT have it)
        tst.b   $ffff8e01.w
        bra.s   .done                   ; it answered: no pad ports
.berr:  movea.l a2,a7                   ; (entered by a bus error)
        cmpi.b  #1,d3
        bne.s   .done                   ; fault in stage 0 or 2: no
        moveq   #2,d3                   ; stage 2: the pad registers must answer
        move.w  #$ffff,$ffff9202.w      ; deselect every group
        move.w  $ffff9202.w,d1
        move.w  $ffff9200.w,d2
        andi.w  #$ff00,d1               ; idle sanity: all direction / keypad lines high ...
        cmpi.w  #$ff00,d1
        bne.s   .done
        andi.w  #$000f,d2               ; ... and all button lines high
        cmpi.w  #$000f,d2
        bne.s   .done
        moveq   #1,d4
.done:  move.l  d7,(a1)
        move.w  d6,sr
.pfin:  move.b  d4,J_ST(a3)
        bgt.s   .yes
        move.l  #$4cdf7fff,$262f6.l     ; no pad ports here: put the original bytes back, the game runs untouched
        move.w  #$4e73,$262fa.l
        move.l  #$70007200,$26b66.l
        move.l  #$14280001,$26b6a.l
        move.l  #$14100242,$26bea.l
        move.w  #$0003,$26bee.l
        cmpi.w  #$6100,$b433a.l         ; p5_ctl_vbl's read, if it was redirected
        bne.s   .ex
        move.l  #$123875a9,$b433a.l
.ex:    bra     jag_exit
.yes:   lea     J_P(a3),a0
        move.l  #$000fff00,(a0)+        ; idle (all lines high) for every group
        move.l  #$000fff00,(a0)+
        move.l  #$000fff00,(a0)+
        move.l  #$000fff00,(a0)+
        clr.w   J_G(a3)
        move.l  #jag_poll,$262f8.l      ; the splice now jumps straight to the poll
        bra     jag_exit
