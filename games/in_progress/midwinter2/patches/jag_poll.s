; name: jag_poll
; default: no
; site: $262c2
; orig: 4eb900027228
; data: $b9ee0 16
; note: Atari Jaguar pad on the STE enhanced joystick ports, part 1 of 3 (work/notes/jagpad.md; gamebench reports/jaguar_pad_study.md).
;       Apply with jag_dir and jag_btn; p5_ctl_vbl reads the same PADJ byte (zero without this patch).
;       The VBL handler's `jsr $27228` (6 B) becomes `jsr jag_poll`; the blob polls the pad, then tail-jumps to $27228, so it runs once per VBL,
;       with every register saved by the handler, before p5_ctl_vbl's `jsr $26b58` / sampler and before the joystick re-read.
;       JOYSTICK MODE ONLY ($eb76 <> 0; mouse and keyboard modes cost two compares and are untouched).
;       Data ($b9ee0, 16 B): FLAG.b +0, PADJ.b +1, PADBTN.b +2, ESCCNT.b +3, PADOLD.l +4, GB.l +8, ROT.b +12
;         FLAG   0 = not probed yet, 1 = pad ports present and answering, 2 = no pad ports (permanent)
;         PADJ   pad directions as the IKBD joystick byte: bit0 up, 1 down, 2 left, 3 right (OR-ed into $75a9 by jag_dir and into p5_ctl_vbl's counters)
;         PADBTN bit0 = pad B (fire): OR-ed into the IKBD mouse-header buttons that become the select/fire event $6872 (jag_btn)
;         GB     the pad state S, one byte per scan group (below); PADOLD the previous S (after the Esc hold): every changed bit that stands for a key
;                makes / breaks that key in the game's own key bookkeeping.
;       DETECTION (first poll in J mode, fail closed, cached in FLAG; nothing is read at $ff9200/$ff9202 unless all three layers pass):
;         1. CPU class: 68000 only (brief-extension-word trick as in cpulib.s / p4_blit_sky). 68020+ (TT, Falcon) = no pad, no hardware access.
;         2. Guarded probes (vector $8 swapped, handler discards the frame, interrupts masked): $ff8901.b (DMA sound) must answer, $ff8a3c.b (blitter)
;            must answer and $ff8e21.b (Mega STE cache register) must bus-error = STE. Plain ST, Mega ST (no DMA sound) and Mega STE fail here.
;         3. Guarded real access: write $ffff to $ff9202, read $ff9202 and $ff9200 (words only: a byte read of $ff9200 bus-errors on a real STE); the
;            deselected idle read must be $ffxx / $xxxf. A bus error or any other value disables the pad.
;       SCAN (every VBL in J mode on a probed STE): the pad is a 4-group matrix (write the row-select word to $ff9202, read $ff9200 / $ff9202, low bit = pressed).
;       Group 4 (D-pad, A, Pause) is read EVERY VBL, and one of groups 3, 2, 1 in turn (ROT), so every button is seen at least every 3rd VBL (60 ms at 50 Hz).
;       Selects `$ffee/$ffdd/$ffbb/$ff77` (that group on port A AND port B in one write; never several groups of one port: a Team Tap decodes that differently),
;       >= 21 us at 8 MHz between a select write and its read (the second select is written before the first group is decoded), $ffff after the scan.
;       Port A and port B are OR-ed by two small tables (T1 rows, T2A / T2B buttons). State S, one byte per group (GB, g4 in the top byte):
;         bits 31-24 g4: 24 up 25 down 26 left 27 right, 28 A, 29 Pause    bits 23-16 g3: 16 `*` 17 `7` 18 `4` 19 `1`, 20 B
;         bits 15-8  g2: 8 `0` 9 `8` 10 `5` 11 `2`, 12 C                   bits 7-0   g1: 0 `#` 1 `9` 2 `6` 3 `3`, 4 Option
;       Key map (a changed bit makes its key on press and breaks it on release; one make per press, no auto-repeat; the game's repeat state $770a/$770c is
;       set like a real key press): A `,` $33 ("<" nose down / dive), C `.` $34 (">" nose up / climb), Option Esc $01 (leave vehicle; held for at least
;       ESCMIN = 16 VBLs because the game polls the key table once per logic tick), Pause P $19, keypad 1..9 F1..F9 $3b..$43, 0 F10 $44,
;       `*` keypad-minus $4a (previous weapon), `#` keypad-plus $4e (next weapon). B = fire (select event, no key).
;       The key bookkeeping mirrors the IKBD ISR $269fe (make) and $26a20+HAGA $3ea+$26a28 (break) and runs with interrupts masked (the ISR saves only d0-d3/a0).
FLAG    equ     $b9ee0
PADJ    equ     $b9ee1
PADBTN  equ     $b9ee2
ESCCNT  equ     $b9ee3                  ; VBLs of minimum hold left for Option (Esc)
PADOLD  equ     $b9ee4
GB      equ     $b9ee8
ROT     equ     $b9eec
ESCMIN  equ     16                      ; 320 ms at 50 Hz, 267 ms at 60 Hz: longer than a 5 Hz tick (200 ms) plus the scheduler's 1-VBL slack
        org     $262c2
        jsr     $b9500.l                ; 6 B: the displaced `jsr $27228.l` is the tail of the blob

        org     $b9500
jag_poll:
        cmpi.b  #2,FLAG.l
        beq.s   .out                    ; no pad ports: nothing touched
        tst.w   $eb76.l
        beq.s   .out                    ; not joystick mode
        movem.l d0-d4/a0-a3,-(a7)
        tst.b   FLAG.l
        bne.s   .scan
        bsr     probe
        cmpi.b  #1,FLAG.l
        bne.s   .done
.scan:  bsr     scan
.done:  movem.l (a7)+,d0-d4/a0-a3
.out:   jmp     $27228.l

; ---- one-time probe (68000 STE only); d0-d4/a0-a3 are the caller's to trash ----
probe:  move.b  #2,FLAG.l               ; fail closed
        moveq   #1,d0
        suba.l  a0,a0
        dc.w    $43f0,$0200             ; lea (0,a0,d0.w*2),a1: 1 on a 68000, 2 on a 68020+
        cmpa.w  #1,a1
        bne     .rts
        movem.l d5-d7/a2/a6,-(a7)
        move.w  sr,d4
        ori.w   #$700,sr
        move.l  $8.w,d7
        movea.l a7,a6
        lea     .be1(pc),a2
        move.l  a2,$8.w
        moveq   #0,d6
        tst.b   $ffff8901.w             ; DMA sound: bus error on ST / Mega ST
        moveq   #1,d6
        tst.b   $ffff8a3c.w             ; blitter
        moveq   #2,d6
        tst.b   $ffff8e21.w             ; Mega STE cache register: bus error on an STE
        moveq   #3,d6                   ; answered = Mega STE
.be1:   movea.l a6,a7
        cmpi.b  #2,d6
        bne.s   .restore                ; phase 1 stopped early (ST / Mega ST) or ran through (Mega STE): not an STE
        lea     .be2(pc),a2
        move.l  a2,$8.w
        moveq   #4,d6
        move.w  #$ffff,$ffff9202.w      ; deselect every group
        moveq   #5,d6
        move.w  $ffff9202.w,d0
        moveq   #6,d6
        move.w  $ffff9200.w,d1
        moveq   #9,d6                   ; both words answered
.be2:   movea.l a6,a7
.restore:
        move.l  d7,$8.w
        move.w  d4,sr
        cmpi.b  #9,d6
        bne.s   .fail                   ; any bus error, or phase 1 failed
        lsr.w   #8,d0
        cmpi.b  #$ff,d0                 ; $ff9202 idle high byte
        bne.s   .fail
        andi.w  #$f,d1
        cmpi.w  #$f,d1                  ; $ff9200 idle low nibble (a Mega STE reads $xxx9, a TT $xx03)
        bne.s   .fail
        move.b  #1,FLAG.l
.fail:  movem.l (a7)+,d5-d7/a2/a6
.rts:   rts

; ---- scan + merge + keys -----------------------------------------------------
; Select-to-read gaps (68000 cycles, 8 MHz): group 4 172, rotated group 178 (>= 160 = 20 us).
rottab: dc.w    $ffdd,$ffbb,$ff77       ; select words: group 3, 2, 1 (both ports); within reach of the (pc,d0.w) read below
scan:   lea     $ffff9200.w,a0
        lea     GB.l,a1
        lea     T1(pc),a2
        lea     T2A(pc),a3
        move.w  #$ffee,2(a0)            ; select group 4
        moveq   #0,d4
        move.b  ROT.l,d4                ; r = 0, 1, 2 -> group 3, 2, 1
        move.w  d4,d0
        addq.b  #1,d0
        cmpi.b  #3,d0
        bcs.s   .r1
        moveq   #0,d0
.r1:    move.b  d0,ROT.l                ; next r
        move.w  d4,d0
        add.w   d0,d0
        move.w  rottab(pc,d0.w),d3      ; select word of this round's group
        moveq   #7,d0
.w1:    dbra    d0,.w1
        move.w  (a0),d1                 ; group 4: buttons / rows
        move.w  2(a0),d2
        move.w  d3,2(a0)                ; select the rotated group
        lsr.w   #8,d2
        move.b  (a2,d2.w),d2            ; port A | port B rows, 1 = pressed
        andi.w  #$f,d1
        move.b  (a3,d1.w),d1            ; bit 4 button (A), bit 5 Pause
        or.b    d1,d2
        move.b  d2,(a1)                 ; GB[0]
        moveq   #9,d0
.w2:    dbra    d0,.w2
        move.w  (a0),d1                 ; rotated group
        move.w  2(a0),d2
        move.w  #$ffff,2(a0)            ; deselect
        lsr.w   #8,d2
        move.b  (a2,d2.w),d2
        andi.w  #$f,d1
        move.b  16(a3,d1.w),d1          ; T2B: bit 4 button (B / C / Option)
        or.b    d1,d2
        move.b  d2,1(a1,d4.w)           ; GB[1 + r]
        move.l  (a1),d3                 ; d3 = S
        move.b  (a1),d0
        andi.b  #$f,d0
        move.b  d0,PADJ.l               ; up / down / left / right
        moveq   #0,d0
        btst    #20,d3
        beq.s   .nf
        moveq   #1,d0
.nf:    move.b  d0,PADBTN.l             ; B = fire
        ; Option (Esc) is polled from the key table ($7687, `tst.b` + `clr.b` at $1b43a) once per 5 Hz logic tick, not latched like the other keys
        ; ($7684 / $75ac), so a tap shorter than a tick would be lost: its break is held back until ESCMIN VBLs after the press.
        tst.b   ESCCNT.l
        beq.s   .e1
        subq.b  #1,ESCCNT.l
        beq.s   .e1                     ; expired: the raw state decides
        bset    #4,d3                   ; still inside the minimum hold: Option stays pressed
.e1:    move.l  PADOLD.l,d1
        move.l  d3,PADOLD.l
        eor.l   d3,d1                   ; d1 = changed bits
        beq     .rts2
        btst    #4,d1
        beq.s   .e2
        btst    #4,d3
        beq.s   .e2
        move.b  #ESCMIN,ESCCNT.l        ; fresh Option press
.e2:    andi.l  #$300fffff,d1           ; keep A (28), Pause (29) and the keypad/C/Option bits 0-19; drop directions (24-27) and B (20)
        beq     .rts2
        movem.l d5-d7/a2,-(a7)
        move.l  d1,d6
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
        movem.l (a7)+,d5-d7/a2
.rts2:  rts

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

; T1[x], x = $ff9202 bits 15-8 (port B rows in the high nibble, port A in the low, 0 = pressed): 1 = pressed on either port
i       set     0
T1:
        rept    256
        dc.b    (~(i&(i>>4)))&$f
i       set     i+1
        endr
; T2A[y], y = $ff9200 bits 3-0 (bit 0 Pause A, 1 button A, 2 Pause B, 3 button B; 0 = pressed): bit 4 = button on either port, bit 5 = Pause on either
; T2B drops the Pause bit (only group 4 carries Pause)
i       set     0
T2A:
        rept    16
m       set     i&(i>>2)
        dc.b    ((((~m)>>1)&1)<<4)|(((~m)&1)<<5)
i       set     i+1
        endr
i       set     0
T2B:
        rept    16
m       set     i&(i>>2)
        dc.b    (((~m)>>1)&1)<<4
i       set     i+1
        endr
