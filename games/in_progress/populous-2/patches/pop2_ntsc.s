; name: pop2_ntsc
; default: no
; site: $183c
; orig: 66000030
; note: The game's own PAL check.  Game entry ($1770) -> $1836: `btst.b #1,$820a.w` (shifter sync mode: 1 = 50 Hz) / `bne.w $186e`
; note: (continue); at 60 Hz it falls through to $1840, which shows the requester "SORRY PAL MACHINES ONLY" ($1856) and loops
; note: forever at $1850 (`bra.b $1850`).  Seen on Hatari's Mega STE with TOS 2.06 (US, "RGB 60 Hz"): work/shots/credit_menu_megaste_4mb.png
; note: of the first run, work/notes/delivery.md.  The patch makes the branch unconditional (`bra.w` with the same displacement), so a
; note: 60 Hz machine plays; a 50 Hz machine is unchanged (the branch was taken anyway).  The game's pacing at 60 Hz is the usual
; note: one-pass-per-VBL (1.2x faster than at 50 Hz): the fixed-tick patch is where that gets decided.  default: no - not in the task's list.
        org     $183c
        bra.w   $186e
