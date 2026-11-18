; name: nt_noenemy
; media: hd
; default: no
; site: $3792c
; orig: 3039
; conflicts: nt_keys
; ram: none
; doc: work/notes/trainers.md section 2
; note: No enemies from boot (static variant, no blob, no key).  sub_03792c (the enemy spawn, one call per game-loop iteration) starts with
; note: `move.w $33a20.l,d0` (30 39 00 03 3a 20); its first word becomes `rts`: nothing spawns (grid-cell creatures and the time-waster flyer),
; note: so the 4 creature slots ($33944 + 2*i, state word at +$48) stay at state 0 = not updated, not drawn, not hit.  The next 4 bytes are left
; note: as they are (dead code).  Not retroactive: creatures already alive keep running (none exist at boot).  Level end does not depend on enemies.
        org     $3792c
        rts
