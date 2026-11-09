; name: p5_ctl_turn
; default: yes
; site: $12fe2
; data: $b3bf0 4
; note: P5 direct controls, part 1 of 2 (apply with p5_ctl_buggy; work/notes/p5_controls.md).
;       Replaces sub_012fe2, the per-step turn consumer shared by the ski ($13236), the snow
;       buggy ($135d0) and the hang glider ($13754). The first 6 bytes (move.w $24faa.l,d0)
;       become `jmp $b3800.l`; the rest of the old routine (the +-512 clamp, the write-back that
;       made the deflection a persistent "yoke" and the cubic rate) is never reached.
;       Every call: consume ALL counts the input funnel ($66c0) added to $24faa since the
;       previous call (one `sub.l d0,$24faa` against the value read, so an IKBD IRQ add in
;       between is not lost), scale them linearly, and
;         $15110 = turn this call   $12c98 += turn   d1 = d0 = turn (the glider reads d1)
;       Mouse: the funnel gets dx per IKBD packet, so the turn is proportional to the motion
;       and is zero the moment the mouse stops. Joystick / numpad keys: the VBL handler
;       injects +-5 counts per VBL while held ($65c0/$652e), so the counts consumed between two
;       calls are 5 x (VBLs held): a constant rate per real second while held, nothing after
;       release, whatever the call interval (a tap shorter than a step still turns pro rata).
;       Gain: MOUSE_GAIN (mouse control selected, $2c176 != 0) or KEY_GAIN (stick/keys), in
;       1/256 heading units (1024 per turn) per count. The sub-unit remainder is carried in
;       REM (blob data) so slow mouse motion is not truncated away; |REM| < 256 always, so it
;       can never produce a turn on its own. CAP limits one call's counts (counts that piled
;       up while the sim did not run, e.g. a held key during a pause).
MOUSE_GAIN equ  192                     ; 0.75 units/count = 0.26 deg/count (as MW2)
KEY_GAIN   equ  128                     ; 0.5 units/count x 5 counts x 50 VBL/s = 125 units/s
CAP        equ  200                     ; counts per call
REM        equ  $b3bf0
        org     $12fe2
        jmp     $b3800.l

        org     $b3800
        move.l  d2,-(a7)
        move.l  $24faa.l,d0             ; high word = signed sum of counts, low word 0
        sub.l   d0,$24faa.l             ; consume exactly what was read
        swap    d0
        ext.l   d0                      ; d0 = counts
        cmp.l   #CAP,d0
        ble.s   .c1
        move.l  #CAP,d0
.c1:    cmp.l   #-CAP,d0
        bge.s   .c2
        move.l  #-CAP,d0
.c2:    move.w  #KEY_GAIN,d1
        tst.w   $2c176.l                ; mouse control selected
        beq.s   .g
        move.w  #MOUSE_GAIN,d1
.g:     muls.w  d1,d0                   ; 8.8 units
        add.l   REM.l,d0
        move.l  d0,d1
        bpl.s   .pos
        neg.l   d1
        lsr.l   #8,d1
        neg.l   d1                      ; truncate toward zero
        bra.s   .out
.pos:   lsr.l   #8,d1
.out:   move.l  d1,d2
        asl.l   #8,d2
        sub.l   d2,d0                   ; remainder, same sign as the input, |r| < 256
        move.l  d0,REM.l
        move.w  d1,$15110.l             ; displaced: turn rate of this step
        add.w   d1,$12c98.l             ; displaced: heading
        move.w  d1,d0
        move.l  (a7)+,d2
        rts
