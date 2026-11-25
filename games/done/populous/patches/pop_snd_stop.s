; name: pop_snd_stop
; default: yes
; prog: populous
; machine: ste, tt, falcon
; site: $16fb6
; orig: 51f900024990
; note: Companion to pop_snd: clears STE DMA loop/playback when the game stops a looping SFX ($16fb6).
;       Blob $b92a0.

        org     $16fb6
        jmp     $b92a0.l

        org     $b92a0
sstop:  sf.b    $024990.l
        clr.b   $ffff8901.w             ; stop DMA playback
        rts
