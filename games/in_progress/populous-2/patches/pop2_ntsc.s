; name: pop2_ntsc
; default: no
; site: $183c
; orig: 66000030
; note: First half of the 60 Hz fix (pop2_ntsc2 is the second; work/notes/timing.md).  The game's own PAL check.  Game entry ($1770) -> $1836: `btst.b #1,$820a.w`
; note: (shifter sync mode: 1 = 50 Hz) / `bne.w $186e` (continue); at 60 Hz it falls through to $1840, which shows the requester "SORRY PAL MACHINES ONLY" ($1856)
; note: and loops forever at $1850 (`bra.b $1850`).  Seen on Hatari's Mega STE with TOS 2.06 (US, "RGB 60 Hz"): work/shots/pal_only_megaste_60hz.png.  The patch
; note: makes the branch unconditional (`bra.w` with the same displacement); a 50 Hz machine is unchanged (the branch was taken anyway).  A 60 Hz machine
; note: needs pop2_ntsc2 as well (a second, hidden check in the pointer code zero-fills RAM when the pointer is lower than y = 184) and, for a world speed
; note: that does not depend on the refresh rate, the pop2_tick set.  default: no.
        org     $183c
        bra.w   $186e
