; name: test_blob16k
; default: no
; site: $2b4c0
; orig: 4e71
; note: payload-capacity test (work/notes/payload32k.md). The site is an existing `nop` that is
;       rewritten with `nop` (no behavioural change; nothing jumps into the blob). The blob is
;       16 KB at $B6000-$B9FFF, i.e. inside the part of the $8000-byte payload ($B3000-$BAFFF)
;       that only exists since the payload grew beyond $1F00. Contents: the 16-byte signature
;       'MW2-TEST-BLOB16K', then 8184 words, each equal to the low 16 bits of its own address
;       ($6010, $6012, ... $9FFE), so a displaced, truncated or overwritten copy shows up at once.
        org     $2b4c0
        nop

        org     $b6000
        dc.b    'MW2-TEST-BLOB16K'
        rept    8184
        dc.w    *&$ffff
        endr
