; name: pop_keys4
; default: no
; prog: populous
; site: $1a508
; orig: 4e5600004a790003d566
; note: Dialog guard for pop_keys (PopUI).  `$1a508(rectA, rectB)` is the game's button hit test; every dialog and requester of the game polls it in
; note: its own loop (14 call sites, none in the map loop: $18b14 text entry, $19176, $1947a, $1960a, $1a11a, $1b012, $1bb7a, $1c066, $1c6ce,
; note: $1d038, $1f3ea, $1fa78, $1feaa, $1ff76).  While one is open the hook empties pop_keys' key ring and drops the Armageddon arm at every poll, so
; note: a key pressed while an options / setup / save dialog is open (pop_keys2 records it in the interrupt, before anybody knows who reads it) can
; note: never be replayed as an icon click when the dialog closes.  Together with pop_keys3 (the text poll $200a6) and the pass stamp of pop_keys.
; note: Change: `link.w a6,#0` + `tst.w $3d566.l` (10 bytes) become `jmp` + 2 nops; the blob runs them after the flush and continues at $1a512
; note: (the `bne.w` that reads the flags of the tst).  Does nothing unless pop_keys' hook is in place.
KD      equ     $c8000
        org     $1a508
        jmp     $c73c0.l
        nop
        nop

        org     $c73c0
dh:     cmpi.w  #$4eb9,$0bb7c.l         ; pop_keys installed?
        bne.s   .go
        move.b  KD+11.l,KD+10.l         ; head := tail
        clr.l   KD+4.l
.go:    link.w  a6,#0                   ; the displaced instructions
        tst.w   $3d566.l
        jmp     $01a512.l
