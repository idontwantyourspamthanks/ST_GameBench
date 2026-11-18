; name: snd_stop
; default: yes
; site: $1ae36
; orig: 23fc0001b7fa0001af3a
; note: STE DMA sound, part 3 of 4 (see snd_core.s).  $1ae36 = stop the player and wait until the timer IRQ ended its stream
; note: (called by $1b978 when a new sound replaces the old one, and at shutdown).  Its first instruction (10 B) becomes `jmp $d0008.l`:
; note: DMA off + busy flags cleared on STE, the displaced `move.l #$1b7fa,$1af3a.l` + `jmp $1ae40` on ST.
        org     $1ae36
        jmp     $d0008.l
