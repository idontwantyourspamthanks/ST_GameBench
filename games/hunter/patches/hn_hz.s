; name: hn_hz
; default: yes
; site: $c63c
; orig: 082d00070093
; note: 50/60 Hz (work/notes/timing.md). Hunter's world runs on VBL counts: the VBL handler ($c5f0 -> $c63a) does, once per VBL while the
; note: 3D loop runs ($93 bit 7): $1a8++, $1aa++ (VBLs since the last frame; the frame loop copies it to $1ac at $5fa4, and the movement,
; note: NPC and timer code multiplies by $1ac), the joystick copy $d1 -> $d0/$cf, the scripted-mode schedule ($c6b4), the countdown timers
; note: ($699c), and $355a (camera ease, turn/accelerate ramp $2a0, game clock $1b2..$1b8, stamina/breath timers $1b0/$1b1/$1ae).  At 60 Hz
; note: all of that ran 20 % fast.  This patch makes that block run at 50 Hz-equivalent: an accumulator in units of 1/300 s gets +6 per VBL
; note: at 50 Hz and +5 at 60 Hz (sync mode = $ff820a bit 1, read every VBL; 1 = 50 Hz); a "world tick" is due when the accumulator reaches 6
; note: (then -6, the remainder is carried).  On a VBL without a tick the whole block is skipped.  At 50 Hz every VBL is a tick, so the
; note: behaviour is byte-identical to the unpatched game.  The sound driver tick is gated through HZ_SKIP (read by snd_core: the original
; note: driver state machine runs on ticks only, the mixer tops up the DMA ring every VBL).  Per real VBL, unchanged: the IKBD poll, the palette
; note: fade step ($66ec, via $c66a), the mouse pointer redraw ($a65c), the flip lock (bit 3 of $8f), the wait-a-VBL loops (bit 7 of $8f).
; note: State (blob at $8dbf0): acc.w (units 0..5), skip.b at $8dbf2 (non-zero = this VBL is not a world tick). Needs no data: header.
HZ_ACC  equ     $8dbf0
HZ_SKIP equ     $8dbf2

        org     $c63c
        jmp     $8da00.l                ; replaces `btst #7,$93(a5)`; $c642 `beq.b $c66a` follows

        org     $8da00
hz_gate:
        moveq   #6,d0                   ; units of 1/300 s per VBL: 50 Hz
        btst    #1,$ffff820a.w          ; shifter sync mode: bit 1 set = 50 Hz
        bne.s   .u
        moveq   #5,d0                   ; 60 Hz
.u:     lea     HZ_ACC.l,a0
        add.w   (a0),d0
        cmpi.w  #6,d0
        bcs.s   .skip                   ; below one 50 Hz tick: no world tick on this VBL
        subq.w  #6,d0
        move.w  d0,(a0)
        clr.b   2(a0)
        btst    #7,$93(a5)              ; the original instruction: Z for the `beq.b $c66a` at $c642
        jmp     $c642.l
.skip:  move.w  d0,(a0)
        st      2(a0)
        jmp     $c66a.l                 ; skip the 3D-loop block, keep the rest of the handler ($c66a: palette fade step, mouse)

        org     $8dbf0
        dc.w    0                       ; HZ_ACC
        dc.b    0,0                     ; HZ_SKIP, pad
