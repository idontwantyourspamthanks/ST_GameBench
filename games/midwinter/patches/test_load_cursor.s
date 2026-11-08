; name: test_load_cursor
; default: no
; site: $53c30
; load: MWB 33 $53bf0
; note: TEST patch (deferred phase).  MWB directory file 33 (348 B) is loaded to $53BF0 during the
; note: boot, before the Game Options screen, by the game's loader sub_010cd2 (work/notes/loading.md
; note: section 3.3); it is not in RAM when the boot trampoline runs.  The load hook (core.s, spliced at
; note: $10D6C) applies the patch right after the load: 8 bytes at file offset $40 become $FF.
; note: Verified in RAM (work/notes/loading.md T3), not visible on screen [INFERENCE: some sprite/shape
; note: table; no visible change was seen on the Options/Team screens].
        org     $53c30
        dc.b    $ff,$ff,$ff,$ff,$ff,$ff,$ff,$ff
