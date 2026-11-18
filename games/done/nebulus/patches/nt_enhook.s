; name: nt_enhook
; media: hd
; default: no
; site: $3792c
; orig: 303900033a20
; requires: nt_keys
; conflicts: nt_noenemy
; ram: blob of nt_keys
; doc: work/notes/trainers.md section 3
; note: Enemy spawn head `move.w $33a20.l,d0` (6 bytes, sub_03792c, only caller $3df42) becomes `jsr NT+$58.l`.  With E on, the hook clears the four
; note: creature state words ($3398c..$33993) and returns straight to the caller (no spawn, nothing drawn or hit); otherwise it executes the original
; note: instruction.  It IS retroactive: creatures on screen when E is pressed disappear on the next iteration.  The frog and the shot are not touched.
NT      equ     $76c00
        org     $3792c
        jsr     NT+$58.l
