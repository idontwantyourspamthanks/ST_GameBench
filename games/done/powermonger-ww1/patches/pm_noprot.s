; name: pm_noprot
; default: yes
; site: $15998
; orig: 600015ea
; note: copy protection, part 1 of 2 (part 2: pm_noprot_box).  Port of master's pm_noprot (games/done/powermonger, notes/protection.md); WW1's address is
;       master $14e4e + $b4a.  The game's "protection passed" state is the LONG at $15998 (== $2c).  The slot sits inside a run of identical
;       `bra.w $16f84` instructions (the people-state jump table), so it is also executable code: `ori.b #$2c,d0` falls through to the next `bra.w`.
;       The routine at $b232 (answer check) writes it after a correct answer (`move.l d0,$242(a0)` with a0 = $15756, $b240-$b246), the check
;       routine at $ae20 clears it before asking.  The untouched value `6000 15ea` (first byte $60) makes the person-state handler at $12a84
;       (`cmpi.b #$60,$154($15844)` at $12a8e) start the check ($acc4: decoy land + "Between Pages 2-7" question) and keeps the demo mode
;       (no SAVE / FORMAT: readers `cmpi.l #$2c,$15998` at $7202, $724c, $a918, $a932, $14c2a; the only writers are $b246 and $ae26).  Presetting the exact value the success path leaves there means the
;       check never starts and every later flag reader behaves as after a correct answer.  Evidence: work/notes/RESULTS_stage02.md.
        org     $15998
        dc.l    $0000002c
