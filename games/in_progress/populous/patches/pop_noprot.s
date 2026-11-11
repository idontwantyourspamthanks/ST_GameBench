; name: pop_noprot
; default: yes
; prog: populous
; site: $ee16
; orig: 6752
; note: Makes the copy-protection check of POPULOUS.TOS pass.  The peep loop of the world step ($db8a) reaches
; note: `cmpi.w #$12,-2(a6)` at $edec when it gets to peep slot 18: it asks the Supexec routine $16020 for the long at
; note: address $24 (2 * 18) and compares it with `$21d92 * 2` ($54ac0842, the key the original disk's loader
; note: left at $24).  PP's build removes the disk protection but not this check, and address $24 holds $090d0578
; note: there; with it armed the game falls into Armageddon (both players' state word +6 := 1, $3d562 := 1)
; note: as soon as more than 18 peep slots are in use (work/notes/baseline.md "The copy-protection trap").
; note: Change: the `beq.b $ee6a` after `cmp.l d1,d0` (the "key matches" branch) becomes `bra.b $ee6a`; one byte.
        org     $ee16
        bra.b   $ee6a
