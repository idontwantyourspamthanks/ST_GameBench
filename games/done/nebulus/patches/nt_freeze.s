; name: nt_freeze
; media: hd
; default: no
; site: $3b0aa
; orig: 6700004e
; conflicts: nt_keys
; ram: none
; doc: work/notes/trainers.md section 1
; note: Level timer frozen from boot (static variant, no blob, no key). sub_03b0a4 (the timer tick, one call per game-loop iteration) starts
; note: `tst.w $33938.l / beq.w $3b0fa` ($3b0a4..$3b0ad): `beq.w` (67 00 00 4e) becomes `bra.w` (60 00 00 4e), so the three digit words
; note: $3ad98/9a/9c never change.  The zero test at $3b0fa still runs (never zero in play).  Level restart / next tower reload the
; note: start value from the table at $3ad9e (BCD 400,450,...,750) and the clock stays frozen at it.  Verified live (byte form of the debugger `w`!).
        org     $3b0aa
        bra.w   $3b0fa
