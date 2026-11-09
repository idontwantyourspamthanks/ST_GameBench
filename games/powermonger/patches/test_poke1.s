; name: test_poke1
; default: no
; stage: 1
; site: $56ff0
; note: self-test of the stage 1 hook: 4 bytes of the 0x7f padding in front of the stage 1 loader ($56fe0..$57031, never
;       read or executed) become 'PMP1'.  Build with --only test_poke1 [--corrupt] and peek $56ff0 after the boot.
        org     $56ff0
        dc.b    'PMP1'
