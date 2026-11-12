; name: p3b_probe2
; default: no
; site: $34006
; orig: 48e7fffe4278676e
; note: SCRATCH (MW2VehAir). sub_034006 (terrain/collision probe) entry: the second call at $33e30 is the
;       probe of every non-generic block (Balloon $33c60, Rocket $33d26, Parachute $33cc2 end at
;       `bra $33e30`). On sub-passes 1..4 of a group it must not run (collision revert $34056/$340d4,
;       $676e event), only on pass 5 (world) or non-sub passes. The skip path clears $676e as
;       p3b_probe does and returns to the caller; the run path does the displaced code.
D       equ     $b42e0
        org     $34006
        jsr     $b8300.l
        nop

        org     $b8300
        addq.l  #4,a7                   ; drop our return address
        tst.w   D+8.l                   ; SUB
        beq.s   .run
        cmpi.w  #5,D+6.l                ; PH
        bne.s   .skip
.run:   movem.l d0-d7/a0-a6,-(a7)       ; displaced
        clr.w   $676e.w
        jmp     $3400e.l
.skip:  clr.w   $676e.w
        rts
