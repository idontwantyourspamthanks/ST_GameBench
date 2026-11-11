; name: test_defer_poke
; default: no
; site: $11642
; load: FILES/4 $10fb2
; Loader self-test (deferred phase, exercises the load hook at $1a6): 8 zero pad bytes at the end of the sound driver
; file FILES/4 (loaded to $10FB2, 1700 B) get a signature.  RAM proof: peek $11642 after boot == "HNDEFER!".
        org     $11642
        dc.b    "HNDEFER!"
