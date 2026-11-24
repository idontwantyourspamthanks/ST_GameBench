# Moonshine Racers fixed tick: shipped patches `mt_clock`, `mt_sync`, `mt_pre` (T = 36, 1/300 s units)

Design and prototype evidence: `timing.md` (sections 1.5, 3, 4). Patches: `patches/mt_clock.s`, `mt_sync.s`, `mt_pre.s` (the tool allows one site per patch; the
three install together, all `default: yes`). Gate scripts and raw outputs: `work/tick/` (`mtlive.py` applies the tool's own `msrpatch.py live` image,
`exp_state.py`/`cmpstate.py` (no exclusions), `exp_tick.py`, `mksnap.py`, `run_speed.sh`, `run_boots.sh`, `play5.py`, `chk*.py`; `res_*.txt`).

## Splice sites (original bytes verified by `msrpatch.py verify` = ALL OK)
| patch | site | original | new | blob |
|---|---|---|---|---|
| mt_clock | `$d128` (`addq.b #1,$611b.l`, VBL ISR) | `52390000611b` | `jsr $b8000.l` | `$b8000` (replays the addq, clears PEND, CLK += 5, += 1 more if `$ffff820a` bit 1 = 50 Hz) |
| mt_sync  | `$7b74` (`jsr $d1e4.l`, end of race pass) | `4eb90000d1e4` | `jsr $b8100.l` | `$b8100` newsync: `jsr $d1ca`, PEND=1, `clr.b $611a`, sleep to NEXT, MAXLAG resync, NEXT += TICK |
| mt_pre   | `$7b0a` (`jsr $17c42.l`) | `4eb900017c42` | `jsr $b8200.l` | `$b8200` waits while PEND, `jmp $17c42` |
Data: CLK `$b8f00`, NEXT `$b8f04`, PEND `$b8f08` (declared as `; data:`, zero in the image). Payload 26,636 B (`$b2700-$b8f0b`). `$d1e4`, `$7b7a` raster copy untouched.
**Switch to T=30: in `patches/mt_sync.s` change `TICK equ 36` to `TICK equ 30`** (MAXLAG follows).
`$ffff820a` is read as a byte (present on ST/STE/TT/Falcon; no probe needed). The code is plain 68000; the tool's trampoline flushes 020+ caches after patching.

## Gates
1. `msrpatch.py verify`: ALL OK. `build --only pp_bigram_cache mt_clock mt_sync mt_pre --out build/mt_only` and the default build (`build/mt_default`) both built: "3 patch(es) + 1 file patch(es); payload 26636 B".
2. Per-pass state (`$1000-$13ff`, `$2c68-$34ff`, `$dae6`, at `$7b86`, keyed by `$100e`; stock vs patched, 8 MHz) `res_state_start.txt`, `res_state_drive.txt`:
```
race_start: A 160 passes, T 168; common passes 154; differing addresses: 0
race_drive: A 204 passes, T 205; common passes 198; differing addresses: 0
```
   `res_state_coverage.txt`: in race_drive both builds reach `$1226`=5 (time-out) at pass 1649 (A) / 1651 (T, the window starts earlier), the key then restarts, `$1030` 0 -> 1 at pass 55 after the restart in both.
3. Speed, `exp_tick.py` (CPU halted at both ends of a 600-VBL window) `res_speed_exp.txt`:
```
A start 8:  8.333 pass/s 6.000 VBL/pass pos 83.33/s     T start 8:  8.333 6.000 83.33
A start 16: 16.667 3.000 166.67                          T start 16: 8.333 6.000 83.33
A start 32: 16.667 3.000 166.67                          T start 32: 8.333 6.000 83.33
A grid 8: 9.833 5.085  | A grid 16/32: 16.667 3.000      T grid 8/16/32: 8.333 6.000 (pos 0)
```
   Race-clock high word per s: stock 1.333 (8 MHz) / 2.583 (16, 32); patched 1.333 (8) / 1.250 (16, 32): the high word of a long advanced by a constant step per pass is quantised in a 100-pass window (15 or 16 increments); the pass rate is identical, so the stopwatch is (the step per pass is identical by gate 2).
   60 Hz (`$ff820a`=`$fc`, Hatari switches to 60 Hz; rates per 60 Hz second) `res_speed_60hz.txt`: stock start 8.500 pass/s (7.059 VBL/pass), patched 8.300 (8 MHz) and 8.400 (32 MHz); stock grid 9.700, patched grid 8.300. Patched at 60 Hz = T/5 VBL (7.2) so about 8.33 pass/s per real second, machine-independent.
   `tools/msrbench.py` on patched snapshots (`mksnap.py` = stock snapshot + live patch, `res_msrbench.txt`; its `vbl_elapsed` span differs from the flip window, so use flips/fps): start 8/16/32 MHz fps 8.33/8.33/8.50 (flip window edge: 50-51 flips per 300 VBL), `$5ff8` 83.33/83.49/83.33 per s; grid 8.33/8.50/8.33. Stock same bench: 8.33/16.67/16.67 (start), 9.83/16.67/16.67 (grid).
4. Cold boots, default build (`msr_boot_test.py --game build/mt_default`, `res_boots.txt`): STE TOS 1.62 1 MB `in_race True` (vbl 5808), STE 1.62 4 MB True (5807), Mega STE 2.06 4 MB True (6046), ST 1.04 1 MB True (5809), TT 3.06 4 MB True (5877). `res_chk.txt`: marker `MSPO`, the three sites patched, CLK advancing.
   Note: `boot_to_race()` returns while the game is in PP's position-table screen (caller `$7496`, `res_chk3.txt`: flip return address on the stack `$d1f2`, then `$749a`); the race loop (`$7b74`) starts after one SPACE (`res_chk4.txt`: `$100e` reset to 7, 17 flips/100 VBL at `$7b74`). So the five boots prove staging, patch application and the clock, not the race pacer, and the pacer is gated by the snapshots and the 5-minute run.
   5 minutes of play, STE 1 MB cold boot + SPACE + `$6105`=1 held, 16,680 VBL (333 s) `res_play5.txt`: race at 8.3 pass/s (about 112 passes per 670 VBL), time-out (`$1226`=5 at `$100e`=1705, VBL 9972), restart (`$100e` 78 at the next sample), no crash, marker `MSPO`, CLK 0x1a3ee at the end.
5. Stock vs patched at 8 MHz (exp_tick, same scenes): driving 8.333 vs 8.333 pass/s (6.000 VBL/pass both), grid 9.833 vs 8.333. **With T = 36 the patched build runs at exactly 8.333 pass/s: the call-site pacing fix's +12 % driving gain (5.357 VBL of work, timing.md 1.4) is not visible at 8 MHz, it only appears when T is lowered (e.g. 30 once rendering is faster) and the grid is 15 % slower than stock (8.33 instead of 9.83 fps).** Faster machines drop from 16.67 to 8.33 pass/s by design.

## Unproven / risks
- Hatari only; no real ST/STE/TT/Falcon. Falcon not booted; `$ffff820a` bit 1 semantics on a Falcon VGA mode are `[INFERENCE]` (the register is ST-compatible: it holds what TOS/the game wrote).
- 60 Hz was tested by writing `$ff820a` in Hatari, not a native 60 Hz boot. T = 36 at 60 Hz alternates 7/8 VBL (about 0.8 % per-pass rate error, self-correcting via the accumulator).
- Overload: a scene needing more than T/300 s per pass just runs at its work rate (no sleep, no burst); T=30 at 8 MHz measured 9.33 pass/s (timing.md 4.2).
- The mt_* patches depend on each other (mt_sync/mt_pre need mt_clock's CLK/PEND); the tool has no dependency check: enable all three.
- Not tested: PP state-save inside the race, `$1027` > 1.
