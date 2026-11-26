; name: p8_clip_fast
; default: yes
; site: $1fdf0
; orig: 48e7fffe267c00010000
; phase: deferred
; note: Homogeneous edge clipper sub_01fdf0: ~33% of calls trivially reject (d4&d5 != 0) or
; note: trivially accept (d4^d5 == 0) at $1fe2c/$1fe34, yet previously paid 260 cy for a full
; note: 15-register movem.l save+restore. Check trivial reject/accept first with only 5 regs
; note: saved (d4-d6/a5-a6), writing $1fde8/$1fdec/$1fbe8/$1fbea identically; only push the
; note: full 15-register frame and rejoin $1fe38 when intersection math is actually needed.
        org     $1fdf0
        jmp     $b9200.l
        nop
        nop

        org     $b9200
        movem.l d4-d6/a5-a6,-(a7)
        lea     (a4,d4.w),a5
        lea     (a4,d5.w),a6
        move.l  (a5),$1fde8.l
        move.l  (a6),$1fdec.l
        clr.w   $1fbe8.l
        clr.w   $1fbea.l
        move.w  4(a5),d4
        move.w  4(a6),d5
        move.w  d4,d6
        and.w   d5,d6
        bne.s   .triv
        move.w  d4,d6
        eor.w   d5,d6
        beq.s   .triv
        ; Need full clip: restore original 5 regs, push full 15-reg frame, set a3 and rejoin $1fe38
        movem.l (a7)+,d4-d6/a5-a6
        movem.l d0-d7/a0-a6,-(a7)
        movea.l #$10000,a3
        lea     (a4,d4.w),a5
        lea     (a4,d5.w),a6
        move.w  4(a5),d4
        move.w  4(a6),d5
        move.w  d4,d6
        eor.w   d5,d6
        jmp     $1fe38.l
.triv:  movem.l (a7)+,d4-d6/a5-a6
        rts
