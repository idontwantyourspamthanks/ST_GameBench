; name: tick_head
; default: no
; site: $31486
; orig: 4df8770e4eb84f5a
; data: $b3404 12
; note: P3 fixed-tick, part 2 (option A). It runs at the head of the in-game
;       frame loop ($31486, work/notes/frameloop.md) and makes the game logic
;       advance at a fixed real-time rate of one tick per TICK clock units (1/300 s,
;       the tick_vbl clock adds 6 per 50 Hz VBL and 5 per 60 Hz VBL), whatever
;       the frame rate and the display refresh rate.
;         ACC ($B3408.l) = real time not yet simulated, in 1/300 s units.
;         Ahead (ACC < TICK): spin until the VBL clock (tick_vbl, $B3400)
;         catches up. This is the frame limiter for fast machines.
;         Behind by another whole tick after this one: set SKIP ($B3404.w) so
;         tick_render skips render+flip and loops straight back here.
;         Catch-up is clamped to 3 ticks.
;       LAST ($B3400 snapshot) is kept at $B340C.l.
;       TICK = 60 units = 0.2 s (5 Hz, 10 VBL at 50 Hz) is about the original speed on a 1 MB 8 MHz STE,
;       where unpatched frames take 9.6-11.9 VBL (work/baseline.md).
TICK    equ     60
CLOCK   equ     $b3400
SKIP    equ     $b3404
ACC     equ     $b3408
LAST    equ     $b340c
        org     $31486
        jsr     $b4000.l
        nop

        org     $b4000
        movem.l d0-d1,-(a7)
.wait:  move.l  CLOCK,d0
        move.l  d0,d1
        sub.l   LAST,d1                 ; VBLs since the previous look
        move.l  d0,LAST
        cmpi.l  #4*TICK,d1
        bls.s   .acc
        moveq   #TICK,d1                ; first entry or back from another screen:
        clr.l   ACC                     ; resync, no catch-up burst
.acc:   add.l   d1,ACC
        cmpi.l  #TICK,ACC
        blt.s   .wait                   ; ahead of real time: wait for VBLs
        subi.l  #TICK,ACC               ; this pass simulates one tick
        cmpi.l  #3*TICK,ACC
        ble.s   .noclamp
        move.l  #3*TICK,ACC             ; bound the catch-up
.noclamp:
        clr.w   SKIP
        cmpi.l  #TICK,ACC
        blt.s   .done
        move.w  #1,SKIP                 ; another tick owed: skip this render
.done:  movem.l (a7)+,d0-d1
        lea     $770e.w,a6              ; displaced
        jmp     $4f5a.w                 ; displaced jsr, as a tail call
