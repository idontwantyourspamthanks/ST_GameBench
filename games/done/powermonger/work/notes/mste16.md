# Powermonger v1.2: Mega STE at 16 MHz (`pm_mste`, PMSixteen, 2026-11-19)

Tags: **[obs]** raw tool output (`/tmp/pm16/runs/*.out`, copied in part below; the run directories are not kept), **[INFERENCE]** not run. Hatari 2.6.1 only, private `HOME` (`/tmp/pm16/home`, every run additionally in its own `strun-*/home`), no real hardware, no MiSTer.

## 1. The problem and the register
* A Mega STE powers up at 8 MHz: `$FF8E21` (byte; word `$FF8E20`) reads 0. In Hatari 2.6.1 bit 1 = 16 MHz, bit 0 = the 16 KB cache (refused at 8 MHz: cache needs 16 MHz). Nothing in Powermonger, TOS 2.06 or HDDRIVER writes it (PMSpeed: `ff8e2` I/O trace over a whole boot); `--cpuclock 16` on Hatari's command line is ignored at boot (it only works as the `hatari-option` after boot).
* v1.1 on a Mega STE (the shipped floppy zip, 60 Hz, map view, 1000 VBL) [obs]: `RESULT mste_fl_v11 map view: sync $fc (60 Hz), fps 4.50 (75 flips / 1000 VBL), 1001 VBL = 16.7 s, 133581 cycles/VBL, world ticks 67 = 4.016/s, loop passes 67 = 4.02/s`, register `[('00', '00')]` at the end.

## 2. The patch (`patches/pm_mste.s`, default yes)
* An `init` routine (`; init: $dc200`, blob `$DC200..$DC247`, 72 B, `EXTRA_RANGES["pm_mste"] = [(0xDC200, 0xDC2FF)]`, the page after `pm_cachecap`'s, inside p6_'s range and the HD overlay window). `init` is core.s's supervisor start-up call (`front` -> `uinit` -> `Super(0)` -> `init`), common to the floppy and the HD build, before the game or stage 1 has run an instruction. **core.s itself is not touched**: its segment has only 10 bytes of room before `hook1`, and the free-RAM pattern gate (`$B8800..`) is not affected (`$DC200` < `$DD000`; the new `used` span is `$dc200-$dc248`).
* It writes `MSTEVAL` (constant in the patch, `3`) to `$FF8E21` iff ALL of: (1) the `_MCH` cookie's high word is 1 (STE hardware family: STE, Mega STE; ST 0, TT 2, Falcon 3; no cookie jar = old TOS = nothing written); (2) a bus-error-guarded byte read of `$FF8E21` answers (vector `$8` is pointed at a handler that resets the stack and returns; restored on both paths; an STE bus-errors there); (3) the byte reads 0. A non-zero value is left alone. The cookie test is an extra guard on top of the bus-error probe so that a TT / Falcon whose `$FF8E21` happens to answer is not touched.
* **0 is "not set yet".** An explicit 8 MHz without cache is also 0 and is raised to 16 MHz as well (lead decision). The user can keep a speed by setting it to anything non-zero before the game (e.g. 16 MHz without cache = 2), otherwise only the v1.1 zips give 8 MHz; there is no way back to 8 MHz while the game runs (the game takes the machine over: no desktop, no control panel).
* Bug found by the first build [obs]: the first version used `a2` freely; core.s's init loop keeps its table pointer in `a2` across the calls (the comment "may use every register" is wrong for `a2`; `hd_core` and `p4_spr` save theirs), so the game jumped to garbage and the machine returned to the desktop (`/tmp/strun-tmdd0hof/shots/grab0073.png`, `16MHz(CE)` in the status line). The routine now saves/restores everything it touches (`movem.l d0-d1/a0-a2`).

## 3. Value: `$02` or `$03` [obs, Mega STE TOS 2.06 4 MB, floppy, map view, 60 Hz]
| register value | cycles/VBL | fps | ticks/s | note |
|---|---:|---:|---:|---|
| 0 (v1.1) | 133581 | 4.50 | 4.016 | 8 MHz |
| `$02` 16 MHz, cache off (`mste_fl_c2.out`) | 267184 | 5.04 | 4.016 | +12 % only |
| `$03` 16 MHz + cache (v1.2 floppy) | 267186 | 8.16 | 4.016 | +81 % |
PMSpeed's 10.18 fps came from `hatari-option --cpuclock 16` (plain 16 MHz CPU, no bus wait states and no cache model). Hatari models the Mega STE's 16 KB cache cycle-exactly (manual: "8/16 MHz CPU speed and cycle accurate external 16 KB cache"): at 16 MHz without cache the RAM accesses wait for the 8 MHz bus, so the cycle counter doubles (the "~266K" gate passes with either value) but the game hardly speeds up. Lead decision B: write `$03`. The README says plainly that the cache is on and unproven on real hardware.
