; name: floppy_copybuf
; media: floppy
; default: yes
; site: $e566
; orig: 0050
; phase: boot
; note: floppy build only. On a >= 1 MB machine the game's own floppy-copy code ($2c542 reads
;   $ff8001, memconfig >= 5, and selects the copy list at $e566: 80 track-sides = 368640 B
;   read into $80000-$DA000; the 512K list at $e558 is 19 + 21 track-sides). Start New
;   Campaign / Create Back-up copy a disk through that buffer, which would overwrite the
;   $B3000 payload (HD build: PP's patch $2c542 bra.s forces the small list, so the issue
;   never arises there). Count 40 = $80000-$AD000, below the payload, and 160 track-sides
;   copy in 4 passes (same pass size as the 512K list). See work/notes/floppy.md.
        org     $e566
        dc.w    $0028
