; name: nt_tmrhook
; media: hd
; default: no
; site: $3b0a4
; orig: 4a7900033938
; requires: nt_keys
; conflicts: nt_freeze
; ram: blob of nt_keys
; doc: work/notes/trainers.md section 3
; note: Timer tick head `tst.w $33938.l` (6 bytes, sub_03b0a4, only caller $3dfa4) becomes `jsr NT+$40.l`: the hook returns the same flags
; note: (Z when the play gate $33938 is 0) or Z=1 while T froze the clock, so the following `beq.w $3b0fa` skips the tick.
NT      equ     $76c00
        org     $3b0a4
        jsr     NT+$40.l
