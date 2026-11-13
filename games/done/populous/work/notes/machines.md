# Populous on TT, Falcon, 60 Hz and Mega STE (PopMachines, 2026-11-11)

Tags: observed = raw output in `work/gates/machines_*.txt` or quoted here; [INFERENCE] = not run. Harness (test scaffolding, not shipped): `work/scratch/machines/` (`pm_cells.py` cold-boot cell, `mm.py`, `nav.py`, `mkimg.py` one-game ACSI image, `dbg.py` Hatari with the debugger on stdin, `hwscan.py`). Hatari 2.6.1; TT = TOS 3.06, 4 MB, `--mmu true`, 32 MHz, VGA (as `dist/run_tt.sh`); Falcon = TOS 4.04, 4 MB, 16 MHz, VGA. Builds: `build/PopMachines/{floppy,floppy_f,hd,hd_f}`. Shots: `work/shots/{tt_floppy,falcon_floppy,ste60_hd_patched,megaste16_cache_patched,ste_hd_a,...}_{menu,play,busy}.png`.

## 1. Why `POPT`: the text base moves (TT and Falcon, and EmuTOS)
* GEMDOS trace (`--trace gemdos`), TT TOS 3.06: `Mshrink(0xE804, 0x2D6)` by our AUTO loader, `Pexec(3,"demo.tos")` -> base page `$EADE`, `_membot` (`$432`) = `$E6FC`. Text base = `$EBDE`, delta against `$AD96` = `$3E48`. The payload read `RELDLT` = `00 00 3e 48` ($B3104) in the cell.
* Falcon TOS 4.04: `Mshrink(0xFB6C, 0x2D6)`, `Pexec(0, "\AUTO\LOADER.PRG"...)`, game base page `$FEAC`, delta `$5216` (payload RELDLT, cell output `D = 21014`).
* TOS 1.62/2.06 leave `_membot` below `$A952`, so the loader's Mshrink steers the game to `$AD96`; TOS 3.06 / 4.04 own memory beyond it, so nothing can steer it there. The stock game does not care (it Mallocs its buffers, `$14b34`: `Malloc($fb00)`, and takes its clean background from Physbase `$aeb0`): it ran at `$EBDE` / `$FFAC` unpatched. Our patches do, because their sites and blobs hold absolute game addresses.
* Fix (built, `patches/core.s` + `tools/poppatch.py`, section "Other machines" of `patches/README.md`): automatic relocation. poppatch assembles every site/blob twice (second time with in-range literals shifted by `$10000`), lists the 32-bit fields that differ, and `apply` adds `p_tbase - $AD96` to them once. Orig bytes of sites are relocated from the program's own relocation table. `verify` prints the count per patch and fails on any other use of a game address (`pop_ptr`: 27 relocated longs in blobs, `pop_land_score` 33, `pop_credit` 1 + 2, `pop_bgcopy` 2, `pop_noprot` 0: all pass, `verify: ALL OK`).
* Observed after the change: TT floppy cell `payload header: 50 4f 50 50 50 4f 50 4f ... D = 15944`: `POPP POPO`, credit line visible on the TT menu (`work/shots/tt_floppy_menu.png`, DEMO blob + relocated `movea.l $12fa4.l`), `$ee16+D` branch applied (busy scene with the game's own poke removed would show armageddon; here `armageddon 0` throughout, the poke in my scene builder only writes the same byte again).
* `loader.s` still mentions `POPT` in a comment (the marker is no longer produced; `POPF` = a site's orig bytes differ).

## 2. TT (TOS 3.06, `--mmu true`)
Floppy build (`Populous_boot.st`, patches pop_noprot + pop_credit): `work/gates/machines_tt_floppy.txt`:
```
menu after 14.427664041519165
start page after 35.277995586395264
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 02 01 00  D = 15944
check_play (sig ok, turn, turn+2s): (True, 231, 387)
busy scene set up; turns:
  turn 931  npeeps 124  armageddon 0  (+153)
  turn 1118  npeeps 124  armageddon 0  (+340)
340 turns in 13.6 s wall
```
(`MACHV` = `01 02 01 00`: probed, class 2 = TT, CPU class 1 = 68030.) sig = `4eb9 + ($14a28+D)` at `$B6F4+D`, the main loop's `jsr $14a28`.
* **Speed**: 78 turns/s at 32 MHz on the empty start world (231 -> 387 in 2 s emulated), about 25 turns/s in the busy scene [wall seconds, includes debugger polls]; the stock STE does 3.2. The world is frame-coupled, so the TT runs the game 8x too fast: the tick work must apply there (it needs the relocation above).
* **Caches**: TOS 3.06 runs with CACR `$3111` (observed in a register dump); the game ran with them on in Hatari (030(CED)): no stale-code failure seen. Hatari's cache model is not proof for a real 030: [INFERENCE] DEMO/POPULOUS do not unpack or modify their own code (they are plain Pexec programs), but I did not scan for self-modification. `apply` flushes both caches after patching (`movec cacr`, ORed `$0808`), so patched bytes are not hidden by stale lines. The Powermonger "caches off" handling was not needed.
* **PMMU**: not used by the floppy build; the HD path (PP's HAGA) needs `--mmu true` (Midwinter note `tt.md`).
* **ST-RAM vs TT-RAM**: all 4 MB is ST-RAM; the payload and blobs stay at `$B3000-$C4xxx` in ST-RAM. `--ttram 8` was only tried with the stock HD image (it needs `--alert-level fatal`: Hatari raises an ERROR dialog "Automatically enabling 32-bit addressing" that blocks the fifo) and did not change its crash; floppy with TT-RAM not run.
* **Pointer** (Powermonger's `tt_ptr`): the pointer showed in `work/shots/tt_floppy_play.png`/`_busy.png`; Hatari's TT video follows `$ff8201/03` live (Powermonger `tt.md` section 2), Populous flips the buffers in `$16f16` and the VBL routine draws the pointer into the displayed buffer, so the same invisibility window is [INFERENCE] likely; not measured (no frame-by-frame pointer count taken). Open item, not fixed.
* **Video**: the game runs at ST low on the TT (picture 640x400 with the status bar below); no resolution fix was needed (DEMO sets it).
* **HD on the TT: not working, in the stock PP build, independent of our patches.** Stock `originals/POPULOUS` on an ACSI+HDDRIVER image (`mkimg.py`, `DESKTOP.INF` `#Z` autorun): HW screen, cover picture, then `Fopen("FILES\POLA")` `Fread(5000,$300100)`, `Fopen("D15RF.FIC")` `Fread(68000,$301488)` at PC `$3FAB74` (HAGA, `$3F8000`), `Fclose`, and the machine dies (Hatari "CPU halted: double bus error"). Exceptions (`--trace cpu_exception`): bus error writing `$fffffc3b` PC `$3e3866` (caught: PP's RTC read `$3e384c` probes the RP5C15 at `$fffc20` under its own bus-error handler, disassembled from the crash dump), then `Bus error reading at address $70004c PC=$7270004e` (A0 = `$7270004E` = code bytes `72 70 00 4e`), vector 2 in PP's game-world low RAM is `$023E24A2`, so the handler itself faults. Same with `--mmu false`, with `--ttram 8`, with a GEMDOS drive instead of ACSI (also on the Falcon: `Bus Error reading at address $b40042, PC=$3e6a2e`). Midwinter 2's stock files on the same Hatari TT/ACSI setup run (`Fopen("FFA")`, `Fread(737280,$300100)` ... no crash within 70 s), so it is Populous-specific (`D15RF.FIC`, the Falcon/TT variant PP picks for 030 machines, vs `D15RH.FIC`). Cause not found; I stopped at the RTC probe / garbage-A0 point. Consequence: our HD build (same RUNME/HAGA/POLA code) cannot be verified on a Hatari TT or Falcon. The delivery path of the HD build on those machines is [INFERENCE] equal to the floppy one (same `apply`), but also needs PP's HAGA to survive, which it does not here.

## 3. Falcon (TOS 4.04)
* DEMO.TOS and the game both bus-error on the YM mirror. Raw log of the unpatched floppy (`Hatari log`): `Bus Error writing at address $ffff8804, PC=$121ae` (DEMO: `$cf98 + $5216`) and later `PC=$1c3be` (game: `$171a8 + $5216`). The DEMO dies before its menu; the loader goes on to the game with command-line digit `/`; the game dies at its first sound effect (cell `--nomenu --sound`: `check_play (False, 1033, 1033)`, turn counter frozen, TOS default palette back on screen: `work/shots/falcon_noym_play.png`).
* Code (`work/scratch/machines/demo.bin` + `m68dis`): `cf96: suba.l a0,a0 / cf98: movep.l d1,-$7800(a0) / cf9c: movep.w d2,-$7800(a0)`, same in the game at `$171a6-$171ac` (timer-A sample interrupt, `move.l #$1717e,$134` at `$17058`). The movep.l writes `$ff8800,02,04,06`.
* Patches `pop_fal_ym_demo` (`$cf98`) and `pop_fal_ym` (`$171a8`), `; default: no`, `; machine: falcon`; blobs `$C4000` / `$C4040`: `swap d1 / movep.w d1 / swap d1 / movep.w d1 / movep.w d2 / rts`, same register writes in the same order through `$ff8800/02`.
* Other ST-only hardware (scan of both programs, `hwscan.py`, capstone linear sweep of the text, `hwscan.txt`): the only `movep` that is real code in either program is that pair (the other 406 hits are data decoded as code). Absolute hardware operands in the programs: video base `$ffff8200`, resolution `$ffff8260` (DEMO `$cd90`), YM `$ff8800/02` (plain), MFP `$fffa..`, ACIA `$fffc00/02`, DMA/FDC `$ff8604/0b` in the game at `$162b2-$16468`, `$17cba-$17e70` (own FDC routines; not reached in the HD or the Pexec/GEMDOS flows seen). Nothing else faulted in 130 s of play.
* Falcon cell (`machines_falcon_floppy.txt`): `POPO`, `D = 21014`, `MACHV 01 03 01 00` (class 3 = Falcon, 030), busy scene 320 turns, `armageddon 0`; `sound check: 41342 log line(s) mentioning $c4040 after the earthquake command; bus errors in log: 0` (the earthquake effect ran the blob thousands of times, no bus error). Menu shot `falcon_floppy_menu.png`, `_play.png`, `_busy.png`.
* Falcon runs the game 42 turns/s (16 MHz 030, empty start world: 85 turns in 2 s emulated).
* Hatari artefact seen in a screenshot only: while POPULOUS loads, the palette is TOS's default until the game sets its own; not a defect (a screenshot taken too early looked "wrong").
* Falcon HD: Hatari's Falcon cannot mount the ACSI image (no ACSI; HDDRIVER finds no drive: `run_falcon.sh`, Hunter `ttfalcon.md`); stock PP via a GEMDOS drive crashes as on the TT (above). Not verified. `pop_fal_ym*` also apply in the HD build (same payload).
* Real Falcon [INFERENCE]: the YM decode behaviour is Hatari's; Powermonger's `fal_ym` uses the same fix.

## 4. STE gating (the new sites and the new core do not change an STE)
* New core vs the old one (HEAD, built from `git show` into `/tmp/oldpop`), STE 1 MB TOS 1.62 HD build, cold boots, text region `$AD96..$214A1` dumped in play (`work/gates/machines_ste_text_compare.txt`):
```
STE 1 MB HD, old core (HEAD) vs new core: text bytes 0xad96..0x214a1 differing: 2 at ['0x16d2d', '0x16f14']
STE 1 MB HD, new core vs new core + pop_fal_ym_demo + pop_fal_ym: text bytes 0xad96..0x214a1 differing: 3 at ['0x16d29', '0x16d2d', '0x16f14']
0x171a8 old 03c8880005888800 new 03c8880005888800 new+fal 03c8880005888800
0xcf98 old 600000a2302e0008 new 600000a2302e0008 new+fal 600000a2302e0008
```
`$16d28-$16d2d` (VBL flag + counter) and `$16f13-5` are run-time words (`RUNTIME_TEXT` plus the flag word `$16d28`); the Falcon sites keep the original bytes on the STE (`$cf98` is a different location in DEMO, whose RAM is gone when the game runs, so the line shows game data). The new-core STE cell shows `payload header ... 00 00 00 03 01 00 00 00` = `RELDLT 0`, machine class 1.
* Mechanism: delta 0 -> no relocation write; `; machine: falcon` sites are not verified or applied on class 1.
* The payload image itself differs (meta words, pool alignment, core2) but only inside `$B3000-$C4FFF`.

## 5. 60 Hz (an STE with TOS 2.06 US)
* `$ff820a` on `--machine ste` TOS 2.06: `00 00` (60 Hz); TOS 1.62: `02 00` (50 Hz) (`work/gates/machines_ste60_syncmode.txt`).
* Patched HD build, 1 MB: `machines_ste60_patched.txt`: `POPO`, `D = 0`, play, busy scene 302 turns, `armageddon 0`, 110 peeps. Stock (`originals/POPULOUS`, no payload): `machines_ste60_stock.txt`: play, 303 turns, 99 peeps (the scene builder pokes `$ee16` itself, so armageddon is 0 here too; the stock game's protection trap is not tested by this cell). Both reach the START page, play, and look normal (`work/shots/ste60_hd_patched_*.png`, `ste60_hd_stock_*.png`).
* Note only: the world is VBL-paced, so 60 Hz runs it 20% faster than 50 Hz [INFERENCE from `baseline.md`: not measured in emulated time]; PP's intro delays and the DEMO attract timeout are VBL/CPU-count based. The tick patch must read `$ff820a` bit 1 like Powermonger's `tick_head`.

## 6. Mega STE 16 MHz, cache on
* `--cpuclock 16` set after boot (a command-line option crashes TOS 2.06's boot, `delivery.md`), then `w $ff8e21 $03` in the debugger (before: `ff`, after: `03`, bit 0 = 16 MHz, bit 1 = cache) at the PP hardware screen. Output `machines_megaste16_cache_patched.txt`: `POPO`, `D = 0`, busy scene 313 turns, `armageddon 0`. Whether Hatari models the Mega STE cache at all is [INFERENCE: not checked]; on a real Mega STE the cache does not see DMA writes, but the HD flows read with HAGA through TOS before the game runs and the game does no DMA. Quick check only; no save/load.

## 7. Not done / open
* HD on TT and Falcon (stock PP crashes in Hatari; cause not found; see section 2).
* Pointer on TT/Falcon (Powermonger `tt_ptr` analogue): not measured, not patched.
* Free-RAM pattern test on TT/Falcon: the floppy loader reserves `$B3000..` with Mshrink/Malloc for any base (observed `POPO` on both), so the payload is safe there by construction; HD and TT-RAM not covered.
* Real 030 cache behaviour, real Falcon YM decode, real Mega STE cache: not testable here.
* Other agents' patches (`pop_ptr`, `pop_bgcopy`, `pop_land_*`) were relocation-checked by `verify` only; none was booted on TT/Falcon.
* `pp_nofade` and the Falcon patches stay `; default: no`: the lead flips them. A Falcon release needs both `pop_fal_ym*` in the build (`poppatch build --floppy --only ... pop_fal_ym_demo pop_fal_ym`).
