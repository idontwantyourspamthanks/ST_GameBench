; name: test_poke2
; default: no
; site: $1bb2c
; note: self-test of the stage 2 hook: 4 bytes inside the comment text of the save-disk boot block ($1bb0e, only ever
;       written to a save game disk) become 'PMP2'.  Build with --only test_poke2 [--corrupt] and peek $1bb2c after the boot.
        org     $1bb2c
        dc.b    'PMP2'
