; name: snd_setup
; default: yes
; site: $6de
; orig: 508f33fc00010002ec86
; note: STE DMA sound, part 4 of 4 (see snd_core.s).  Game start, right after `jsr $1c59c` built the FX sound tables: `addq.l #8,a7 ; move.w #1,$2ec86.l` (10 B) become `jsr $7640c.l` + nops.  snd_setup (snd_core) does the Microwire setup (STE only), runs the two displaced instructions and returns with a7 as after the addq.
        org     $6de
        jsr     $7640c.l
