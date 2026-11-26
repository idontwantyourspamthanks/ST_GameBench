; name: p5_ctl_x
; default: yes
; site: $34152
; orig: 6100069e7000
; note: P5 direct controls, part 2 of 2 (needs p5_ctl_vbl for J/K; work/notes/p5_controls.md).
;       Replaces `bsr.w $347f2` (X-axis clamp + deadzone, writes $6766) and the following
;       `moveq #0,d0`, once per logic tick, in sub_034142. Every one of the 22 vehicle
;       types uses the X axis for yaw (apply selector 4 = $345c4, rate selector 2 =
;       direct). The yoke store ($6fb6) is no longer used as a persistent rate.
;       The player sim runs once per 5 Hz tick (p3cp_head: once per group of five 40 ms passes; the extra
;       passes run no game logic), so every call consumes fresh input: the counters/accumulators are
;       read and cleared there, the mouse dx and the J/K held fractions accumulate until the next tick.
;       a0 = per-type control block ($54dc0+type*$3e) on entry; preserved.
;       M mode   $6766 = mouse dx accumulated since the previous tick * MOUSE_GAIN/256
;                (toward zero, capped at +-MOUSE_CAP), $6fb6 cleared. No motion, no turn.
;       J/K mode $6766 = YAW_PCT % of the old full-yoke rate (clamp - deadzone of the
;                vehicle, from the block) * (VBLs held right - left) / (VBLs elapsed since
;                the last tick) -- a constant rate while held, zero on release; a tap
;                shorter than a tick still turns pro rata. The ramps' $6fb6 is discarded.
;       The deadzone and the clamp write-back of $347f2 are gone for X. Downstream is
;       unchanged: $6752 = $6766*scale clamped to the vehicle's limits, $6740 = >>4.
MOUSE_GAIN equ  384                     ; 8.8 fixed: $6766 units per mouse count (1.5)
MOUSE_CAP  equ  1000                    ; |$6766| cap (keeps $6766*scale inside a word)
YAW_PCT    equ  50                      ; J/K yaw rate, % of the old full-yoke rate
YAW_NUM    equ  YAW_PCT*256/100
ELAPSED equ     $b46c0
CNTL    equ     $b46c2
CNTR    equ     $b46c4
PREV    equ     $b46c6
        org     $34152
        jsr     $b4400.l                ; 6 B = 4 B bsr.w + 2 B moveq

        org     $b4400
        movem.l d2-d5,-(a7)
        move.w  sr,d5
        tst.w   $eb7a.l
        bne.w   .mouse
        ; ---- joystick / keyboard
        ori.w   #$700,sr                ; the VBL sampler must not run in between
        move.w  ELAPSED,d3
        move.w  CNTR,d2
        sub.w   CNTL,d2                 ; d2 = VBLs right - VBLs left
        clr.l   ELAPSED                 ; ELAPSED + CNTL
        clr.w   CNTR
        clr.l   $6fb6.w                 ; discard the 50 Hz ramp
        move.w  d5,sr
        tst.w   d3
        beq.s   .prev                   ; no VBL since the last tick (catch-up tick)
        moveq   #0,d4                   ; d4 = left flag
        moveq   #0,d0                   ; d0 = yaw
        tst.w   d2
        beq.s   .st
        bpl.s   .right
        neg.w   d2
        moveq   #1,d4
        move.w  $14(a0),d1              ; left: -(clamp min) - deadzone
        neg.w   d1
        bra.s   .cap
.right: move.w  $16(a0),d1              ; right: clamp max - deadzone
.cap:   sub.w   $12(a0),d1
        ble.s   .st                     ; vehicle has no yaw on X (type 4)
        muls.w  #YAW_NUM,d1
        asr.l   #8,d1
        mulu.w  d2,d1                   ; * |R-L|
        divu.w  d3,d1                   ; / ELAPSED  (|R-L| <= ELAPSED, so it fits)
        move.w  d1,d0
        tst.b   d4
        beq.s   .st
        neg.w   d0
.st:    bra.s   .out
.prev:  move.w  PREV,d0
.out:   move.w  d0,PREV
        move.w  d0,$6766.w
        movem.l (a7)+,d2-d5
        moveq   #0,d0                   ; displaced
        rts
        ; ---- mouse: heading change = gain * dx since the last tick
.mouse: ori.w   #$700,sr                ; IKBD IRQ adds to $6fb6
        move.l  $6fb6.w,d0
        clr.l   $6fb6.w
        move.w  d5,sr
        swap    d0                      ; high word = summed dx
        ext.l   d0
        muls.w  #MOUSE_GAIN,d0
        moveq   #0,d4
        tst.l   d0
        bpl.s   .mp
        neg.l   d0
        moveq   #1,d4
.mp:    lsr.l   #8,d0                   ; magnitude, truncated toward zero
        cmpi.l  #MOUSE_CAP,d0
        bls.s   .mc
        move.l  #MOUSE_CAP,d0
.mc:    tst.b   d4
        beq.s   .out
        neg.w   d0
        bra.s   .out
