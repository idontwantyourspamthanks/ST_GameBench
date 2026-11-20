; name: asn_core
; default: yes
; site: $18f92
; orig: 303868626b0a
; phase: deferred
; note: Amiga sound effects on the STE's DMA sound (work/notes/amiga_sound.md).  Apply with asn_wd, asn_lvc, asn_lv1, asn_lv2 and the bank file (tools/asn_build.py).
; note: THIS FILE IS ONLY THE SITE.  The code is patches/asn/blob.s (not a patch: no `; site:`), assembled by tools/asn_build.py into the bank file
; note: `build/asn_bank.bin` (RAM $BF800, fixed entry jumps at its start; the bank is loaded to $BB000: HD by a RUNME splice from FILES\ASNBANK.BIN,
; note: floppy as part of FFA file 10).  Without the bank the sites would jump into zeros: always build the group with the bank (MW2_BANK=...).
; note: SITE = the ST in-game sound tick `$18f92` (overlay FFB f1, `$18d96-$210b2`; the VBL handler `$26298` calls it through the hook `$5138`):
; note: `move.w $6862.w,d0 / bmi.b $18fa2` (6 B) becomes `jmp asn_tick.l`.  Plain ST / Mega ST (no DMA sound), a 68020+ (TT/Falcon) or a missing bank:
; note: the displaced two instructions are replayed and the original tick runs unchanged (YM plays; cost: one jmp + two tests).
; note: STE / Mega STE: the YM tick is NOT run.  The game's request words keep their meaning (`$6862` = sound id*6, `$686c` = the sustained sound
; note: re-requested when every voice is idle, `$19218` = engine level); this blob is a port of the AMIGA driver ($2f3b2 tick, $2f28c start,
; note: $2f2f2 kill, $2f46c voice, $2f4fa step, $2f5b0 stop): same sound rows / sequence table / effect records (from the bank), four voices,
; note: and writes its "Paula" registers (volume, period, sample, length) to a software mixer instead of AUDx: 6258 Hz mono ring of 2048 B in a
; note: looped DMA frame, nearest-neighbour stepping (inc = PAL clock / period / 6258 Hz), volume tables (16 levels, two gain sets).
; note: Driver ticks are 50 Hz (60 Hz VBL: 5 of 6); the mixer tops the ring up to TARGET samples ahead of the DMA position every VBL.
; note: Everything runs inside the VBL (no timer, no new interrupt).  asn_wd (boot site $262c2) stops the DMA when the tick no longer runs.
; note: The same blob, mixer and ring play the Amiga MUSIC (asn_mus; work/notes/amiga_music_port.md): the game's tick pointer is
; note: either this sound-effect tick or the music tick, never both.
; note: PSG reg 7 (v1.6.1): while this tick (or asn_mus's) owns `$5138` the YM tick does not run, and the YM tick was what rewrote reg 7 with bits 6+7 set every VBL.  Bit 6 = port A
; note: DIRECTION = the floppy drive-select / side lines: with it 0 the real chip never selects a drive (Hatari does not model it).  asn_mixer therefore writes reg 7 := $ff (ABSOLUTE, no
; note: read-back: a read-back cannot be tested in Hatari) every VBL, asn_ymsilence writes $ff too, and ym_porta makes the game's init write $c0 instead of 0.  work/notes/stesound.md.
        org     $18f92
        jmp     $bf800.l
