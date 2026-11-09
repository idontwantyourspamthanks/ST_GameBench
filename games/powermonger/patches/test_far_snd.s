; name: snd_testfar
; default: no
; data: $e0000 4096
; note: gate for the sparse payload: a blob at the start of the snd_ range and a data span at $E0000.  Never applied.
        org     $d0000
        dc.b    'PMFAR3'
