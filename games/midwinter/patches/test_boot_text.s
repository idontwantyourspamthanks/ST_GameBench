; name: test_boot_text
; default: no
; site: $250ea
; phase: boot
; note: TEST patch (boot phase). The Game Options screen labels its first control icon with the
; note: resident ASCII string "MOUSE" (NUL-terminated, five characters, game file MWA/1 at RAM
; note: $250EA, found by a string search of the Options-screen RAM dump).  This replaces it with
; note: "PATCH": visible on the screen and readable in RAM (`m $250ea 6`).  Same length, so the
; note: site table verifies the five original bytes and applies the new ones before the game runs.
        org     $250ea
        dc.b    "PATCH"
