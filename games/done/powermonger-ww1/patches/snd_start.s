; name: snd_start
; default: yes
; site: $1bbbc
; orig: 41f90002d9c6
; note: STE DMA sound, part 2 of 4 (see snd_core.s).  $1bbbc starts one sample chunk (chunk $2d7b8, timer-A data $2d7ba): its first instruction `lea.l $2d9c6.l,a0` becomes `jmp $76404.l` (snd_start in snd_core: DMA on STE, the displaced lea + `jmp $1bbc2` on ST).
        org     $1bbbc
        jmp     $76404.l
