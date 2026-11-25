; name: snd_stop
; default: yes
; site: $1bb96
; orig: 23fc0001c55a0001bc9a
; note: STE DMA sound, part 3 of 4 (see snd_core.s).  $1bb96 = stop the player and wait until the timer IRQ ended its stream (called when a new sound replaces the old one, and at shutdown).  Its first instruction (10 B) becomes `jmp $76408.l`: DMA off + busy flags cleared on STE, the displaced `move.l #$1c55a,$1bc9a.l` + `jmp $1bba0` on ST.
        org     $1bb96
        jmp     $76408.l
