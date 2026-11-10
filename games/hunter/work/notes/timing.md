# Hunter 50/60 Hz: the world runs on world ticks, not on VBLs (HunterHz)

Tags: **[obs]** observed in Hatari 2.6.1 (raw output below, tool `tools/hunthz.py`, `tools/snd_test.py`); **[disasm]** read from `tools/m68dis.py` on `work/dumps/ram_foot_walk.bin`; **[calc]** computed from 68000 timings, not measured.
Files: `patches/hn_hz.s` (default yes, site `$c63c`, blob `$8da00`, state `$8dbf0`), `patches/snd_core.s` (reads `HZ_SKIP = $8dbf2`), `patches/test_hznop.s` (timing control, default no), `tools/hunthz.py` (gates a, b, d + driver tick count), `tools/snd_test.py` (`ring`, `dur`, `--live`, `--hz`).
Precedent: `games/powermonger/work/notes/timing.md` section 11, `games/midwinter/work/notes/timing.md` section 10 (units of 1/300 s: +6 per 50 Hz VBL, +5 per 60 Hz VBL, mode from `$ff820a` bit 1).

## 1. Inventory: what advances per VBL [disasm]

Everything time-like in Hunter comes from the VBL handler `$c5f0` (vector `$70`). Nothing reads `$4ba`/`$462`/`$466` or an MFP timer (baseline.md), and the game switches TOS's 200 Hz timer C interrupt off (`movep.l d0,$7a01(a6)` ... at `$a9da..$a9e2` clears IERA/IERB/IMR) [disasm]. The handler runs:

| Part of the handler | What it does | Class | Handled by |
|---|---|---|---|
| `$c6a4` (LFSR `$1c6(a5)`) | random numbers, one step per VBL | consumed per use, not a clock | unchanged (per real VBL) |
| `$c63c..$c664` 3D-loop block, only while `$93` bit 7 (3D loop) is set: | | | |
| `$1a8(a5)` (`$9ae`) += 1 | absolute tick counter; compared with the schedule at `$5f7e` (scripted mode) | **world** | gated |
| `$1aa(a5)` += 1 | VBLs since the last frame; the frame loop copies it to `$1ac` at `$5fa4` | **world**: elapsed time of the frame | gated |
| `$1ac(a5)` readers | movement of the player and of every object: `mulu.w $1ac(a5)` at `$2acc $2af0 $2b52 $2b60 $2bd2`, `muls.w` at `$2bde` (position += speed x ticks, gravity), object timers `sub.w d0,$30(a4)` at `$2738`, `sub.b d0,$2e(a4)` at `$2770`, `$34(a4)` at `$2a5c`, byte `$1ad(a5)` at `$2938 $2950` | **world** | follow `$1aa` |
| `$d1 -> $d0`, `$cf` | joystick state copy and fire edge | input sampled per tick | gated |
| `$c6b4` | scripted-mode (intro/demo) schedule: byte countdown per VBL, `$c8(a5)` list | **world** (demo timing) | gated |
| `$699c` | countdown timers `$232` (16-VBL animation tick, calls `$6a50`), `$234`, `$186`, `$184`, `$188` (cooldowns, mission timeout `$2638`) | **world** | gated |
| `$355a` | camera pitch/step ease (`$1530/$1536`), turn/accelerate ramp `$2a0(a5)` (+-1 per VBL while the stick is held), game clock `$1b2` (60 ticks) -> `$1b4` minutes -> `$1b6` hours -> `$1b8` days (`$c38a`), stamina/breath timers `$1b0/$1b1` and `$1ae` (the breathing effect repeat, via `$ae38`, sound.md) | **world** | gated |
| `$c66a..` fade step `$66ec` (`$8f` bit 5) | palette fade, `$190/$191/$192` per VBL | presentation | unchanged |
| `$adbe` (`$90` bit 7), `$a65c` (`$1ce`) | mouse hit test, software mouse pointer redraw | presentation (input/display) | unchanged |
| `$c5fa` IKBD "interrogate joysticks" | joystick poll, once per VBL | input hardware | unchanged (p4_ikbd) |
| `$ea(a5)` countdown | screen timer of the intro/attract screens (`$1f68`: 1500 VBL) | presentation, not in the 3D loop | unchanged |
| `$1a6(a5)` (frame limiter) | byte countdown, reload `$1a7`; `$aaa2` spins on it; `$1a7` = 0 in the game (snapshots and the cold-boot 3D dump), i.e. a pure VBL lock | presentation (frame pacing) | unchanged |
| `bclr #3,$8f(a5)` | releases the flip lock `$aaa2/$aab4` (frames end on a VBL) | display sync | unchanged: frames still end on a real VBL |
| `bclr #7,$8f(a5)` | releases the wait-a-VBL loops `$aa98` (`$aa8a`: d0 VBLs of delay: 100/150 VBL pauses at `$2110/$22f0`, mouse click throttle `$a5a6`, 3-VBL character delays `$b39a`) | presentation (menus, transitions) | unchanged (these pauses are 20 % short at 60 Hz, as in the original) |
| `$c628` sound tick -> driver `$10fb2+$40` | request/priority/lock, **durations** (`$10+c`), volume words, envelopes of the 3 channels | **world** (effect lengths) | gated through `HZ_SKIP` |
| snd_core mixer (`snd_update` after the tick) | tops the DMA ring up to TARGET = 192 samples ahead of the DMA position | hardware (rate = 6258 Hz) | every real VBL |

Nothing else in `$800..$12003` reads the VBL counter: the `$aa8a` family and the `$1a6` limiter are the only other VBL waits, and `$5f7e` (scripted-mode compare against `$1a8`) is world time.

## 2. Change

**hn_hz** (`$c63c`: `btst.b #7,$93(a5)`, 6 B -> `jmp $8da00.l`). It runs once per VBL, right after the LFSR and before the 3D-loop block:
```
d0 = 6 (sync bit 1 of $ff820a set = 50 Hz) or 5 (60 Hz)         units of 1/300 s per VBL
acc += d0
if acc >= 6: acc -= 6; skip = 0; btst #7,$93(a5); jmp $c642      -> the handler continues unchanged = one WORLD TICK
else:        skip = -1;                         jmp $c66a        -> the whole 3D-loop block is skipped (fade, mouse, joystick poll, sound mixer still run)
```
- 50 Hz: acc stays 0, every VBL is a tick: the same instructions as the original run, plus the hook.
- 60 Hz: 5, 10, 9, 8, 7, 6 -> ticks on 5 of every 6 VBLs; `$1a8`, `$1aa/$1ac`, the clock and every counter advance 50 times per real second, and `$1ac` (elapsed ticks of a frame) is the 50 Hz-equivalent count the game consumes. The remainder (`acc`) is carried across frames.
- The mode is read at every VBL (a runtime switch is followed). State: `acc.w` at `$8dbf0`, `skip.b` (`HZ_SKIP`) at `$8dbf2`; the hook uses only d0/a0 (saved by the handler).
- A frame can now contain 0 ticks only if it lasts one VBL (at 60 Hz, 1 in 6); `$1ac = 0` is harmless (all uses are `mulu`/`sub`; no divide). A frame that long needs a machine far faster than anything the game has run on (walking at 16 MHz is 3 VBL).
- Cost [calc]: tick path moveq 4 + btst abs.w 16 + bne.s 10 + lea.l 12 + add 8 + cmpi 8 + bcs.s 8 + subq 4 + move 8 + clr.b 16 + btst 12 + jmp 12 = 118 cycles, minus the replaced `btst` (12) = **+106 cycles per VBL** (0.066 % of the 160,256 of an 8 MHz PAL VBL). Skip path (60 Hz, 1 in 6): ~110 cycles and the whole block is not run.

**snd_core** (two tests of `HZ_SKIP`): `snd_run` skips `jsr $40(a0)` (the original driver tick) and the scan/voice allocation (`snd_update` up to the voice parameters) and enters the mixer at the new label `snd_act`; `snd_pass` (plain ST, YM) skips the tick. So on a skipped VBL only the DMA ring is topped up. `.ret` became the global `snd_ret` (scoping); no other change. Without `hn_hz` the byte at `$8dbf2` is 0 (zero-filled image), i.e. the tick always runs.
- Ring at 60 Hz: the write cursor is kept TARGET = 192 samples ahead of the DMA counter whatever the VBL period; one VBL consumes 104.3 samples (125.2 at 50 Hz), so the lead before each top-up is larger at 60 Hz. The DMA rate register stays `$80` = 6258 Hz: the pitch does not depend on the refresh. A top-up writes at most 31 groups (248 samples), far above 104/125.
- The voice allocator counts `age` in driver ticks (one `snd_update` per tick; `age x 125` samples for a promoted one-shot): unchanged and still right because ticks are 50 Hz-equivalent.

**test_hznop** (not shipped): the same site, the same instruction sequence and cycles as `hn_hz` at 50 Hz, but it never skips. It is the timing control for gate (a) and the "unpatched speed at the same cost" control at 60 Hz.

## 3. What the game does with the refresh [disasm][obs]

The game forces **50 Hz** itself: `$a946` (hardware init: saves the TOS state incl. `$ff820a` into `$a7f6..`) calls `$aa28` with `d0 = 0, d1 = 2` (`$a9e8 moveq #2,d1`) which ends in `move.b d0,$260(a6) / move.b d1,$20a(a6)` (low res, sync mode 2 = 50 Hz) [disasm]; the restore at `$a89e..$a8fc` writes the saved values back. Cold boot, sync byte after each stage (`hunthz.py cold`), bit 1 set = 50 Hz [obs]:
```
STE 1.62 (HD):          hw:$02 title1:$fe title2:$fe main:$fe games:$fe name:$fe mission:$fe game:$fe
STE 1.62 (floppy):      title2:$fe games:$fe name:$fe mission:$fe game:$fe
Mega STE 2.06 4 MB:     hw:$00 title1:$fc title2:$fe main:$fe games:$fe name:$fe mission:$fe game:$fe       (TOS 2.06 boots at 60 Hz in Hatari; the game switches to 50 Hz while it loads)
```
So on hardware that honours the write (ST/STE/Mega STE shifter) Hunter runs at 50 Hz even on a 60 Hz-booted machine, and `hn_hz` never skips a tick there. It acts when the screen really runs at 60 Hz with the game running: hardware or adapters that ignore the write, or a machine on which the 50 Hz write does not change the VBL rate [INFERENCE: Falcon/TT video modes were not tested]. The test runs force 60 Hz with `w $ff820a $00` (as in the Midwinter and Powermonger gates); Hatari then runs 60 VBL per second (cycles per VBL 133,3xx at 8 MHz = 8,000,000 / 60). Limit: the detection reads the same register the game writes; if a machine ignored the write AND returned the written value, `hn_hz` would read 50 Hz and not correct. A timer-based measurement of the VBL period (MFP timer C's data register is still counting under the game, its interrupt masked: the phase moves by 1/3 of a period per VBL at 60 Hz and not at 50 Hz [INFERENCE]) was not built.

## 4. Gates

### (a) 50 Hz: identical to the build without `hn_hz` [obs]
Method (`hunthz.py ab`): both runs restore the snapshot, at the first flip after a start VBL apply the live patch set, hold the stick (the debugger pokes `$d1(a5)` at the handler's `$c64c` every VBL, so both runs see the same input to the VBL; a host key press is not reproducible), and at every loop top `$253e` log the VBL, the cycle counter and **5418 bytes of RAM `$806..$1d2f`: all game variables and the 30 object records (`$a68 + 30 x $a0`: player, NPCs, birds, projectiles, vehicles)**. 1500 VBL per run.
The frame lengths in VBLs are part of the simulation (`$1ac`), and `hn_hz` adds 106 cycles per VBL (about 1,000 per frame), so against the plain unpatched game a frame that ends close to a VBL boundary can take one VBL more; from that frame on the two runs legitimately differ. Therefore the gate uses the **timing control `test_hznop`** (same cost, never skips) as the base: equal timing means every frame must be bit-identical. Free-running, no lock, 50 Hz:
```
AB foot_stand    8 MHz:  133 of 133 frames IDENTICAL (1500 VBL), frame VBL sequence identical
AB foot_walk (Up) 8 MHz: 238 of 238 IDENTICAL
AB car_stand (Up) 8 MHz: 210 of 210 IDENTICAL
AB car_drive (Up) 8 MHz: 213 of 213 IDENTICAL
AB car_turn (Up+Left) 8 MHz: 191 of 191 IDENTICAL
AB hills_stand   8 MHz:  176 of 176 IDENTICAL
AB 4mb_foot_stand 8 MHz: 137 of 137 IDENTICAL
AB foot_walk (Up) 16 MHz: 472 of 472 IDENTICAL
AB car_turn (Up+Left) 16 MHz: 377 of 377 IDENTICAL
```
Against the plain unpatched game (free-running, 8 MHz unless noted), frames identical before the first difference: foot_stand 84 of 133, foot_walk 2 of 238, car_turn 24 of 191, car_stand 16 MHz 117 of 415; the first difference is always a frame whose loop-top VBL is one later in the patched run (`VBL 5855/5856`: a frame crossed a refresh boundary), and the changed bytes are `$9af $9b1 $9b9` (the tick counter and the `$1aa/$1ac/$1ae` words) and the stick poke. A "lock" (`$1a7 = $0e`, minimum frame 15 VBL) does not remove this: the limiter's reload races the handler, frames still come out 14/15/16 VBL and 1-7 % of them differ (base itself shows 14 and 16). This is the same effect as any change of the per-VBL cost (p4_ikbd saves 2,800 cycles per VBL and shifts frames the same way, huntab.py); it is timing, not state.

### (b) 60 Hz vs 50 Hz: world speed per real second [obs]
Method (`hunthz.py table`): snapshots `foot_walk` (Up), `car_stand` (Up), `car_turn` (Up+Left; heading word `$ae6`), 50/60 Hz x 8/16 MHz, the same pokes; rate = least-squares slope of the unwrapped word against t = VBL / hz over a window of whole frames (foot 1-9 s, car 0.5-3 s, turn 0.5-4 s after the first loop top; the car stops at a shore after ~4 s). `base` = the default patches without `hn_hz` (the original behaviour); `hn_hz` = with it. Units are the game's word units per second (1 HUD unit = 256).
```
scenario  set    MHz | 50 Hz units/s | 60 Hz units/s | 60/50  | clock ticks/s 50 -> 60 | tick counter/s 50 -> 60
foot      base     8 |        101.0  |        121.0  | 1.1980 | 50.000 -> 60.000 | 50.000 -> 60.000
foot      base    16 |        100.51 |        120.37 | 1.1976 | 50.000 -> 60.000 | 50.000 -> 60.000
foot      hn_hz    8 |        101.0  |        100.94 | 0.9994 | 50.000 -> 50.013 | 50.000 -> 50.013
foot      hn_hz   16 |        100.49 |        100.47 | 0.9998 | 50.000 -> 49.962 | 50.000 -> 49.962
car       base     8 |        457.29 |        550.2  | 1.2032 | 50.000 -> 60.000 | 50.000 -> 60.000
car       base    16 |        448.61 |        537.25 | 1.1976 | 50.000 -> 60.000 | 50.000 -> 60.000
car       hn_hz    8 |        457.0  |        456.05 | 0.9979 | 50.000 -> 49.984 | 50.000 -> 49.984
car       hn_hz   16 |        447.27 |        446.3  | 0.9978 | 50.000 -> 49.957 | 50.000 -> 49.957
car_turn  base     8 |     -12748.4  |     -15278.4  | 1.1985 | 50.000 -> 60.000 | 50.000 -> 60.000
car_turn  base    16 |     -12800.0  |     -15267.4  | 1.1928 | 50.000 -> 60.000 | 50.000 -> 60.000
car_turn  hn_hz    8 |     -12748.4  |     -12740.3  | 0.9994 | 50.000 -> 49.960 | 50.000 -> 49.960
car_turn  hn_hz   16 |     -12800.0  |     -12740.1  | 0.9953 | 50.000 -> 49.940 | 50.000 -> 49.940
```
(speed of the car = hypot of the X and Z slopes; the foot scenario is Z only.) With `hn_hz` all ratios are within 0.5 % (worst: turn at 16 MHz, -0.47 %); the original runs +19.3 .. +20.3 % fast at 60 Hz. The game clock (`$1b2..$1b8`, in ticks) and the tick counter `$1a8` run at 50 per real second at both refreshes (the 60 Hz deviations of 0.03-0.12 % are the one-tick quantisation of a 7 s window). The 8 MHz and 16 MHz columns of the same refresh agree to 0.5 % (the 1.3 % car difference between 8 and 16 MHz at 50 Hz is in the base too: per-frame integer truncation of the movement). The raw rows are printed by the tool (`ROW {...}`).
The driver tick count (`hunthz.py drv`, breakpoint at the driver entry `$10ff2`, 600 VBL) [obs]:
```
DRV STE (DMA sound) payload mode 2 50 Hz: driver ticks 592 in 592 VBL = 1.0000 per VBL = 50.00 per second
DRV STE (DMA sound) payload mode 2 60 Hz: driver ticks 496 in 595 VBL = 0.8336 per VBL = 50.02 per second
DRV plain ST (YM) payload mode 1 50 Hz: driver ticks 595 in 595 VBL = 1.0000 per VBL = 50.00 per second
DRV plain ST (YM) payload mode 1 60 Hz: driver ticks 496 in 595 VBL = 0.8336 per VBL = 50.02 per second
```

### (c) Sound at 60 Hz [obs]
Hatari WAV capture (`--sound 50066`, `snd_test.py record ... --live snd_hz --hz 60`; `snd_hz` = snd_core + hn_hz, `snd_ctl` = snd_core + test_hznop = the original per-VBL tick at the same cost), `snapshot 1mb_foot_stand`, `--quiet`, effects injected like the game's trigger does; `snd_test.py dur` finds the onset and the end of each sound in the DMA stream (one sample per 8-sample group, threshold 8 % of the peak). Lengths in seconds:
```
                                        50 Hz (hn_hz)     60 Hz (hn_hz)     60 Hz control (tick every VBL = original)
effect 3  explosion (vol 12)             2.74              2.75              2.75     (sample-limited)
effect 6  gunfire   (vol 14)             0.57              0.58              0.47     (driver duration-limited: -17 %)
effect 4  explosion (vol 10)             1.59              1.60              1.34     (-16 %)
effect 17 tired breathing, env 2 (vol 12) 1.59             1.58              1.45     (-9 %)
effect 18 breathing, env 2 (vol 12)      3.64              3.64              2.86     (-21 %)
```
With `hn_hz` the lengths at 60 Hz match 50 Hz within 0.01 s (< one VBL, 0.017-0.020 s); without the gate the driver-limited ones and both envelopes run 9-21 % short. Request-to-sound onset +22 ms (50 Hz) / +19 ms (60 Hz).
Engine loop (effect 11, vol 15, 4 s correlated against the model render): `|rho| = 0.9833` at 50 Hz and `0.9832` at 60 Hz (the loop pitch is the DMA rate, independent of the refresh).
Ring (`snd_test.py ring`, 900 VBL, an engine and a rotor loop at volume 15 plus an explosion re-injected every 70 VBL; breakpoints at the top-up in `snd_update` and at the underrun resync): lead before each top-up (samples ahead of the DMA position) and resyncs:
```
50 Hz  8 MHz 1mb_foot_stand: 856 top-ups, lead min 58 max 70 mean 63.9, underrun resyncs 0   (1 VBL = 125.2 samples)
60 Hz  8 MHz 1mb_foot_stand: 849 top-ups, lead min 74 max 96 mean 84.7, underrun resyncs 0   (1 VBL = 104.3 samples)
60 Hz  8 MHz, tick every VBL control: min 80 max 90 mean 84.8, resyncs 0
60 Hz 16 MHz 1mb_car_drive (Up held): 849 top-ups, lead min 78 max 92 mean 84.7, resyncs 0
```
Mixer bit-exactness at 60 Hz (`snd_test.py mixcheck --live snd_hz --hz 60`, the 68000's ring and voice phases against the Python model per mixer call): 306 calls (one rotor + explosion scenario, 1-2 table voices) and 318 calls (two direct/table mixes) **0 differences**; `n8 = 13` groups per top-up (104 samples) as expected.

### (d) Cold boots with the default build (`HNPO`) [obs]
`hunthz.py cold`: boot with the harness (`boot_to_game` / `boot_floppy`), read marker/flags/payload mode, then measure the walking rate and the tick counter at 8 and 16 MHz with the refresh forced to 60 Hz (the game switches to 50 Hz itself, section 3; HD STE also at 50 Hz for reference). Builds: `build/game` (HD, `huntpatch.py build`), `build/floppy/HUNTER_disk1.st` (`build --floppy`), the packaged default sets (6 patches incl. `hn_hz`).
```
HD STE TOS 1.62 1 MB:    boot 47 s, in 3D view, marker HNPO, FLAGS 3, payload mode 2
   50 Hz  8 MHz: 100.68 u/s, ticks 50.000/s      50 Hz 16 MHz: 100.3 u/s, 50.000/s
   60 Hz  8 MHz: 100.31 u/s, ticks 49.989/s      60 Hz 16 MHz: 100.04 u/s, 49.959/s     (133,722 / 266,973 cycles per VBL = 8, 16 MHz / 60)
floppy STE TOS 1.62 1 MB (82x11 disk, real FDC timing): boot 91 s, in 3D view, marker HNPO, FLAGS 3, payload mode 2
   60 Hz  8 MHz: 100.78 u/s, ticks 49.977/s      60 Hz 16 MHz: 100.11 u/s, 50.006/s
Mega STE TOS 2.06 4 MB (HD; TOS boots at 60 Hz, the game at 50 Hz): boot 129 s, in 3D view, marker HNPO, FLAGS 3, payload mode 2
   60 Hz  8 MHz: 100.92 u/s, ticks 50.006/s      60 Hz 16 MHz: 100.1 u/s, 49.994/s
```
(foot = the HQ start position, Up held by the stick poke, window 1-8 s.) The original (no `hn_hz`) at 60 Hz walks at 120.4-121.0 u/s (table in (b)). The `hn_hz` state read after the boot is `acc = 0, skip = 0` (the 3D view runs at 50 Hz there).

## 5. Limits
- On ST-family hardware the game stays at 50 Hz (section 3); the correction is exercised by forcing 60 Hz. TT/Falcon video modes and real hardware were not run.
- Detection = `$ff820a` bit 1. 71 Hz monochrome is not representable in whole units of 1/300 s and the game has no mono mode (same as the Midwinter/Powermonger gates).
- Not converted (presentation, 20 % short at 60 Hz as in the original): palette fades, the 100/150-VBL pauses of the intro/mission screens, mouse-click throttling in menus, the screen timer `$ea`. They never touch the 3D world.
- The hook costs +106 cycles per VBL at 50 Hz; frame lengths in VBLs (quantised, 5-12 VBL) can change by one at a boundary, as with any per-VBL cost change.
- `tools/huntab.py`'s identical-picture gate (first frame after the patch goes live) is unaffected: `hn_hz` does not touch the render.
