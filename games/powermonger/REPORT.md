# Powermonger enhanced: how it was done

This is a plain-English account of the work on *Powermonger* (Bullfrog / Electronic Arts, 1990, Atari ST, the single-disk original). It covers what was changed, what the original code did at each point we changed, and what each change achieved. It follows the Midwinter and Hunter jobs (`../midwinter/REPORT.md`, `../hunter/REPORT.md`) and reuses their method and test harness. The evidence (disassembly, measurements, raw logs) is in `work/notes/`, and the patch sources are in `patches/`. Every number below comes from those notes (`regression.md` for the final machine matrix).

## 1. Starting point

The game is floppy-only. The disk (`disks/protected.st`, 800 KB, GEMDOS FAT12) holds:

| File | Role |
|---|---|
| `AUTO\WAR.PRG` | Two self-unpacking programs in series. Stage 0 is a tiny plain stub; stage 1 unpacks the title/intro program (pictures, credits) and a FAT12 loader. |
| `DATA\SPRITE40.DAT` | Not sprites: stage 2, a second self-unpacking program that unpacks the game proper (111,592 bytes at `$10A6..$1C48D`). Dated 1987 on the disk, which is why it looks like a leftover. |
| `DATA\*.DAT` (14 more) | Compressed data: textures, sprites, the sound effects bank (`FX.DAT`), the map, the end pictures. |

After the TOS boot sector the game never calls TOS again. It drives the floppy controller and the DMA chip directly with its own FAT12 reader (about 12 call sites) and its own save-game code, and reads only `DATA\<name>` by name. Saves go to a second, game-formatted floppy (the "SAVE GAME DISK"), never to the game disk.

**Baseline**, unpatched, 1 MB STE (`baseline.md`, fps = flips of `$ff8201`, 8 MHz / 16 MHz):

| Scene | 8 MHz fps | 16 MHz fps |
|---|---:|---:|
| Map view, standing (a sample is playing) | 2.38 | 6.25 |
| Get Men, 16 walkers | 4.00 | 8.25 |
| Battle | 3.88 | 8.25 |

A pass of the main loop costs 2.1–3.4 million cycles, i.e. 13–21 refreshes at 8 MHz. About 130 terrain triangles and 17–18 sprites are drawn per pass in every scene, so the cost is the amount of terrain and objects in view, not the fighting.

**Game speed.** The world is tied to the frame rate: one world step per main-loop pass. Measured on the same scene, the stock game ran its world **3.8 ticks/s at 8 MHz and 7.86 ticks/s at 16 MHz**, and 2.1–2.9 times faster at 16 MHz than at 8 MHz (`timing.md`, `PLAN.md`). While a sample plays, the original's world crawls to 58% of its stock pace on an 8 MHz machine (the YM sample interrupt takes 26% of the CPU).

**The copy protection** is not a disk check. After the first conquest starts, the renderer builds a decoy land and asks "how many houses/people in this land?", with the answer taken from a manual page. A wrong answer prints "Demo mode now activated" and disables Save/Format (`protection.md`).

### How we worked
- Hatari ran headless, driven by scripts (`tools/pm.py`, `tools/pmpatch.py`, `tools/pmtick.py`, ...), from saved machine states, with profiling.
- **Equality gates.** The world state of the patched game is compared with the unpatched game tick by tick over the whole low RAM, with a negative control each time (a patched tick against the next unpatched tick must differ). Rendering patches are compared frame by frame, byte for byte, matched by (world tick, kind of pass), because the world no longer advances once per frame.
- **Cold boots** of the real disk and the HD folder into the map view on the machines in section 11.

## 2. The patch system

`tools/pmpatch.py`; `patches/core.s`, `patches/hd_*.s`; note `loading.md`. A patch is one `.s` file with a header (`; name:`, `; site:`, `; orig:` = the original bytes at the site, `; default:`, `; stage:`). `pmpatch.py verify` derives the original bytes by unpacking the shipped disk image (it does not use a dump) and compares them with each patch's declared `orig`.

- **Delivery.** The new `AUTO\WAR.PRG` has an appended data segment that holds the patch code. TOS loads text and data with its own file API, so the same file works from a floppy and from a folder, and no other file on the disk moves. A 96-byte front stub copies the payload to `$B8000..$DC023` (free RAM, proven free), then the original program runs. The patch records are stored sparse: only non-zero runs take disk space.
- **Hooks.** At the end of stage 2's own unpacker, 32 bytes of stack routine end in `jmp hook2` instead of `rts`. The hook compares the **original bytes of every site first, and only then writes them all, or none** (`MARKER` = `PMPO` all applied, `PMPF` refused). The game starts either patched or as before. Plain `rts` registers are preserved exactly.
- **STE probe.** The core finds out whether DMA sound exists by touching `$ff8901` with a bus-error guard (flag bit 0 = DMA sound): STE, Mega STE, TT and Falcon give `3`, plain ST gives `6`.
- **Free RAM.** Every unused byte of `$B8800..$EFFFF` was filled with a position-dependent pattern, then the game was booted, played into a battle and compared: **0 bytes changed** (floppy at 1 MB and 4 MB; HD at 1 MB and 4 MB Mega STE, with a save and load through the menu).
- **CPU caches.** On a 68020+ `init` switches every cache off before the game runs a single instruction (section 11, `loading.md` section 9). `pm_credit` adds the version line on the main menu; `fal_ym` is the Falcon title-music fix.
- **Floppy build:** the disk image with `AUTO\WAR.PRG` replaced and `DATA\SPRITE40.DAT` patched in place (30 bytes differ). The patch payload costs about 24 KB on the disk; 31,744 bytes stay free.

## 3. Timing: real time instead of the frame rate

`patches/tick_*.s`; note `timing.md`.

The loop is split by pass kind. Every pass looks at the VBL counter (converted to 1/300 s units, so 50 Hz and 60 Hz both work) and decides:
- **T pass** (a world tick is due): the original pass, byte for byte the same frame and logic. 4.00 ticks per second (0.25 s).
- **S pass** (behind): logic, men and HUD only, no render, so an 8 MHz machine catches up (at most 3 ticks owed).
- **R pass** (ahead of real time, 16 MHz and up): no logic; render, HUD, input and camera only.

Pause, a gap of more than a second and a backwards counter all re-sync without a burst of ticks. The click-lifetime clock (`$2df70`) keeps counting passes so a click does not live for a whole tick.

| Gate | Result |
|---|---|
| World ticks per second, get_men, 8 / 16 MHz, 50 Hz | 4.011 / 3.999 |
| the same at 60 Hz (a Mega STE with TOS 2.06 boots at 60 Hz) | 4.012 / 3.999 |
| Per-tick state equality against the unpatched game (3 scenes × 8/16 MHz, a forced season change, 60 Hz) | **identical** in every run (up to 99 loop tops); negative control different every time |
| Patched 8 MHz against patched 16 MHz | identical, 51 ticks |
| Displayed frame of each tick pass against the unpatched frame | 32 of 32 and 38 of 38 byte-identical |
| Map view at 8 MHz where the stock game crawled at 2.33 passes/s | world at 3.97–4.00 ticks/s (+70%) |

**Limits:** camera, scroll and rotate speed still follow the frame rate (a held key scrolls one cell per pass, as in the original); the speed slider (`$57fee > 1`) was not tested with the patch.

## 4. 50 Hz and 60 Hz

The first tick patch counted VBLs, so a 60 Hz screen (US TOS defaults, TOS 2.06 on a Mega STE) ran the world at 4.8 ticks/s. The tick now converts the VBLs since the last look using the shifter's sync bit (`$ff820a`, read at every look, so a switch while playing is followed): 4.0 ticks/s measured at 50 and 60 Hz, 8 and 16 MHz (table above). Sound effects are still scheduled per VBL, so on a 60 Hz screen the sound sequences run 20% fast, exactly as in the original.

## 5. STE DMA sound

`patches/snd_*.s`; note `snd.md`.

**What the original does.** The ST has no sample hardware, so the game plays 8-bit effects through the YM chip's three volume registers from an MFP timer-A interrupt at up to 8 kHz. Each interrupt costs 264 cycles: **26.4% of an 8 MHz CPU** measured while the map-view ambient loop plays (13.2% at 16 MHz). The FX bank has 58 chunks in 56 sequences; the steps of a sequence change the playback rate per step (381 different chunk/rate pairs, 2.4–8.7 kHz), and a pause is a short chunk played at a high rate. A new effect cuts the old one (one voice).

**What we did.** On STE-class machines the same bytes play through the DMA chip. The game's sequencer and effect queue are untouched, so timing, pauses, loops and pitch steps stay exactly the game's. The 8-bit data are linear signed PCM and the STE's output stage inverts like the YM path, so no conversion is needed. A producer in the VBL tick resamples each chunk live (nearest neighbour, the same sample-and-hold as the original) to the DMA's 6,258 or 12,517 Hz into a staging buffer, one VBL ahead of the DMA pointer, and plays it single-shot. No timer, no interrupt, no state outside the sequencer. Plain ST keeps the YM player (the hook runs the original instructions).

| | Original (YM IRQ) | DMA |
|---|---:|---:|
| CPU, map-view ambient loop, 8 MHz | 26.4% | 4.9% |
| fps, same scene, 8 MHz | 2.35 | 3.35 (+43%) |
| CPU, 16 MHz | 13.2% | 2.5% |
| Average over all effects, 8 MHz [INFERENCE: computed from the sequence tables] | 18.6% | 3.4% |

Sound check (Hatari WAV capture, same trigger, onset-aligned): correlation with the original 0.90–0.99 on eight effects, durations within one VBL over 14.6 s (a "direct" DMA of the raw chunk was tried and rejected: wrong pitch by +492 cents on average, correlation 0.05–0.3). The DMA version is about 1.3× louder in Hatari. The plain-ST path of the patched build gives correlation 0.996–1.000 with the original. Quality is the original's (zero-order hold from 2.4–8.7 kHz); a better sample bank from the user can be dropped in later (format proposed in `snd.md`).

## 6. Speed-ups

All patches are on by default and every row is pixel-identical to the original in the frame-by-frame gate (`tools/pmab.py`).

### Pass 1: pointer and sprites (`p4_ptr_a/b`, `p4_spr`; note `p4_raster.md`)

| Patch | What the original did | What changed | Saving (render-stage cycles per pass, 8 MHz) |
|---|---|---|---|
| `p4_ptr_a` + `p4_ptr_b` | The VBL handler restored the 16×16 area under the pointer and redrew the pointer **every VBL**: about 12.9 k cycles × ~12 VBLs per pass. | Skips both when nothing changed: same pointer address, same inputs, no animation step, and the pointer rectangle compared with what the last draw left. A buffer flip always takes the full path. | −4.4 to −5.6% |
| `p4_spr` | Masked sprite blits, shift-and-mask in the CPU. | The STE blitter does the shift and mask. Plain ST uses a pre-shifted sprite cache in CPU code (62 KB RAM, no disk space). | −10.6 to −12.3% (blitter), −8.3 to −10% (cache) |
| both | | | **−15.6 to −15.9%** cycles, fps +16.5 to +18.5% |

A copy of the 3D window during the VBL wait (`p4_chase`) gave +2 to +8% fps but was **not exact**, so it is off. Maths tables and a static-frame skip were looked at and not built (`p4_raster.md` sections 6 and 7).

### Pass 2: terrain (`p6_tri`, `p6_slope`, `p6_cpy`; note `hotpaths2.md`)

The new profile of the default set showed the terrain span fill (40–48% of all cycles) and triangle setup (8–11%) as the heavy items, then the 32,000-byte window copy (8–12%).

| Patch | What changed | Gain |
|---|---|---|
| `p6_slope`, `p6_tri` | The terrain triangle setup and span fill (the original did 3–7 `divu` of about 130 cycles per triangle, a 12-word record, and a per-scanline edge walk with two run counters). The divides come from a 64 × 64 table of the exact `divu` results (`p6_slope`, 16 KB of RAM, no disk space) whenever the edge is small, from the original `divu` otherwise; the fill runs in chunks between slope changes. Anything unusual (clipping) falls back to the original code. | −12.7 to −13.97% cycles (+9 to +16% fps) |
| `p6_cpy` | The 32,000-byte copy of the window picture to the back buffer, done by the STE blitter in 20 chunks of 10 rows (the bus is held for 0.8 ms at most, so the keyboard cannot overrun). Plain ST (and TT/Falcon, where the blitter probe is not taken) keep the original routine. | a further −2.7 to −5.0% |
| all three | | map view **+22.6% fps** (2.77 → 3.39), get_men **+19.5%** (4.52 → 5.40), battle **+20.6%** (4.55 → 5.49) at 8 MHz; +12 to +17% at 16 MHz |

(The fps columns are relative to the then-current default set, which already contained pass 1 and the DMA sound.)

## 7. Protection

`patches/pm_noprot.s`, `pm_noprot_box.s`; note `protection.md`. The state "passed" is **one long word at `$14e4e`** in the game image (`$0000002c`); until it holds that, the renderer's handler for the first person (`$11bf4`) runs the check. `pm_noprot` writes `$2c` into the word at the hand-over and `pm_noprot_box` turns the "Please wait for the protection check" box into a no-op. The question is never asked, the real land is generated at once, and Save/Format stay enabled. The cold-boot test fails if the question box appears (`pm.py boot_to_game`), and checks the pass flag.

## 8. Tooltips

`patches/pm_tooltip.s`; note `tooltip.md`. The game has no hover help at all (every read of the pointer position is a click path). The hook before the HUD draw tests the pointer against the game's own hit-test tables (the same line tables the click uses, re-implemented in `pmtt_grid.py`: no divide overflow and no icon outside its cells over all 320 × 200 pixels) and writes a 52-character line in the game's font into the free part of the black bar at the top of the screen, for the command icons, the four map modes, rotate, zoom and the compass. The text depends on the posture setting (1/2/3 swords = 25/50/100%). Cost per frame: 416 cycles when the pointer is still, +0.16% cycles per pass while hovering; the screen differs from the unpatched game only inside rows 0–5, columns 7–19 (gate `pmtt_ab.py`: identical with the pointer away from every icon, tooltip rectangle only with it on one).

## 9. Men interpolation

`patches/p3b_interp.s`, `p3b_delta.s`; note `interp.md`. The world still steps 4 times a second, so on a fast machine every frame between ticks looked the same. On the frames between ticks, the men (and projectiles) are drawn part-way into their next step: the delta from the last tick is extrapolated by the fraction of the tick that has passed (predict-ahead, no latency), then restored. It is exact on tick frames and costs 1.1% at 16 MHz. **On an 8 MHz machine the frame is longer than a tick, so it changes nothing** (fps identical). Limits: animals and angels are not extrapolated (about 1 px per tick); a man that stops is overshot by 3–5 px for at most one tick; a man crossing a cell edge is sorted a tick late.

## 10. The hard-disk build

`pmpatch.py build --hd`; note `loading.md` section 7. The game reads its disk with its own FDC code, so for a hard disk the loader had to be replaced.

- **`hd_load`** replaces the by-name loader (Fopen/Fseek/Fread/Fclose); **`hd_sector`** replaces the sector driver for the save game (`SAVEDISK.DAT`, byte offset = sector × 512, 800 sectors); **`hd_s1`** replaces stage 1's call to the by-name loader that loads `DATA\SPRITE40.DAT` (the game proper, stage 2). The data lives in `DATA\` next to `AUTO\`; the folder the program was started from is the data folder.
- **The TOS swap.** The game overwrites TOS's low memory and the hard-disk driver in it on the first instruction, so the first real GEMDOS call crashed under HDDRIVER. The core copies TOS's region (everything from address 8 to the program's start: 78,640 B on an STE with TOS 1.62, 87,760 B on a Mega STE with TOS 2.06) to a buffer at `$DD000` before the game runs, and for each file call exchanges the two ([INFERENCE] about 0.1 s at 8 MHz for 78 KB, not timed), runs the call with its own stack, interrupts reduced to the 200 Hz timer and the keyboard, and exchanges back. The buffer spills as far as `$F5FFF` if it has to; 102,400 B is the limit, above it a message is shown.
- **The keyboard** bytes that arrive during a call are queued and fed to the game's own handler afterwards (a bug that took the longest to find: lost bytes of the 6-byte mouse packets gave a wild pointer position and a bus error right after Save).
- **`PMLATE.DAT`:** stage 1 reads `SPRITE40.DAT` over the payload area, so the code and tables that live there are read back from this file in the same call.
- **Results.** Real driver (ACSI + HDDRIVER 10.15): STE 1.62 1 MB and Mega STE 2.06 4 MB reach the map view with `PMPO`; Save and Load through the game's own menu reproduce the state exactly (0 bytes differ over the 198-sector game state), and `SAVEDISK.DAT` slot A equals the saved bytes. Hatari's GEMDOS folder works with the same code. The free-RAM pattern proof (including the swap spill region) passed with 0 bytes changed.

## 11. Regression

See `work/notes/regression.md` for the table with the exact numbers, the commands and the raw lines. Summary:

Cold boots into the map view, then get_men, patched build (no triple buffering), Hatari 2.6.1; fps / world ticks per second:

| Machine (floppy unless noted) | map view | get_men | notes |
|---|---|---|---|
| ST TOS 1.04, 1 MB, 8 MHz | 4.55 / 4.05 | 4.75 / 4.00 | YM sound; original 2.30 / 3.45 fps |
| STE TOS 1.62, 1 MB | 4.60 / 4.00 | 5.40 / 4.00 | DMA sound; original 2.80 / 3.45 fps |
| STE 4 MB | 4.60 / 4.00 | 5.35 / 3.95 | |
| Mega STE TOS 2.06, 4 MB, 60 Hz, 8 / 16 MHz | 4.62 / 4.02, 9.84 / 3.96 | 5.52 / 4.02, 11.88 / 4.02 | |
| TT TOS 3.06, 4 MB | 19.80 / 4.02 | 19.80 / 4.02 | CPU caches off |
| Falcon TOS 4.04, 4 MB | 10.00 / 4.05 | 12.15 / 4.00 | CPU caches off, title-music fix |
| HD (ACSI + HDDRIVER) STE 1 MB, Mega STE 4 MB, TT 4 MB | same as the floppy | same | Save and Load through the menu: 0 bytes differ |
| HD, Hatari GEMDOS folder, STE | 4.60 / 4.00 | 5.30 / 4.00 | |

On all of them the DMA sound plays (or the YM on the ST), the tooltips appear, the protection question is never asked and the world runs at 4.0 ticks/s. The patched game is **+98% / +38%** (ST) and **+64% / +57%** (STE) faster than the original in the map view / get_men at 8 MHz.

**TT and Falcon.** The original does not start on either: the game unpacks code over its own unpacker and the 68030's instruction cache keeps executing the old bytes (Line-F at `$672`, then TOS hangs or bombs). The loader now switches the CPU caches off on a 68020+ (data cache too: the 030 does not see the floppy DMA). The Falcon also bus-errors on the title music's writes to the sound chip's mirror addresses; `fal_ym` does the same writes through the two real addresses. Switching the instruction cache back on in the game was tried on the TT and the game never reached the name prompt, so it stays off. The Falcon with a hard disk could not be tested (Hatari's Falcon has no ACSI, and HDDRIVER does not see its IDE disk); play.sh falls back to the GEMDOS folder there. Details: `loading.md` section 9 and `regression.md`.

## 12. Triple buffering

[Placeholder, to be filled in by the lead when `p7_*` lands: what the original's double buffer plus window copy does, what changes, the cycle saving, the gate results and the regression re-run.]

## 13. Known limits

- **TT/Falcon run with the CPU caches off** (instruction cache back on: the game does not start on a TT in Hatari).
- **No real hardware was used.** Everything is Hatari 2.6.1. The DMA sound set-up (Microwire defaults, the DMA position read) is the one from Hunter and has only been seen in Hatari. The patches that probe for the STE with a bus-error guard are untried on a real ST.
- **Camera speed follows the frame rate** (scroll, rotate, zoom), as in the original.
- **Windows, messages and the speed slider** were not exercised with the tick patch (static check only: no UI routine counts passes).
- **Plain 8 MHz machines gain 20–40% in fps, not more,** because a frame is quantised to whole refreshes (a 13-refresh frame becomes 10.9, not 10) and the terrain fill is a hard floor.
- **Sound:** nearest-neighbour resampling from 2.4–8.7 kHz, as the original; louder than the YM version in Hatari; a delayed VBL (more than about 60 ms) would replay the stale tail of a chunk until it ends.
- **HD:** needs a driver that works through TOS's GEMDOS and a swap region of at most about 100 KB (the game stops with a message otherwise); the drivers other than HDDRIVER, the Falcon HD (untestable in Hatari), and booting from a subfolder were not tested. The ST-class machines with TOS 1.04 on HD were not re-run with the final core.
- **Floppy:** a save needs a second disk, as in the original (31,744 bytes are free on the game disk, not enough for 198-sector slots).
- **Saved games** of the original and of this version have the same format (the game state, 198 sectors); loading an old save into a patched game and the reverse was not tested.
- **Not examined:** the intro/title program (stage 1) has its own sound code and is not touched; the 71 Hz mono mode is not handled (the game has none).

## 14. Delivered

- `dist/Powermonger_v1.0_patched_floppy_<date>.zip`: `Powermonger_patched.st` and `README.TXT`.
- `dist/Powermonger_v1.0_patched_hd_<date>.zip`: `POWERMONGER\` with `AUTO\WAR.PRG`, `DATA\*.DAT`, `PMLATE.DAT`, `SAVEDISK.DAT` and `README.TXT` (hard-disk drivers and the TOS swap).
- `tools/package.sh` (verify, build, zip, md5s) and `tools/play.sh` (launcher: machine and TOS choice, `--floppy` / `--hd`, `--original`).
- The patch tool, 24 default patch files, the study notes, the test tools, and `work/notes/regression.md`.
