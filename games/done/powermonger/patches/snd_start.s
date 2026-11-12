; name: snd_start
; default: yes
; site: $1ae5c
; orig: 41f90002cba6
; note: STE DMA sound, part 2 of 4 (see snd_core.s).  $1ae5c starts one sample chunk (chunk $2c998, timer-A data $2c99a): its first
; note: instruction `lea.l $2cba6.l,a0` becomes `jmp $d0004.l` (snd_start in snd_core: DMA on STE, the displaced lea + `jmp $1ae62` on ST).
        org     $1ae5c
        jmp     $d0004.l
