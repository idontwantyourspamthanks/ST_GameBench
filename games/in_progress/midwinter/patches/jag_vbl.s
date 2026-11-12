; name: jag_vbl
; default: no
; site: $61e2
; orig: 610003dc61000346
; data: $b6bf0 8
; note: Jaguar pad support, part 1 of 4 (apply with jag_mrg, jag_btn, jag_rmp; work/notes/jagpad.md, reports/jaguar_pad_study.md).
;       The VBL handler $61a8 calls the joystick re-read `bsr.w $65c0` and the key poll `bsr.w $652e` at $61e2/$61e6 (8 bytes).
;       Both calls move into the blob, behind the pad poll.  JOYSTICK MODE ONLY ($2c178 != 0): in M and K mode the pad is ignored.
;       The pad sits on the STE enhanced joystick ports ($ff9200/$ff9202, read by the hardware, not the IKBD).  Every VBL, if a
;       pad port exists, the four rows of both ports are read (select word $ffee/$ffdd/$ffbb/$ff77 = group 4/3/2/1 on A and B,
;       OR-ed) and the 21 switches become the state S (1 = pressed): byte 0 = group 4 (bits 0-3 Up Down Left Right, bit 4 Pause,
;       bit 5 A), byte 1 = group 3 (bits 8-11 `*` 7 4 1, bit 13 B), byte 2 = group 2 (`0` 8 5 2, bit 21 C), byte 3 = group 1 (`#` 9 6 3, bit 29 Option).
;       What the game sees (every game variable is the one the IKBD path writes):
;         directions  PADJ (bits 0-3 = the IKBD joystick byte bits up/down/left/right) is OR-ed into the latched byte by jag_mrg
;                     ($65e2); a change sets the "new joystick byte" flag $2c32c so $65c0 recomputes the held vector $24f98/$24f9c,
;                     and replays it every VBL: the same funnel $66c0 -> $24faa/$24fae as the real stick, so p5_ctl_turn counts it.
;         fire (B)    PADBTN = 1 = the IKBD right-button bit a joystick-1 fire produces; jag_btn ($665e) ORs it into the button byte
;                     and jag_rmp ($6696) gives the J-mode remap `$2c32e == $f9` -> $24fba = 2 (left button), exactly the real fire.
;         A, C, Option, Pause, 1, 2, 3  make / break of a key: $2c324 (last scancode), $2c29a[sc] = $ff / 0, $2c326 pending, the
;                     same bookkeeping as the IKBD ISR $64ac/$64cc; one make per press, one break per release, nothing repeats.
;                     A = `>` $34 (right button = stop) C = Space $39  Option = X $2d  Pause = P $19  1 = M $32  2 = S $1f  3 = H $23
;       Detection (first VBL in J mode, cached in PADST: 0 unprobed / 1 pad ports / $ff none): 68000 CPU (the TT and Falcon are never
;       touched), DMA sound $ff8901.b and blitter $ff8a3c.b answer, the Mega STE register $ff8e21.b does not (bus errors caught
;       with the $8 vector swapped), then a guarded word write/read of $ff9202/$ff9200 whose idle value must be $ffxx / $xxxf.
;       Machines without a pad: one `move.b PADST` + `bmi` per VBL.
PADST   equ     $b6bf0                  ; byte 0 unprobed, 1 pad ports present, $ff none
PADJ    equ     $b6bf1                  ; byte: pad directions in the IKBD joystick byte layout (1 up, 2 down, 4 left, 8 right)
PADBTN  equ     $b6bf2                  ; byte: 1 = pad fire held (B)
PADOLD  equ     $b6bf4                  ; long: previous state S
KEYMASK equ     (1<<4)|(1<<5)|(1<<11)|(1<<19)|(1<<21)|(1<<27)|(1<<29)
        org     $61e2
        jsr     $b6900.l

        org     $b6900
vbl:    move.b  PADST.l,d0
        bmi.s   .disp                   ; $ff: no pad ports
        bne.s   .run                    ; 1: present
        tst.w   $2c178.l                ; 0: probe once, when joystick mode is first in effect
        beq.s   .disp
        bsr.w   probe
        tst.b   PADST.l
        bmi.s   .disp
.run:   bsr.w   poll
.disp:  jsr     $65c0.l                 ; displaced: joystick re-read
        jsr     $652e.l                 ; displaced: key poll
        rts

; ---- read the pad and process the changes ---------------------------------------------------------------------------------------
DEC     macro                           ; d1 = raw $ff9200, d2 = raw $ff9202 -> byte of the group in d3.b (bit 4 pause, 5 button, 0-3 rows; 1 = idle)
        move.w  d2,d7
        lsr.w   #4,d7
        and.w   d7,d2                   ; bits 8-11 = port A and port B rows (low = pressed on either)
        lsr.w   #8,d2
        move.w  d1,d7
        lsr.w   #2,d7
        and.w   d7,d1                   ; bits 0,1 = pause, button of A and B
        andi.w  #3,d1
        lsl.w   #4,d1
        or.w    d1,d2
        move.b  d2,d3
        ror.l   #8,d3
        endm

poll:   moveq   #0,d3
        tst.w   $2c178.l
        beq.w   upd                     ; not joystick mode: the pad counts as released
        lea     $ffff9200.w,a0
        move.w  #$ffee,2(a0)            ; group 4 (Up Down Left Right, Pause, A)
        moveq   #15,d6
.w1:    dbra    d6,.w1                  ; ~23 us settle (8 MHz)
        move.w  (a0),d1
        move.w  2(a0),d2
        move.w  #$ffdd,2(a0)            ; group 3 (`*` 7 4 1, B)
        DEC                             ; decode group 4 while group 3 settles
        moveq   #4,d6
.w2:    dbra    d6,.w2
        move.w  (a0),d1
        move.w  2(a0),d2
        move.w  #$ffbb,2(a0)            ; group 2 (`0` 8 5 2, C)
        DEC
        moveq   #4,d6
.w3:    dbra    d6,.w3
        move.w  (a0),d1
        move.w  2(a0),d2
        move.w  #$ff77,2(a0)            ; group 1 (`#` 9 6 3, Option)
        DEC
        moveq   #4,d6
.w4:    dbra    d6,.w4
        move.w  (a0),d1
        move.w  2(a0),d2
        move.w  #$ffff,2(a0)            ; no group driven
        DEC
        not.l   d3
        and.l   #$3f3f3f3f,d3           ; S, 1 = pressed

upd:    move.l  PADOLD.l,d4
        cmp.l   d3,d4
        beq.w   .rts                    ; nothing changed
        move.l  d3,PADOLD.l
        eor.l   d3,d4                   ; d4 = bits that changed
        move.b  d3,d0
        andi.b  #$0f,d0
        cmp.b   PADJ.l,d0
        beq.s   .nd
        move.b  d0,PADJ.l
        move.w  #$ffff,$2c32c.l         ; "new joystick byte": $65c0 recomputes the vector from $2c328 | PADJ
.nd:    moveq   #0,d0
        btst    #13,d3                  ; B = fire
        beq.s   .nf
        moveq   #1,d0
.nf:    move.b  d0,PADBTN.l
        move.l  d4,d5
        and.l   #KEYMASK,d5
        beq.w   .rts
        move.w  sr,d6                   ; the IKBD ISR (IPL 6) writes the same key variables
        ori.w   #$0700,sr
        lea     keymap(pc),a2
        lea     $2c29a.l,a1
.kl:    move.b  (a2)+,d7
        bmi.s   .ke
        moveq   #0,d0
        move.b  (a2)+,d0                ; scancode
        btst    d7,d5
        beq.s   .kl
        btst    d7,d3
        beq.s   .brk
        move.w  d0,$2c324.l             ; make: as $64b6..$64c2
        move.b  #$ff,(a1,d0.w)
        move.w  #$ffff,$2c326.l
        bra.s   .kl
.brk:   move.w  d0,d1                   ; break: as $64cc..$64e2 (the HAGA save-state hook $392 only matters for $e5/$e6)
        ori.w   #$80,d1
        move.w  d1,$2c324.l
        clr.b   (a1,d0.w)
        tst.w   $2c326.l
        bne.s   .kl
        clr.w   $2c324.l
        bra.s   .kl
.ke:    move.w  d6,sr
.rts:   rts

keymap: dc.b    5,$34                   ; A      -> '>' (right button: stop)
        dc.b    21,$39                  ; C      -> Space (grenade / bullets / missiles, glider 45 degree view)
        dc.b    29,$2d                  ; Option -> X (leave the action mode)
        dc.b    4,$19                   ; Pause  -> P
        dc.b    11,$32                  ; 1      -> M (main map)
        dc.b    19,$1f                  ; 2      -> S (ski / snipe)
        dc.b    27,$23                  ; 3      -> H (help)
        dc.b    $ff,0

; ---- detection ---------------------------------------------------------------------------------------------------------------------
probe:  move.b  #$ff,PADST.l            ; fail closed
        moveq   #1,d0
        suba.l  a0,a0
        dc.w    $43f0,$0200             ; lea (0,a0,d0.w*2),a1: 1 on a 68000 (ignores the scale), 2 on a 68020+
        cmpa.w  #1,a1
        bne.s   .out                    ; TT / Falcon / accelerators: never touch the pad registers
        move.l  $8.w,d7                 ; bus error vector
        movea.l a7,a6
        lea     .be1(pc),a2
        move.l  a2,$8.w
        moveq   #0,d6
        tst.b   $ffff8901.w             ; DMA sound: absent on ST / Mega ST
        moveq   #1,d6
        tst.b   $ffff8a3c.w             ; blitter: absent on a plain ST
        moveq   #2,d6
        tst.b   $ffff8e21.w             ; Mega STE cache register: no bus error = Mega STE (DIP bits at $ff9200, no pad)
        moveq   #3,d6
.be1:   movea.l a6,a7
        move.l  d7,$8.w
        cmp.b   #2,d6
        bne.s   .out
        lea     .be2(pc),a2
        move.l  a2,$8.w
        moveq   #0,d6
        move.w  #$ffff,$ffff9202.w      ; no group driven
        move.w  $ffff9202.w,d4
        move.w  $ffff9200.w,d5
        moveq   #1,d6
.be2:   movea.l a6,a7
        move.l  d7,$8.w
        tst.b   d6
        beq.s   .out                    ; a bus error on the pad registers
        lsr.w   #8,d4
        cmp.b   #$ff,d4
        bne.s   .out                    ; rows must idle high
        andi.w  #$000f,d5
        cmp.w   #$000f,d5
        bne.s   .out                    ; pause / buttons must idle high
        move.b  #1,PADST.l
.out:   rts
