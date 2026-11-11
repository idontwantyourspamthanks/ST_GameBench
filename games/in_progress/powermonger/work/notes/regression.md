# Powermonger release regression (PMPack, 2026-11-10)

Tags: **[obs]** raw tool output (`/tmp/pmreg/*.log`, tool `tools/pmreg.py`; lines quoted); **[INFERENCE]** not run.
Hatari 2.6.1, headless. Every cell = a cold boot (`pm.py boot_to_game`: intro, name, options, chart, island, map view; it raises if the protection question shows) followed by the measurements.
Build under test: default patch set + `pm_credit` + `fal_ym` + the `core.s` cache fix, **without** triple buffering (p7_*). Release candidate `build/rc2` (the rc cells below ran on `build/rc`, = rc with fal_ym applied on every machine; after the Falcon gating and the core layout change only Falcon and STE floppy and HD STE were re-run, see the end): floppy md5 `3d116a3272af50ddc9d3a5bd39dc0a58`, HD `AUTO\WAR.PRG` `eb143fd0d92579f1fa58097de090161a`, `PMLATE.DAT` `44f44608244ab68a8879dcf2ce413a39`. Cells marked (a) ran on the earlier build `build/reg` (floppy md5 `2034757f0a116358e13799492b5e7e4a`: no cache fix, no `fal_ym`, no `pm_credit`), (b) on `build/cache` (= `build/rc` floppy, byte-identical; HD built before `fal_ym`). The lead re-runs a short regression after triple buffering.

## Method
`tools/pmreg.py --disk|--hd DIR [--acsi] [--saveload] --machine M --tos T --mem K [--mhz 8 16]`. Windows are 1000 VBL; emulated seconds = VBL / refresh (refresh from `$ff820a` bit 1: 50 Hz / 60 Hz); fps = flips of `$ff8201` per emulated second; world ticks/s = `$4bb3e` per emulated second (atomic samples, `pmtick.sample_at`); `cycles/VBL` proves the CPU clock. Sound: FLAGS bit0 plus how often `$ff8901` bit0 (DMA play) was set in 40 samples (plain ST: timer-A control `$fa19` and the player's busy flag `$2c993`). Tooltip: pointer away vs on the Get Men icon, pixels that change in the top-bar area (ST x 112..319, rows 0..5; screenshot geometry picked by width). Protection: pass flag `$14e4e = $2c` and no question box on the way to the map view.
Falcon cells need `--hopts "--borders false"` (screenshot 640x436 like the TT; with borders it is 718x600 and the harness gates never match).

## Results, patched (fps / world ticks per second)
| cell | build | boot | marker | map view | get_men | sound | tooltip | protection |
|---|---|---:|---|---|---|---|---|---|
| floppy ST 1.04 1 MB, 8 MHz, 50 Hz | rc | 147 s | PMPO, FLAGS 6 | 4.55 / 4.05 | 4.75 / 4.00 | YM: timer A running 40/40, busy 19/40 | 1184 px changed | skipped |
| floppy STE 1.62 1 MB, 8 MHz | rc | 149 s | PMPO, FLAGS 3 | 4.60 / 4.00 | 5.40 / 4.00 | DMA play seen 19/40, 24/40 | 1184 px | skipped |
| floppy STE 1.62 4 MB | (a) | 147 s | PMPO, FLAGS 3 | 4.60 / 4.00 | 5.35 / 3.95 | DMA 19/40, 21/40 | 1184 px | skipped |
| floppy Mega STE 2.06 4 MB, 60 Hz, 8 MHz | rc | 147 s | PMPO, FLAGS 3 | 4.62 / 4.02 | 5.52 / 4.02 | DMA 19/40, 39/40 | 1184 px | skipped |
| same, 16 MHz | rc | | | 9.84 / 3.96 | 11.88 / 4.02 | | | |
| floppy TT 3.06 4 MB, 32 MHz, 60 Hz | rc | 105 s | PMPO, FLAGS 3 | 19.80 / 4.02 | 19.80 / 4.02 | DMA 19/40, 33/40 | 1184 px | skipped |
| floppy Falcon 4.04 4 MB, 16 MHz, 50 Hz | rc | 125 s | PMPO, FLAGS 3 | 10.00 / 4.05 | 12.15 / 4.00 | DMA 19/40, 12/40 | 1184 px | skipped |
| HD real (ACSI + HDDRIVER) STE 1.62 1 MB | rc | 101 s | PMPO, FLAGS 3 | 4.60 / 4.00 | 5.35 / 4.00 | DMA 19/40, 25/40 | 1184 px | skipped |
| HD real Mega STE 2.06 4 MB, 8 / 16 MHz | rc | 123 s | PMPO, FLAGS 3 | 4.62 / 3.96 ; 9.90 / 4.02 | 5.52 / 3.96 ; 11.88 / 3.96 | DMA 19/40, 40/40 | 1184 px | skipped |
| HD real TT 3.06 4 MB | (b) | 62 s | PMPO, FLAGS 3 | 19.80 / 3.96 | 19.86 / 3.96 | DMA 19/40, 31/40 | 1184 px | skipped |
| HD Hatari GEMDOS STE 1.62 1 MB | (a) | 101 s | PMPO, FLAGS 3 | 4.60 / 4.00 | 5.30 / 4.00 | DMA 18/40, 23/40 | 1184 px | skipped |
| HD real Falcon 4.04 | rc | not booted | | | | | | **untestable** (below) |

Save and load through the game's own menu (`--saveload`, `pmpatch.run_saveload`): **0 bytes differ between the state saved and the state read back** (101376 B = 198 sectors), the state moved away in between (398-463 B differ), `SAVEDISK.DAT` slot A == the saved bytes, game keeps iterating:
* HD ACSI STE 1.62 1 MB (rc): `saved vs loaded: 0 differ; saved vs the state just before the load: 439 differ; SAVEDISK.DAT slot A == saved: True (409600 B)`
* HD ACSI Mega STE 2.06 4 MB (rc): `0 differ; 404 differ; True`
* HD ACSI TT 3.06 4 MB (b): `0 differ; 463 differ; True` (needs the TT screenshot offset in `pmpatch.find_btn`, added)
* HD GEMDOS STE (a): `0 differ; 436 differ; True`

World ticks: 3.95-4.05 per second in every cell (a 1000-VBL window holds 66-81 ticks, one tick = 0.015-0.06 error); 4.0 at 8, 16 and 32 MHz and at 50 and 60 Hz.

## Unpatched original, same harness (floppy, 8 MHz, 50 Hz)
| | map view fps / ticks | get_men fps / ticks |
|---|---|---|
| ST 1.04 1 MB | 2.30 / 2.50 | 3.45 / 3.90 |
| STE 1.62 1 MB | 2.80 / 3.55 | 3.45 / 3.85 |
Patched vs original: ST **+98% / +38%** (map view / get_men), STE **+64% / +57%** (the patched map view also runs its world at 4.00 instead of crawling at 2.5-3.5).

## TT and Falcon: what failed and why
* **Unpatched original floppy on TT 3.06: does not run** [obs `tools/pmdiag.py`: black screen, pc = `$e00d8c` (TOS `vsync` wait) for 225+ s; `--trace cpu_exception`: Line-F at pc `$672`]. Falcon 4.04: **does not run** [obs: double bus error dialog, `Bus Error reading at address $80808090, PC=$e0fbd2`, same Line-F at `$672` first].
* **Cause 1 (TT and Falcon): stale 68030 instruction cache** after the game's in-place depackers [obs: CACR = `$3111`; `r cacr=$0` at the stage-0 stub (`pc = $508`) lets the unpatched original reach stage 2 and our patched game reach the map view]. Fixed in the carrier: `core.s` `cacroff` (loading.md section 9). TT patched (rc): map view and get_men as in the table.
* **Cause 2 (Falcon only): YM mirror writes** `movep.l d6,0(a1)` -> `$ff8804/$ff8806` in the intro's sound interrupt (stage 1 `$b60c`): `Bus Error writing at address $ffff8804, PC=$b60c` [obs]. Fixed by `patches/fal_ym.s` (same register writes through `$ff8800/02`), applied ONLY on a Falcon (`; falcon: yes`, `_MCH` cookie). Applied on every machine it changed the ST intro music (WAV A/B rho 0.95, centroid 4137 vs 3436 Hz), so it was gated; with the gate the ST/STE A/B shows only load-timing noise (loading.md section 9). Falcon patched floppy: the table row.
* **I-cache back on in the game** (`ICMODE = 1`, TT, cold boot): the **name prompt is never reached** (`RuntimeError('name prompt not reached')`, `tt_icache.log`), so the instruction cache stays OFF (default). The cause was not investigated (a stale line from code the game writes, or the first draws after `$10a6`) [INFERENCE]. TT fps with every cache off: 19.80 (a flip every 3.03 VBL); not measured with the I-cache on. A static check found no executed code byte that differs between the load image and the three snapshots (map_idle, get_men, battle_320) [obs, 3196 executed instruction addresses from `work/prof2`], which proves nothing about code written between snapshots.
* **Falcon HD: untestable** [obs: `--acsi` on a Falcon is ignored by TOS 4.04, the machine sits in the TOS desktop; `name prompt not reached`]. Hunter's finding (HDDRIVER does not see Hatari's IDE) applies [`games/done/hunter/work/notes/ttfalcon.md` section 3, not re-run]. The patched game runs from the GEMDOS folder on STE; on a Falcon `tools/play.sh --hd` falls back to the GEMDOS folder [INFERENCE: not booted here].
* FDC time-out loops (Hunter's lesson): the same `move.l #$40000/#$60000,d0 ; btst #5,$fa01.w` loops exist (stage 1 `$57644 $576ea $5793c`, stage 2 `$db86 $dc2c $de7e`) but with the caches off the floppy boots on TT and Falcon in Hatari without touching them. On real hardware the cache-off 030 is slower, which also keeps them long enough [INFERENCE].

## Checks not run
Real hardware (all of it); Mega STE / TT / Falcon at 1 MB; TT or Falcon with TT-RAM; HD on plain ST (TOS 1.04) with the final core; the old (a) cells were not re-run on the final build for STE 4 MB (the changes since are the stage-1 YM site and `pm_credit`, boot paths exercised by the other cells).

## Re-run on `build/rc2` (fal_ym gated to the Falcon, core layout moved: HOOK1 `$B8140`, HOOK2 `$B8190`, APPLY `$B81F0`, TABLE `$B8250`)
Floppy md5 `3d116a3272af50ddc9d3a5bd39dc0a58`; HD `WAR.PRG` `eb143fd0d92579f1fa58097de090161a`, `SPRITE40.DAT` `37d28ff241b94d3f493f24e236e5a73b` (the stack routine's hook address changed), `PMLATE.DAT` unchanged.
* Falcon 4.04 floppy: PMPO, map view 10.00 fps / 4.00 ticks/s (`fal_ym` applied; `hook1` found the `_MCH` cookie).
* STE 1.62 floppy 1 MB: PMPO, 4.60 / 4.00 map view, 5.35 / 4.00 get_men.
* HD ACSI STE 1.62 1 MB: PMPO, 4.60 / 4.00, 5.30 / 4.00; save and load `0 differ; 430 differ; SAVEDISK.DAT slot A == saved: True`.
* Not re-run on rc2: ST, Mega STE, TT floppy, HD Mega STE / TT (same code paths as rc apart from the Falcon gate; the ST/STE intro WAV A/B above ran on rc2).

## Update 2026-11-10 (PMIntegrate)
The default set now also holds `p7_triple_*`, `qol_*`, `tick_rain` (instead of `tick_wx`), `tt_ptr` (TT + Falcon), `pm_intro_*`, `p4_clamp`. The per-machine table (cold boots, fps, pointer, key F, village hover, buffers) and every gate of the combined set are in `combined.md`; fps then: ST 4.65 / 4.85, STE 4.85 / 5.30, Mega STE 4.74 / 5.58 (8 MHz) and 10.20 / 12.48 (16 MHz), TT 22.62 / 27.12, Falcon 11.40 / 12.20, HD STE 4.85 / 5.30 (map view / get_men).
