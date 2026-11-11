; name: p3b_probe
; default: yes
; site: $33dc6
; orig: 6100023e4a78676e
; note: P3 partial-B: the collision/terrain probe $34006 (two calls per pass, about
;       15 k cycles each, two thirds of sub_033bca) runs only on the world pass (PH 5)
;       of a foot group, like option A, instead of on all five 25 Hz sub-ticks.
;       The site is the foot (flags bit 0) path of sub_033bde: `bsr.w $34006` then
;       `tst.w $676e.w`, followed by `bne.w $33e34`. On a foot sub-tick (SUB = 1, PH < 5)
;       the hook clears $676e and returns with Z = 0, so the bne goes straight to
;       $33e34 (view matrix, cell): the probe, the arrival test $33e7a and the second
;       probe at $33e30 are all skipped. $676e must not keep the world pass's value:
;       the post-flip handler $32db6 acts on it every rendered pass, and option A would
;       have cleared it at the next tick's probe.
;       Otherwise (world pass, or not foot) it runs the probe and tests $676e as the
;       original. Together with p3b_save (position saved at PH 1) the probe at PH 5
;       sees the full 5 Hz step and reverts to the group start, exactly as option A.
D       equ     $b42e0
        org     $33dc6
        jsr     $b4c00.l
        nop

        org     $b4c00
        tst.w   D+8.l                   ; SUB
        beq.s   .run
        cmpi.w  #5,D+6.l                ; PH
        bne.s   .skip
.run:   jsr     $34006.l
        tst.w   $676e.w
        rts
.skip:  clr.w   $676e.w                 ; the probe would have cleared it
        tst.w   D+8.l                   ; SUB = 1: flags NE
        rts
