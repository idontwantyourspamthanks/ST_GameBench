# STE / Mega STE: "music plays, no disk activity" in v1.5/v1.6 - cause and fix (2026-11-20)

Follow-up of `realfloppy.md` / `realfloppy_v16.md`. The downloader's v1.6 on a real STE and a real Mega STE (any TOS: 1.04/1.62/2.06 loaders): after the logo the Amiga music plays but the
drive never does anything (no light, no motor, no freeze); on his Mega ST (original TOS) v1.6 boots to the normal disk-change screen and works. All Hatari gates (`--sound off`, see
`tools/mw2harness.py`) passed. Labels: **[MEASURED]** raw lines in `work/stesound/out/` (traces in `/tmp/mw2s/` are RAM), **[SOURCE]** read in code/disassembly, **[RULE]** hardware rule from the
YM2149 data sheet (not measurable here), **[INFERENCE]** not proven. Nothing here ran on a real machine.

## 1. Sound emulation is not the difference [MEASURED]
Hatari 2.6.1-devel, `--sound 50066` (DMA sound + YM mixed), shipped v1.6 FFA..FFD from `dist/Midwinter2_v1.6_patched_floppies_2026-11-19.zip`, 1 drive, `--fastfdc no`, boot -> orange prompt ->
FFB swap -> key (`work/stesound/swapgate.py`, scenario B): STE TOS 1.62 1 MB / 2 MB / 4 MB, Mega STE TOS 2.06 8 and 16 MHz, Mega ST TOS 1.04: all `M/J/K screen REACHED`, 0 force interrupts
(`out/*.txt`). Sound off: same. The Amiga mixer, Microwire, DMA start/stop, the PSG reads in `asn_ymsilence` etc. all run in Hatari without any effect on the FDC.

## 2. Cause [MEASURED trace + SOURCE + RULE]
* PSG register 7 (mixer / I/O control): bits 0-5 = tone/noise disable, **bit 6 = port A direction, bit 7 = port B direction, 0 = INPUT** [RULE]. Port A (reg 14) carries the floppy **drive-select
  (bits 1-2) and side (bit 0)** lines. With bit 6 = 0 the YM does not drive those pins: the game's select (`sub_027cfc`, `$27d12`: `move.b #14,$ff8800 / read / andi #$f8 / or / move.b d7,$ff8802`
  under sr=$2700) changes only the output latch, the drive stays deselected: no light, no motor spin-up, every FDC command runs without a drive [INFERENCE for the physical effect on his machines;
  RULE for the direction semantics].
* Hatari does **not** model it: `src/psg.c` stores `PSGRegisters[14]` and calls `FDC_SetDriveSide` whatever reg 7 holds. So no Hatari gate could ever fail on it.
* Who writes reg 7 [MEASURED, `--trace fdc,psg_write`, STE 1.62, shipped v1.6, `work/stesound/psgcheck.py`]: TOS reset `$c0`; the YM tick (`$101c`) always `$f8/$dc/$d8/$c8/...` (bits 6+7 set);
  the game's sound init `$33870` -> `sub_0338ce` (`movep.w` pairs from the register shadow `$682c-$685f`, which `$33870` has just zeroed) writes **reg 7 := 0 at pc `$33930`**; `$c4c` (silence, called by
  `$c6c` = `asn_mstart`'s park) writes 0 to reg 7 and then `$ff` (60 us window).
```
line 160001: reg 7 bits 6+7 $c0 -> $00 (reg 7 := $00) at pc=33930        (sound init, cold start)
line 160095: reg 7 bits 6+7 $00 -> $c0 (reg 7 := $ff) at pc=c64          (asn_mstart parks the YM driver: $c6c -> $c4c)
line 160127: reg 7 bits 6+7 $c0 -> $00 (reg 7 := $00) at pc=33930        (sound init again: $33870 runs at every music start)
  15 x reg-14 write with port A/B not both output; first: line 160155 ... pc=27d26
  215 x game FDC command with port A/B not both output; first: line 160161 r7=$00 fdc type I restore ... (the game's FIRST command)
  FRAMES with reg 7 bits 6/7 not both set at the frame start: 283 of 1492 (longest run 283)
PSGCHECK g_v16_ste: FAIL
```
  In the original game (YM tick = `$5138` from the music start on) the next VBL rewrites reg 7 with bits 6+7 set; with the Amiga sound (STE / Mega STE only: `asn_mtick` / `asn_tick` own `$5138`, the YM tick
  never runs again) nothing does. Reg 7 stays 0 from the second `$33870` (VBL 3296) on, **including the game's first disk check** (first game FDC command VBL 3299): on real hardware that check fails
  silently, the game shows its black "Insert Graphics Disk / press any key" prompt (the failed-check path of `realfloppy.md` 0), the music plays on, FFB can never be accepted, nothing is ever selected: exactly the report.
  ST / Mega ST / TT (asn inactive: YM tick runs) keep working, which is why the Mega ST worked.
* The v1.4 report (no Amiga code at all) had its own cause (head position / FDC time-out, `realfloppy.md`, fixed in v1.6); this one exists only since v1.5 (`asn_*`). The v1.6 gates could not see it.
* `asn_ymsilence` (3D view, effects session start) made it permanent there too: read-modify-write of reg 7 with `ori.b #$3f` keeps a bit 6 that is already 0.

## 3. Reentrancy / other hypotheses checked [SOURCE unless noted]
1. **PSG select-latch interleaving: not possible at the game's reg-14 accesses.** The only main-code reg-14 RMWs (`$27d12` game, `$4de4a` boot stub) run at `move.w #$2700,sr`; the YM tick writes with
   `movep.w` pairs (select + data in ONE instruction). The new VBL-side write of reg 7 (`move.b #7,$ff8800 / move.b #$ff,$ff8802`) cannot split the driver's select/write (VBL cannot run at sr=$2700);
   it leaves the latch at reg 7 (the original tick left it at 13); every game/stub access selects its own register first. The unmasked non-atomic pair in `$c4c` (`move.b d0,$8800.w / move.b #0,$8802.w`)
   could in principle take the VBL write between its two stores (data lands in reg 7 = 0): the same window existed with the original YM tick (data into another register) and is repaired by the next VBL's `$ff`.
2. **Reg 7 read-back** (`asn_ymsilence`): replaced by an absolute `$ff`; no code of the fix reads the PSG back.
3. Microwire waits, DMA start/stop vs the FDC DMA, MFP/GPIP: nothing in `asn/blob.s` touches `$ff8604/06/0e`, GPIP or MFP registers (grep of every `$ff8xxx/$fffaxx` in the blob: `$ff8800/02` (ymsilence + fix),
   `$ff8901/09/0b/0d/0f.../21` (sound DMA), `$ff8922/24` (Microwire, bus-error guarded, 1000-round wait), `$ff820a` (50/60 Hz)). The FDC wait polls GPIP bit 5 only. Not shown to matter; Hatari-lenient items remain
   [INFERENCE]: real sound-DMA/FDC-DMA bus contention, Microwire reset state.
4. RAM size (2/4 MB STE/Mega STE vs 1 MB Mega ST) as a difference: ruled out in Hatari (STE 2 MB, 4 MB reach M/J/K).

## 4. Fix (released as v1.6.1)
| What | Where | Effect |
|---|---|---|
| `asn_mixer` writes PSG reg 7 := `$ff` (absolute) at its start | `patches/asn/blob.s` | every VBL while an Amiga tick owns `$5138` (DMA tune or effects session): bits 6+7 set, tones/noise off |
| `asn_ymsilence` writes reg 7 := `$ff` (absolute, no read-back) | `patches/asn/blob.s` | the effects session start no longer preserves a 0 bit 6 |
| `ym_porta`: `$3392c` `move.b $14(a3),d0` (`102b0014`) -> `move.b #$c0,d0` (`103c00c0`) | `patches/ym_porta.s` (boot, 4 B, all media) | the game's sound init writes `$c0` (bits 6+7 set; tone/noise enabled but the amplitudes 8-10 are written 0 right after: silent, same as before) instead of 0: no window at all; also on ST/Mega ST/TT, where the next YM tick overwrites reg 7 as before |
When the YM driver plays a tune (not in the bank, plain ST/TT) reg 7 stays the driver's. Cost: 2 stores per VBL (~36 cycles).

## 5. Gates (sound ON, `--sound 50066`; `work/stesound/run_gates.sh`)
`psgcheck.py` replays `--trace fdc,psg_write`: at every game FDC command and every reg-14 write reg 7 & `$c0` must be `$c0`; frames starting with a bad reg 7 are counted. Negative control: shipped v1.6 FAILS.
Gate of record: **`work/stesound/psgcheck.py`** (this project's). The shared `tools/psgcheck.py` (PSGGuard, unreviewed) is a second implementation; both were run on the same two traces (STE 1.62 8 MHz, 1 drive, boot + FFB swap, sound on): shipped v1.6 `PSGCHECK FAIL` in both (mine: 215 game FDC cmds + 15 reg-14 writes with port A/B input; shared: 230 violations), candidate `PASS` in both (0 / 0). The cell/swap/boot results quoted below used mine for the swap gate and boot gate and, in the cells, whichever `psgcheck` the cell script imported first (the shared one: its summary line has "violations/warnings"); both agree.

## 6. Results (all with `--sound 50066` and `--trace fdc,psg_write`; raw lines in `work/stesound/out/p2_*.log`, `pc2_*`, `fl_*`, `ym_*`)
Candidate = the floppy build of the tree with the fix (FFA md5 `3c9d67db94f7eefcf5be232ff4df9166` at the time; the release build adds only the 1.6.1 logo string).
* **Sound on does not reproduce the failure** with shipped v1.6 (section 1) - the PSG gate is what sees it.
* **Fix-invariant gate (boot + first check + FFB swap)**: STE 8 MHz PASS (0 of 1548 frames start with reg 7 bits 6/7 clear), Mega STE 16 MHz PASS (0/1980), Mega STE 8 MHz PASS (re-run, 0/1821), `$3392c` = `103c00c0` in RAM in all. **Negative control shipped v1.6**: STE FAIL (15 reg-14 writes, 215 of 215 game FDC cmds, 279/1482 bad frames, `$3392c` = `102b0014`), Mega STE FAIL (353/1752 bad frames).
* **Gate a (first restore)** STE 8, Mega STE 8, Mega STE 16: all PASS (parked, completed, 0 cuts) + PSG PASS.
* **Gate c (swaps)**: 1 drive A+B, 1 drive empty C+CB (first C run: key lost by the harness, "black prompt NOT up", CB then reached M/J/K, PSG PASS), 2 drives A+B, drive-B-holds-FFB D: all reach M/J/K, 0 force-ints, PSG PASS.
* **Gate b (full cells to the 3D view, `cell16.py`)**: STE 8 MHz 1 drive and 2 drives PASS, Mega STE 8 MHz 1 drive PASS, Mega STE 16 MHz 2 drives PASS, Mega STE 16 MHz 1 drive PASS on re-run (first run: harness `EXC OSError(6)` = Hatari fifo error, game side PSG PASS, 0 cuts), Mega ST (TOS 1.04) PASS on re-run (first run `never reached the boss screen`, harness navigation, game side PSG PASS 0 cuts; **shipped v1.6 with sound on, same cell: PASS twice**, so that failure is harness/flake, not the patch: 1 of 4 candidate runs), TT (TOS 3.06, 4 MB) PASS. All: first restore parked, 0 cut game commands, `$3392c` = `103c00c0`.
* **Mega STE 8 MHz boot hang**: 1 of 8 cold boots (candidate, first run of the group) stalled in the boot loader reading sector 6 of track 0 (0 game FDC cmds; FFA sectors 0-17, boot sector + stub, are byte-identical to v1.6). Re-runs: candidate 1 swap run + 3 boot runs clean, shipped v1.6 3 boot runs clean. Not reproduced: Hatari timing flake [INFERENCE], not shown to be pre-existing.
* **YM A/B on YM-only machines** (`ymab.py` + `ymdiff.py`: `--trace psg_write`, v1.6 vs candidate, cold boot to the orange prompt; sound registers 0-13 compared in order from the game's sound init `$338ea`): Mega ST TOS 1.04: 13625 writes compared, **0 differ except the two reg-7 init writes `$00` (v1.6) vs `$c0` (candidate) at pc `$33930`** = identical audio. TT TOS 3.06: 23479 compared, the two init writes as above plus **2 YM-tick writes of reg 7 that differ in bit 4 only** (`$c4` vs `$d4`, `$cc` vs `$dc`, pc `$1020`: the tick's own mixer value; not the init; run-to-run tune/timing variation [INFERENCE, not verified by a second v1.6 run]). The boot stub's tune before the init is not comparable run to run (different phase), so the comparison starts at the init.
* `$c4c`/`$c6c` in-flight check: the FDC driver is synchronous (GPIP polling, no FDC interrupts); the music start `$321fe`/`$c6c` is main-loop code; the one VBL-context caller is the fade end `$322d6` -> `$80e` = `$c4c`, unchanged from the original game (reg 7 := 0 for ~60 us, then `$ff`).
* Unit gates: `tools/asn_test.py unit`, `tools/asn_mus_test.py unit` ALL OK with the new blob; `mw2patch.py verify` ALL OK.
* Not proven: that the real chip's port-A tri-state is what the real machines showed (the tester's STEs now work with the fix); the TT, Falcon and plain ST hardware behaviour; the Mega STE real hardware (reported only "STEs").
