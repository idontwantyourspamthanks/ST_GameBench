; name: p5_ctl_vbl
; default: yes
; site: $262c8
; orig: 6100088e61000950
; data: $b46c0 8
; note: P5 direct controls, part 1 of 2 (apply with p5_ctl_x; work/notes/p5_controls.md).
;       VBL sampler for joystick/keyboard steering. The game's VBL handler ($26298)
;       calls the joystick re-read $26b58 and the keyboard poll $26c1e at $262c8/$262cc.
;       Both calls move into the blob, followed by the sampler: every VBL it counts how
;       many VBLs the left / right direction was held since the logic tick last looked.
;         ELAPSED.w ($B46C0) VBLs since the consumer (p5_ctl_x) last read the counters
;         CNTL.w    ($B46C2) VBLs left was held   CNTR.w ($B46C4) VBLs right was held
;         PREV.w    ($B46C6) last yaw written by the consumer (reused if ELAPSED = 0)
;       Left  = joystick bit 2 of $75a9 (J mode) or KP7/KP4/KP1 (K mode).
;       Right = joystick bit 3 of $75a9 (J mode) or KP9/KP6/KP3 (K mode).
;       M mode counts nothing. All of d0-d7/a0-a6 are saved by the VBL handler.
ELAPSED equ     $b46c0
CNTL    equ     $b46c2
CNTR    equ     $b46c4
        org     $262c8
        jsr     $b4300.l
        nop

        org     $b4300
        jsr     $26b58.l                ; displaced: joystick re-read
        jsr     $26c1e.l                ; displaced: keyboard poll
        cmpi.w  #64,ELAPSED             ; window too long (menus, pauses): halve it,
        bcs.s   .cnt                    ; the held fractions stay the same
        lsr.w   ELAPSED
        lsr.w   CNTL
        lsr.w   CNTR
.cnt:   addq.w  #1,ELAPSED
        moveq   #0,d3                   ; d3 = left held, d4 = right held (nonzero)
        moveq   #0,d4
        tst.w   $eb76.l                 ; joystick mode
        beq.s   .nj
        move.b  $75a9.w,d1
        btst    #2,d1
        sne     d3
        btst    #3,d1
        sne     d4
        bra.s   .tally
.nj:    tst.w   $eb78.l                 ; keyboard mode
        beq.s   .done
        lea     $7686.w,a0              ; key-down table, $ff = down
        move.b  $67(a0),d3              ; KP7
        or.b    $6a(a0),d3              ; KP4
        or.b    $6d(a0),d3              ; KP1
        move.b  $69(a0),d4              ; KP9
        or.b    $6c(a0),d4              ; KP6
        or.b    $6f(a0),d4              ; KP3
.tally: tst.b   d3
        beq.s   .nl
        addq.w  #1,CNTL
.nl:    tst.b   d4
        beq.s   .done
        addq.w  #1,CNTR
.done:  rts
