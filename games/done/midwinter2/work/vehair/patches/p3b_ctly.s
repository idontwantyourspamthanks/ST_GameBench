; name: p3b_ctly
; default: no
; site: $341cc
; orig: 41f900054dc0
; note: SCRATCH (MW2VehAir). The three control-rate routines sub_034142 (X, $6752), sub_0341cc (Y, $6756)
;       and sub_034256 (buttons, $675a) are STATEFUL for selector 1 (derivative: $676a/$676c = last input)
;       and selector 3 (integrator: $6754/$675c/$6758, $6752/$6756/$675a accumulate). They also write the
;       clamped yoke back ($347f2/$3481e). On a 25 Hz sub-pass they must not run again: the 5 Hz game runs
;       them once per tick. Run them only on the first pass of a group (HOLD = 0) or on a non-sub pass;
;       passes 2..5 leave $6752/$6756/$675a as the first pass set them (they are not cleared per pass;
;       $33bde clears only $674e and $6750).
D       equ     $b42e0
        org     $341cc
        jsr     $b8000.l
