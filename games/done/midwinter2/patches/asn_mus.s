; name: asn_mus
; default: yes
; site: $806
; orig: 00000d0e00000c6c
; phase: boot
; note: The Amiga MUSIC on the STE's DMA sound (work/notes/amiga_music_port.md).  Apply with asn_wd (the watchdog that stops the ring when the tick
; note: is parked) and the bank file (tools/asn_build.py); the sound effects of the same blob are asn_core / asn_lvc / asn_lv1 / asn_lv2.
; note: THIS FILE IS ONLY THE SITE: two longs of the YM music driver's vector table (FFA file 8, `$806`: tick `$d0e`, `$80a`: start `$c6c`).
; note: Every caller goes through that table (`lea $806.w,a0 / movea.l N(a0),a1 / jsr (a1)`; the game copies `[$806]` into its VBL tick pointer
; note: `$5138` at `$3225c`), so the two longs redirect the music of every screen to patches/asn/blob.s: asn_mtick (+$1e) and asn_mstart (+$24).
; note: `$80e` (silence, `$c4c`) stays: the YM chip is silent anyway while a DMA tune plays, and the tick honours the attenuation byte `$b9a`
; note: (0 loud .. `$f` mute, written by the game's fades and the music on/off key) and the once flag `$ba2` itself.
; note: Plain ST / Mega ST (no DMA sound), a 68020+ (TT / Falcon), a missing bank, or a tune that is not in the bank: both entries `jmp` to the
; note: original routines and the YM driver plays, untouched (cost: one jmp + three tests per VBL).
; note: STE / Mega STE: start (tune number in `$b96`) parks the YM driver on its silent tune 0 and sets up a port of the Amiga player
; note: (`MWII` `$5760c` / `$57720`: 4 channels of pattern lists, notes = period + duration in 50 Hz ticks, instruments with a one-shot or a looped
; note: sample, volume envelopes, slide, vibrato); its Paula registers feed the blob's mixer at 12517 Hz mono (ring of 2048 B, 640 samples ahead).
; note: PSG reg 7 (v1.6.1): the music tick never runs the YM tick, so asn_mixer (every VBL of a DMA tune) writes reg 7 := $ff absolute: bits 6+7 = I/O ports A/B OUTPUT; port A carries the
; note: floppy drive select, and the game's sound init `$33870` writes reg 7 := 0 (see asn_core, ym_porta, work/notes/stesound.md).
        org     $806
        dc.l    $bf81e,$bf824
