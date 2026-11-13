; name: pop2_spr16
; default: yes
; site: $212b4
; orig: 727044015342
; note: Item 2, the 16 px sprite variant $212b4 (called by the 16 px front end $211be: 4-5 times per pass in the first minutes of a game, 1.1 % of the busy frame):
; note: only the site; the code is in pop2_spr's blob (PB+$5400), so it needs pop2_spr (they ship together).  Blitter on an STE, the original code on a plain ST.
SPR16   equ     PB+$5400
        org     $212b4
        jmp     SPR16.l
