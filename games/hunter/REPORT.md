# Hunter enhanced: how it was done

This is a plain-English account of the work on *Hunter* (Activision, 1991; Atari ST, PP's 2010 "Gamex" hard-disk version). It covers what was changed, what the original code did at each point we changed, and what each change achieved. It follows the Midwinter jobs (`../midwinter/REPORT.md`) and reuses their method and test harness. The evidence (disassembly, measurements, raw logs) is in `work/notes/`, and the patch sources are in `patches/`. Every number below comes from those notes.

## 1. Starting point

PP's package is the older Gamex loader, not the HAGA system of the Midwinter conversions:

| File | Role |
|---|---|
| `START.TOS` | PP's packed loader: hardware-detect screen, title pictures, then loads the game. |
| `HUNTER.PCH`, `D15R_H5.FIC`, `HUM.FIC` | Title pictures, the game's own disk loader ("D15R") and the packed game code (71,684 bytes once unpacked to `$800..$12003`). |
| `FILES/0..F` | The game's data files, read by name through the hard-disk driver. |

It needs a real hard-disk driver on a FAT disk (Hatari's plain GEMDOS drive does not work): the test setup is a 16 MB ACSI image with HDDRIVER (`tools/hunter.py`).

**Baseline**, unpatched, 1 MB STE at 8 MHz (cycles per frame from the loop profile; fps from 600 refreshes):

| Scene | Cycles per frame | Frames per second |
|---|---:|---:|
| Standing on foot | 1,762,721 | 4.50 |
| Walking on foot | 1,015,560 | 7.42 |
| In the car, standing | 1,442,603 | 5.58 |
| Driving the car | 1,121,753 | 7.17 |
| Car, turning | 1,190,632 | 6.67 |

A frame always lasts a whole number of 50 Hz refreshes (standing: 11.0 refreshes = 4.5 fps), so a 1% saving can be invisible until it crosses a refresh boundary.

**Game speed.** Unlike Midwinter, the world is **not** tied to the frame rate. Movement and the NPCs multiply by the number of refreshes the previous frame took (`$1ac(a5)`), and nothing reads the real-time clocks. Measured walking on foot: 101.4 units/s at 8 MHz against 100.4 units/s at 16 MHz. So no timing patch was needed; a faster renderer only makes the motion smoother.

**Where the time goes.** The 3D render is 74–88% of a frame; about 61% of the walking frame is polygon scan conversion, edge set-up and span fills. The joystick poll in the 50 Hz interrupt wasted 2.4% of all cycles in a delay loop.

### How we worked
- Hatari ran headless, driven by a script (`tools/hunter.py`), from saved machine states, with profiling.
- **Identical-picture gate** (`tools/huntab.py`). Because the simulation depends on the length of each frame, patched and original runs are compared on the first frame after the patch goes live (both screen buffers, byte for byte), and with a locked 15-refresh frame time so that longer runs stay frame-for-frame identical. Passed on all 7 snapshots.
- A **differential test of the polygon filler** (`tools/polydiff.py`) runs new and original code on the same input and compares the output window: 16,773 polygons, 0 mismatches.
- **Cold boot** of the real file set into the 3D view on 1 MB STE (TOS 1.62), 4 MB STE, 4 MB Mega STE (TOS 2.06) and 1 MB ST (TOS 1.04).

## 2. The patch system

`tools/huntpatch.py`; `patches/core.s`, `patches/core_floppy.s`; notes `loading.md`, `floppy.md`.

### Hard disk
- **`START.TOS` is shipped unpacked** (PP's LZ unpacked by our tool) with two changes: the 6 bytes `lea $7e800,a7` just before its final `jmp $800.w` become a jump to a 142-byte stub, and the stub is written into a dead zero run of START's own text. Everything else, including the relocation table, keeps its layout.
- **The stub reads a new file, `FILES\P`**, through the game's own file loader (the same FAT/hard-disk path the game uses, so it works on every machine the game works on). It checks the magic `HNPA` and calls the core. If the file is missing, the game starts unpatched.
- **The core verifies the original bytes of every patch site first and only then writes them all, or none** (`HNPO` or `HNPF` is left at `$8BFF8`). Tested: with one wrong byte the game ran unpatched and nothing was written.
- **STE detection** is a hardware probe (cookies are unreliable under Gamex): it tries the STE DMA registers behind a bus-error guard. STE and Mega STE gave flag value 3, plain ST gave 6 (bus error seen, no DMA sound).
- The payload lives at `$8BA00..$AEFFF`. The free-RAM proof filled every unused byte with a pattern, booted, played and drove 25 s, and found 0 changed bytes on 1 MB STE, 2 MB STE and 4 MB Mega STE.
- Not used on Hunter: loading hooks for the game's own files (supported by the tool, none needed by the final patches).

### Floppy
A floppy release is needed because PP's build is hard-disk only. We use the **Paper Bag crack** (the user supplies the image in `alt/floppy/`).
- Its resident game, once unpacked and with the cracker's own RAM patches applied, is **byte-identical to PP's** (71,684 bytes compared). The only differences to PP's hard-disk RAM are 13 bytes (PP's two hooks and a debug constant), outside the patched code. So the same patch sources work unchanged.
- The cracker's `HUNTER.TOS` gets a small extra loader stage (306 bytes). It reads the patch file `HNPATCH.BIN` and the sample bank, then calls the same core.
- Its loader keeps a file cache over `$80200..$FFFFF`, which is where the payload lives. The cache start was moved to `$AF000` (331,776 bytes remain).
- The loader writes saves into existing slot files only, so extra files on the disk do not disturb saving.
- The Replicants crack was rejected: its game image is a different build (the keyboard patch site is not found), and it has a permanent trainer.

## 3. Speed-ups

`patches/p4_*.s`; note `p4_raster.md`. All three are on by default and pixel-identical to the original.

| Patch | What the original did | What changed | Saving (cycles per frame) |
|---|---|---|---|
| `p4_ikbd` | The 50 Hz interrupt polled the joysticks and then waited in a 200-iteration delay loop after the keyboard ACIA was ready (2,800 cycles, 3,855 per call measured). | Same byte, same ready check, same write, no delay. The multi-byte command senders keep the delay. | −1.9% in every scene |
| `p4_poly` | The polygon scan converter kept its state on the stack, counted rows per edge, and filled spans through generic mask code. | A register-based rewrite: exact early rejection of polygons that lie entirely left or right of the screen, edge walk in blocks of rows, mask tables. Anything unusual re-enters the original code. | −3.7% (standing) to −11.8% (walking) |
| `p4_edge` | Edge set-up used a divide for every edge. | No divide for dx = 0 and for dy of 1, 2, 4, 8, 16 or 32, where the quotient is an exact shift (proved exhaustively, including the overflow case). | −0.7% to +0.2%; marginal, kept because it is exact |

Combined, `p4_ikbd + p4_edge + p4_poly`, in the identical-picture test:

| Scene | Cycles per frame, original | Enhanced | Change | Refreshes per frame |
|---|---:|---:|---:|---|
| Standing on foot | 1,715,099 | 1,602,020 | −6.6% | 11.00 → 10.64 |
| Walking on foot | 1,556,173 | 1,343,317 | −13.7% | 10.55 → 9.00 |
| Car, standing | 1,367,769 | 1,277,241 | −6.6% | 9.00 → 8.68 |
| Car, driving | 1,052,275 | 980,316 | −6.8% | 7.00 → 6.88 |
| Car, turning | 1,177,296 | 1,032,873 | −12.3% | 8.00 → 7.00 |
| Hills, standing | 1,028,464 | 961,393 | −6.5% | 7.32 → 7.09 |
| 4 MB, standing | 1,646,916 | 1,531,143 | −7.0% | 11.01 → 10.01 |

(Cycles are from the first patched frame, logic and render without the idle wait; the "enhanced" column is the base minus the measured saving.)

**Frames per second** in the same test: standing 4.55 → 4.70, walking 4.74 → 5.55, car turning 6.25 → 7.14. In the **cold-booted** game the patched build stands at the HQ at 5.0 fps (10.0 refreshes per frame) at both 1 MB and 4 MB, against 4.5 fps unpatched; on the Mega STE (16 MHz in Hatari) it ran 8.4 fps. On a stock 8 MHz machine the gain is real but modest: Hunter's frames are quantised to whole refreshes.

## 4. STE DMA sound

`patches/snd_core.s`, `tools/snd_build.py`; notes `sound.md`, `snd.md`.

**What the original does.** The ST version uses the YM chip. A sound driver (file `FILES/4`, loaded at `$10FB2`) is ticked from the 50 Hz interrupt with 3 effect channels (request byte, priority, duration, volume word). There is no music in the 3D view and no timer is used; the driver costs about 2,550 cycles per refresh (1.8%).

**What we did (the user's decision, after listening to previews).** On STE-class machines the Amiga version's samples play through the STE DMA sound chip instead:
- The original driver keeps running as the state machine, but its 16 YM register writes are redirected to a dummy location, so the YM stays silent. Our code reads its state after each tick.
- **Two-voice software mixer, mono, 6,258 Hz**, mixing into a 1,024-byte looped DMA ring, kept about 31 ms ahead of the DMA position. No timer or interrupt of its own: it all runs inside the existing 50 Hz tick. The DMA stops when the 3D view is left, so the menu music is untouched.
- **Voice choice.** The 3 channels map onto 2 voices by the game's own priority classes and volume: an engine or rotor loop keeps one voice, the most important newest one-shot (explosion, shot, ping) gets the other. A bullet is never starved by two engines.
- **Engine pitch follows the speed**, as on the Amiga (the ST never did): period = base − 4 × speed. Measured loop periods in the capture matched the model to 4 digits.
- **Samples come from the user's Amiga ADF at build time** (`snd_build.py`, 124,126 bytes, 12 samples plus volume tables, placed at `$90000`). Nothing from the ADF is in git.
- **Plain ST** (no DMA sound) or a missing bank: the original YM driver runs unchanged. Cost: one jump and a few tests.

**Cost** (Hatari cycle profile, 8 MHz STE, 160,256 cycles per refresh = 100%):

| Scenario | Cycles per refresh | Share of the CPU |
|---|---:|---:|
| No effect playing | 304 | 0.2% |
| 1 sustained voice at volume 15 | 6,866 | 4.3% |
| 1 voice, other volume | 8,801 | 5.5% |
| 2 voices, both volume 15 | 11,879 | 7.4% |
| 2 voices, volume tables | 15,734 | 9.8% |

The cost applies only while effects play. With two sounds looping (the worst case) frames came out 0–8% slower (one voice) and 2–13% slower (two voices) than the original driver playing the same sounds; with nothing playing there is no measurable difference.

**Checks.** The mixer output matched a Python model in all 1,009 ticks over 5 scenarios (0 differences). Captured explosion, gunfire and effect samples correlate with the model at 0.987–0.995; two-voice overlap at mean 0.93. On a plain ST the injected explosion plays on the YM with the same onset as the original.

## 5. Floppy format choice and load times

`tools/huntpatch.py build --floppy`; note `floppy.md`.

Paper Bag's disk is 81 tracks × 10 sectors with only 43,008 bytes free. The sample bank (124,126 bytes) plus the patch file and the longer `HUNTER.TOS` need about 130 KB.

| Geometry | Bytes | Free with Paper Bag files only |
|---|---:|---:|
| 81 × 10 × 2 (original) | 829,440 | 43,008 |
| 80 × 11 × 2 | 901,120 | 116,736 |
| 81 × 11 × 2 | 912,384 | 128,000 |
| **82 × 11 × 2 (chosen)** | **923,648** | **139,264** |
| 83 × 11 × 2 | 934,912 | 150,528 |

**One disk, 82 × 11, full-quality bank** (the user's choice): 9,216 bytes remain free. It needs a drive that reaches track 81 and a writer that supports 11 sectors (Fastcopy, MSA-style tools, Gotek/HxC), with a sector skew.
A smaller bank (dropping the half-scale copies of the loop samples) would have fitted 80 × 11, but costs 4.3% → 5.5% of a frame for the player's own engine, so it was not done.

**Two-disk alternative** (`--two-disk`): standard formats only. Disk 1 is the original 81 × 10 layout without the bank; disk 2 is a 720 KB disk with the bank. On STE-class machines a prompt asks for disk 2 (drive A, or drive B without swapping); RETURN or fire loads, SPACE or ESC skips to the YM sound; from drive A the loader asks for the game disk again. A plain ST never asks. Use it only if the single-disk format cannot be read or written.

**Load times**, Hatari with real floppy timing, STE 1.62, key at the "Paper Bag" screen until MAIN OPTIONS (±8 s):

| Disk | Our stage done | Key → MAIN OPTIONS |
|---|---:|---:|
| Original Paper Bag, 81 × 10 | – | 39 s |
| Lean build (81 × 10, no bank) | 15 s | 42 s |
| Shipped: 82 × 11, bank read by raw track reads | 20 s | 51 s |
| 82 × 11, bank read with plain file reads (not shipped) | 24 s | 51 s |

So the patched disk takes about 12 s longer to reach the menu: about 3 s for our stage and 5–9 s for the 124 KB bank (the bank is not read on a plain ST). The game's own loading takes 27 s either way.

**Cold boots** (Hatari, patch marker `HNPO` = every site applied): STE 1.62 1 MB (shipping disk, in the 3D view after 89 s, 4.8 fps), Mega STE 2.06 4 MB (226 s including the TOS memory test, 4.8 fps), ST 1.04 1 MB (5.6 fps with fast floppy emulation; the 3D view was not reached in the slow-timing run because the blind menu clicks missed), lean STE (5.0 fps, YM sound), two-disk with disk swap on STE (prompt after 22 s, 3D view after 103 s). **Saving** works on the extended disk (ESC → Disk Operation → Save Game): the game returned to the 3D view, the disk's directory and our files stayed intact, `fsck.fat` found no errors. Loading the save again was not tried.

## 6. Tried and dropped

- **`p4_col`** (skip the colour set-up when a polygon repeats the previous colour). Identical output, but +0.05 to +0.16% *slower*: consecutive polygons rarely share a colour, and the compare costs more than it saves. File deleted.
- **Merging the template copy with the dither fill.** The premise was wrong: `$c84a` already draws every row of the 3D window once; `$c91a` is the HUD copy.
- **Span fill trimming.** The middle loops are 44–49% of the fill cost, but only 3.8–4 groups per multi-group span; unrolling or `movem` pays only from about 8. Estimated at most 1.2% for 16 generated routines: not done.
- **Keeping span masks between rows.** 36% of spans repeat the row above, but keeping the masks costs about 116 cycles against 130 to recompute.
- **Vertex-transform cache.** The inputs repeat when the camera is still (up to 82% hits), but while moving the matrix changes every frame, so walking gains nothing, and the lookup costs about 100 cycles.
- **Timing patch.** Not needed: the world speed is already based on the 50 Hz counter.
- **Three-voice mixer at 12.5 kHz.** Estimated up to about 27% of an already saturated game; replaced by two voices at 6,258 Hz after listening to the previews.
- **Replicants floppy as the base.** A different game build, permanent trainer; Paper Bag is identical to PP's.
- **Floppy-only fixes that were not needed:** loader rewrite (a .st cannot express interleave, and 11 sectors per track cost nothing in Hatari).

## 7. Known limits

- **No real hardware was used.** All testing is in Hatari 2.6.1. In particular the STE DMA sound (Microwire defaults, the DMA position read, the 6,258 Hz register behaviour) and real 11-sector, 82-track floppies are untested; the file cache on the floppy is smaller than the original, which may reload some files (not measured).
- **Speed gain is modest at 8 MHz** (about 6.5–14% fewer cycles per frame, 4.5 → 5.0 fps standing in the real boot), because frames are quantised to whole refreshes.
- **Sound.** Each voice has half scale (6–7 bit) so two never overflow, so distant sounds are coarse. Native rates up to 9.4 kHz are stepped to 6,258 Hz without filtering (some aliasing on explosions and bullets). Request-to-sound latency is 23–38 ms. A stopped engine fades out one step per frame, as on the ST, not instantly as on the Amiga. Effects 0, 8, 9, 12 and 16 were never heard live.
- **Floppy.** The two-disk set's second-drive and skip paths were not re-run after the file-cache fix, nor were TT and Falcon. Plain-ST single-disk reached the title but the harness's blind menu clicks missed in the slow run. Minimum 1 MB: below that the stage leaves the game unpatched.
- **`huntab.py`** (the identical-picture gate) was not rerun on the floppy build: the patched code and all bytes it reads are PP's HD ones [inference].
- **Patched `START.TOS`** only works with a disk the game can read through the HDDRIVER/AHDI route PP described; the harness tests used HDDRIVER V10.15 on ACSI.

## 8. TT and Falcon

See `work/notes/ttfalcon.md`. Summary: the floppy build runs to the 3D view with DMA sound on TT 3.06 and Falcon 4.04 in Hatari (the original Paper Bag floppy does not: its FDC time-out loop is CPU-speed dependent); the HD build runs on TT 3.06 (ACSI + HDDRIVER; the unpatched game does not, because PP's cookie jar claims a Falcon); the Falcon HD build could not be tested (HDDRIVER 10.15 does not see Hatari's IDE/SCSI drive).

## 9. Delivered

- `dist/Hunter_patched_hd_<date>.zip`: folder `HUNTER/` with PP's files, the patched `START.TOS`, `FILES/P` (patches plus sample bank) and `PATCHES.TXT`.
- `dist/Hunter_patched_floppy_<date>.zip`: `HUNTER_disk1.st` (one disk, 82 × 11) and `README.TXT`.
- `dist/Hunter_patched_floppy_2disk_<date>.zip`: the standard-format two-disk alternative.
- `tools/play.sh` (launcher for any machine, HD or `--floppy`, `--original`) and `tools/package.sh`.
- The patch tool, 4 default patches (`p4_ikbd`, `p4_edge`, `p4_poly`, `snd_core`), the study notes and the test tools.
