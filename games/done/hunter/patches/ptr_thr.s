; name: ptr_thr
; default: yes
; site: $af9c
; orig: 0b030300
; note: Mouse IKBD threshold (1,1 instead of 3,3): at $af9a Hunter sends `move.l #$0b030300,$1d4(a5)`
; note: (IKBD command $0B = set mouse threshold X=3, Y=3), which holds back all 1-2 count movements until 3 counts
; note: accumulate and makes the menu pointer feel sticky/sluggish. Setting $0b010100 restores standard 1:1 ST mouse response.
        org     $af9c
        dc.l    $0b010100
