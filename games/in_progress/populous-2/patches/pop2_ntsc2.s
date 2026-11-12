; name: pop2_ntsc2
; default: no
; site: $1a6e
; orig: 670005ac
; note: Second half of the 60 Hz fix (pop2_ntsc is the first; work/notes/timing.md).  The game protects itself against NTSC in TWO places, both reading the
; note: shifter sync mode `btst.b #1,$820a.w` (bit 1 set = 50 Hz): the PAL check at $1836 (`SORRY PAL MACHINES ONLY`, pop2_ntsc) and this one, inside the
; note: VBL handler's pointer draw: $1a5e `subi.w #$b8,d2` (pointer y - 184) / `ble.w $1a72` (y <= 184: draw all 16 rows) / $1a66 `sub.w d2,d7` (rows to clip at the
; note: bottom edge) / $1a68 `btst.b #1,$820a.w` / $1a6e `beq.w $201c` - at 60 Hz, whenever the pointer is lower than y = 184 - $201c is
; note: `suba.l a0,a0` / `clr.l (a0)+` / `bra.b $201e`: a loop in the VBL handler that zero-fills RAM from address 0 upwards (vectors, then the game itself) until
; note: the bus error.  That is what "draws garbage and dies" at 60 Hz was: PROCEED on the battle sheet sits at y = 195.  This patch drops the branch
; note: (two nops): the clip at the bottom edge ($1a72, the 50 Hz path) runs at 60 Hz as well, so the pointer, and with it every pixel the game draws, is the
; note: same as at 50 Hz.  No other reader of $820a/$ff820a exists in the game ($1836, $1a68 only: linear disassembly of $1770-$7b380).  At 50 Hz the
; note: branch was never taken, so nothing changes there.  Needs pop2_ntsc for the PAL check; default: no (the 60 Hz work item).
        org     $1a6e
        nop
        nop
