; name: p4_ck_skip
; default: yes
; site: $1dd18
; note: item #2 (render.md s8). sub_01dd14 (object set-up, 1-2x per frame) starts with `jsr $122f0`: the
; note: per-object anti-tamper byte sum (48 cy/byte over the object's model data, 2.6 % walk / 7.3 % stand).
; note: The covered data ($31698-$3DDB4) is never written by any patch (antitamper.md); the routine only
; note: scribbles on $12390/$12394/$12398, and $1235c (global sum) re-initialises all three before use.
; note: Side effect of skipping: the hang on a mismatch (and on a model pointer missing from the table) is gone.
        org     $1dd18
        nop
        nop
        nop
