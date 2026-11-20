; name: ym_porta
; default: yes
; site: $3392c
; orig: 102b0014
; phase: boot
; note: The game's sound init `$33870` (cold start `$26656: jsr $5032`, every music stop/start, the 3D view's `$338c2`) clears the YM driver's register shadow `$682c-$685f` and
;       writes ALL of it to the chip (`sub_0338ce`, `movep.w` pairs): PSG reg 7 (mixer / I/O control) gets the shadow byte `$14(a3)` = 0.  Reg 7 bit 6 = port A DIRECTION, 0 = INPUT:
;       with port A an input the real YM2149 does not drive reg 14 = the floppy drive-select (bits 1-2) and side (bit 0) lines, so the FDC driver's select (`$27d12`) has no effect on the
;       drive: no drive selected, no light, no motor, no disk activity (Hatari does NOT model the direction bit: every Hatari gate passed).  The original game hides it because its YM tick
;       (`$d0e`) rewrites reg 7 every VBL with bits 6+7 set (`$f8`, `$dc`, ...); with the Amiga sound (asn_*) the YM tick does not run on an STE / Mega STE (real-floppy v1.5/v1.6 report:
;       "music plays, no disk activity"; work/notes/stesound.md), so asn_mixer writes `$ff` to reg 7 every VBL.  This patch closes the window left by the init itself: it writes `$c0`
;       (tone and noise channels enabled, ports A+B output; the amplitudes 8-10 are written 0 right after, so the chip stays silent) instead of the shadow's 0.  4 bytes; the next YM tick
;       (ST, TT, a tune that is not in the Amiga bank) still overwrites reg 7 as before.
        org     $3392c
        move.b  #$c0,d0
