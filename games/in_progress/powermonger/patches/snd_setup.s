; name: snd_setup
; default: yes
; site: $11f0
; orig: 508f33fc00010002de66
; note: STE DMA sound, part 4 of 4 (see snd_core.s).  Game start, right after `jsr $1b83c` built the FX.DAT sound tables:
; note: `addq.l #8,a7 ; move.w #1,$2de66.l` (10 B) become `jsr $d000c.l` + nops.  snd_setup (snd_core) does the Microwire setup (STE only),
; note: runs the two displaced instructions and returns with a7 as after the addq.
        org     $11f0
        jsr     $d000c.l
