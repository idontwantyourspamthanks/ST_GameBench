; name: pm_noprot
; default: yes
; site: $14e4e
; orig: 60001374
; note: copy protection, part 1 of 2 (part 2: pm_noprot_box).  The game's "protection passed" state is the LONG at $14e4e
;       (== $2c; the slot sits inside a table of `bra.w $161c4`, so it is also executable code: `ori.b #$2c,d0` falls
;       through to the next identical `bra.w`).  b856 writes it after a correct answer to the manual question; the
;       untouched value `6000 1374` (first byte $60) makes the person-state handler at $11bf4 start the check ($b2d4:
;       decoy land + "Between Pages 18-23" question) and keeps the demo mode (no SAVE/FORMAT, $7774/$af10/$13ea6).
;       Presetting the exact value the success path leaves there means the check never starts and every later flag
;       reader behaves as after a correct answer.  Evidence and the success-path disassembly: work/notes/protection.md.
        org     $14e4e
        dc.l    $0000002c
