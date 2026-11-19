# Real-floppy report (v1.4, STE + Mega STE): investigation, 2026-11-19

Report (downloader, v1.4 floppy set): "problems getting this to real floppies. Most image writers say they're corrupt images. Best results with
DOS and makedisk. Module music starts playing, but no disc activity anymore, even with the graphics disk. It doesn't freeze. Tried STe and MegaSTe",
plus a screenshot of the game's ask for the graphics disk.

Evidence labels: **[MEASURED]** = raw output reproduced here (files under `work/realfloppy/`, Hatari traces `/tmp/mwrf/*/fdc.trace`, RAM, so gone after
a reboot; the numbers quoted below are the record), **[SOURCE]** = read in code (game disassembly `tools/m68dis.py work/dumps/ram_boot_fl1mb.bin`,
Hatari source), **[INFERENCE]** = not proven. Nothing here was run on real hardware. Hatari 2.6.1-devel (`~/Code/AtariST/hattari/build/src/hatari`),
private HOME, `--fastfdc no --trace fdc`, one instance at a time. Scratch: `work/realfloppy/` (`drive.py` driver, `ffa.py` image reader, `mkvariant.py`
variant builder, `an.py`/`an.out` image analysis, `b_*.out` run logs, `v13/ v14/ v15/` unzipped sets, `var_to44/` test image). Nothing tracked was edited.

## 0. Short answer

* **(A) "corrupt images":** the files are plain raw `.st`, 737 280 B (80 tracks x 2 sides x 9 sectors), a size every writer knows. What is not standard is
  the **boot sector**: only FFD has a valid BPB. FFB (graphics) and FFC (missions) have **no boot sector at all** (sector 0 is the game's own file directory,
  `grafix00` / `mission0`, so byte 13 = sectors-per-cluster = 0 and bytes-per-sector = 0); FFA keeps the original game boot sector with a **bogus BPB**
  (10 sectors/track, 1 side, 800 sectors, 0 FATs). Any writer that validates or derives the geometry from the BPB (Hatari's own "Pacifist/Makedisk bug"
  heuristic, DOS/Windows image tools, `fsck.fat`/mtools) calls FFA/FFB/FFC corrupt; writers that go by file size accept them (HxC, Greaseweazle with a
  format, Makedisk). Cannot be fixed inside the image: FFB/FFC byte 0..31 are the game's directory and the game's disk-identity check reads them.
* **(B) "no disc activity with the graphics disk":** the game has **no disk-change detection**: it identifies a disk by the bytes `graf` at sector 1 of a given
  track and re-reads on each key press. The check right after the boot expects the **start-up disk (FFA)**, not FFB (the screen text says "Insert Graphics Disk"
  both times). If that first check fails, the game probes drive B (no drive: 5 FDC time-outs = **10.9 s with the drive light off**) and shows a black
  "Insert Graphics Disk / press any key" screen; inserting FFB there can never pass, so every key press = a short light, then 11 s dark, then the same prompt. The
  v1.4 packaging makes that first check fragile: the patch payload sits on tracks 72-79, so at game start the head is on **track 79** instead of track 71 (original)
  and the game's first `restore` needs 2.15 s+ against a built-in time-out of 2.18 s (Hatari STE, 8 MHz); the original's is 2.006 s, i.e. **only 0.18 s of margin even on the
  untouched disk**. [MEASURED] Hatari lets v1.4 through by a hair (cut in the verify tail); a 15 % shorter time-out (or, [INFERENCE], real spin-up/step/clock tolerances) aborts the restore mid-stepping and the symptom reproduces exactly.
* **Ask the lead to look at the screenshot:** orange MIDWINTER II logo with "v1.4 enhanced by dad_prg" at the bottom = normal prompt; **black screen with only
  "Insert Graphics Disk / press any key" = the failed-check path** (section 3.4).

## 1. The images (task 1)

Zips: `dist/Midwinter2_v1.4_patched_floppies_2026-11-12.zip` (md5 c73fa148...), `..._v1.5_patched_floppies_2026-11-16.zip` (8a3a03e4...), also v1.3. Each holds
`FFA_boot.st FFB_graphics.st FFC_missions.st FFD_campaign_blank.st README.TXT`. No MSA/STX/DIM, no extra tracks, no 'HAGA' track, no interleave information
(a `.st` cannot carry it). `an.py` output [MEASURED] (`work/realfloppy/an.out`):

| image | md5 | size | /512 | BPB bytes/sec, spc, FATs, root, sectors, media, spf, spt, sides | byte13 | boot sum | verdict |
|---|---|---|---|---|---|---|---|
| FFA_boot (v1.4) | 01fce856... | 737280 | 1440 | 512, 2, **0**, **0**, **800**, **0x00**, 0, **10**, **1** | 2 | $1234 (exec) | BPB inconsistent with file (800 x 512 = 409 600 B); bootable; original game boot sector |
| FFA_boot (v1.5) | d34daade... | 737280 | 1440 | same | 2 | $1234 | same |
| FFB_graphics | 9d4ea2dd... | 737280 | 1440 | **0**, 0, 116, ... (garbage: it is `grafix00` + directory) | **0** | $3316 | no boot sector, no BPB |
| FFC_missions | 252d0ad0... | 737280 | 1440 | **0**, 0, 255, ... (`mission0` + directory) | **0** | $eb7f | no boot sector, no BPB |
| FFD_campaign_blank | 5e034299... | 737280 | 1440 | 512, 2, 2, 112, 1440, 0xf9, 5, 9, 2 | 2 | $9517 | valid BPB; FAT1 media byte f0 vs BPB f9 and FAT2 all zero (`fsck.fat`: "FATs differ", "Bad media types f0/f9") |

* Format: raw ST image, 80 cylinders x 2 heads x 9 sectors of 512 B, standard 720K, nothing beyond track 79 (so no 81/82-track or 10/11-sector problem), size
  multiple of 512, not MSA (no 0x0E0F header), no trailing data. FFB/FFC/FFD are **byte-identical in v1.3, v1.4 and v1.5 and to `FILES/FFB..FFD`** of the HD
  release. FFA differs from `FILES/FFA` only in: boot sector `$B4-$1A2` + checksum byte `$1FF` (see 3.1), stub `$2FA-$2FD` and `$604-$623` (stage 1), directory
  entry 10 `$2458-$245F`, and the payload track-sides (v1.3/v1.4: image `$A2000-$B1DFF`, track-sides 72-79 of side 0; v1.5: payload + Amiga sample bank 209 330 B on
  track-sides 81-126 = side 1, tracks 1-46). The game addresses a disk as 160 "track-sides": n < 80 = side 0 track n, n >= 80 = side 1 track n-80
  (`sub_02772c`: `divu #80`). FFA uses side 0 only (plus ts 80 and, from v1.5, side 1 tracks 1-46); FFC side 0 only; FFB all 160.
* Tools [MEASURED]: `file` says "data" for FFA/FFB/FFC; `fsck.fat -n`: FFA "only 1 or 2 FATs are supported, not 0", FFB/FFC "Logical sector size is zero";
  `mdir -i`: "non DOS media" (all four; FFD fails too on the FAT-media mismatch). Hatari: inserting FFB (and the original FILES/FFB) logs
  "WARN: Disk in drive A: maybe suffers from the Pacifist/Makedisk bug. If it does not work, please repair the disk first!"; source `src/floppy.c`
  `Floppy_IsBootSectorOK`: the disk is flagged "bad" when byte 13 (sectors/cluster) == 0 **and** the boot sector is not executable ($1234 sum), the comment
  says "Such images cannot be read correctly using a real ST", and a flagged image is never written back (this also explains the README's Hatari campaign
  creation failure: the game overwrites FFD's boot sector with `camp...`, byte 13 = 0, so Hatari discards the writes [SOURCE; not re-run]).
* HxC `st_loader.c` (read from GitHub): uses the BPB only when `bps*spt*sides*512 == file size`, otherwise falls back to a size table (737280 = 80x9x2): FFA/FFB/FFC
  load fine. Greaseweazle's IMG class needs an explicit format, no BPB check. Makedisk `/write ... /auto` is documented only as "writes the image"; the user reports it
  worked. [INFERENCE] The writers that "say corrupt" are BPB-validating ones (typical Windows/DOS tools; I do not know which the user tried). Not proven.
* README.TXT (v1.3-v1.5) says only: "Needs 1 MB RAM, a double-sided 80-track drive. The disks are standard 720K .ST images (9 sectors, 2 sides, 80 tracks)" and
  "Tested in Hatari 2.6.1: STE TOS 1.62 and Mega ST TOS 1.04". Nothing on how to write real disks (no tool, no DD-media remark, no warning that FFB/FFC carry no boot sector
  and may be flagged by writers, nothing on drive B, nothing about the black prompt), and floppy.md/README never claimed a real-drive test: **no real drive or real STE was ever used.**
* Writer hint: the images **must be written raw as 80x2x9 sector-for-sector**. A writer that follows FFA's BPB (10 spt, 1 side) writes a disk the game cannot read.

## 2. How the game identifies a disk, and what our patches change (task 2)

### 2.1 The original loader (no disk-change detection) [SOURCE, `ram_boot_fl1mb.bin` = RAM at game entry of an unpatched floppy boot]
* The game never uses TOS after the boot sector: `sub_026570` installs all vectors (`$118` ACIA, `$70` VBL, `$68`, `$120`, ...). No `hdv_*`, no GEMDOS/BIOS, no media-change
  (`$ff8604` WP bit 6 is read only before a **write** pass, `sub_02772c`).
* Disk identity = `sub_028b20`: `sub_0277c6` reads **sectors 1-3 of track-side `[$e544]`** into `$e576/$e776/$e976`, then compares the NUL-terminated string at `[$93ca]` with the data:
  `graf` (graphics, `$9ba3`), `pers`, `camp`, `mission` (`$9b98`), start-up = `60 3a` (boot sector bytes). On a mismatch it toggles the drive select word `[$27d34]`
  (2 = A, 4 = B, `eori.w #6`) and tries the other drive once; if both fail `sub_028b9e` draws a **black** screen "`<Insert X Disk>` / press any key" (`$93ce` text, `$13187` "press any key"), selects no
  drive (`sub_027786`), waits for key release then press (key latch `$7684`, `$4f66`), and loops back. The loop retries with `$e546 = $ffff` (restore + seek first).
* `$e544` is 1 for the first check in `sub_01f4fc` (`$1f50a`) and 0 afterwards (`$1f54e`): **the first check reads track 1, where FFA's own directory (`grafix00`) is, so
  it is satisfied by FFA, not by FFB** (FFB has `grafix00` at track 0, FFA's track 0 is the boot sector). The orange logo with the static "Insert Graphics Disk / press any
  key" (`$1f5fc..$1f636`, drawn unconditionally, key wait) comes after that first check; the check after the key reads track 0 and wants FFB.
* FDC driver (`$27ac4..$27d38`): one DMA command per 512-byte sector (sectors 1..9 sequentially), status never checked per sector; correctness only by the file XOR checksum
  (`sub_027a14`, retried 3x with restore, then the prompt); drive/side via PSG port A (`sub_027cfc`, bit0 side 0 = high, bit1 A / bit2 B active low); `sub_027a38` = `restore` (`$05`: r=12 ms,
  V=1, h=0 => spin-up), `sub_027a4e` = `seek` (`$15`), `sub_027a86` = `step in` (`$55`) per track; **every command waits at most `$50000` iterations of `btst #5,$fffa01` (`sub_027caa`)
  and then sends `force interrupt $d4`** and carries on. Hatari measured: 2.18 s on an STE at 8 MHz.
* Not applicable on this game: instant media change, WP toggle, `$ff8604` fakes (the game does not read the WP/ready bits for reads), TOS hdv vectors, BPB.

### 2.2 What the floppy patches change (68000 machines) [SOURCE + MEASURED]
* Boot sector: the final `jmp $4d9a6` becomes `bra.w $ca`; the block at `$CA..$1A2` (`floppy_cpu.s` + `cpulib.s`) runs `cl_detect` (index-register scale probe) and on a 68000/68010 returns
  immediately and jumps to the stub: inert on ST/STE/Mega STE. Boot sum stays `$1234`. Branches to unmodified `$4d9a6` code.
* Stub: `jmp $3104` -> `bra.w $4DDAA` (stage 1 in dead code), which calls the stub's own loader for file 10 (the payload) and jumps to the trampoline `$B3000`
  (`core.s`; `cpufix` returns at once on a 68000; applies the sites; `jmp $3104`). No change to any FDC routine on a 68000 (`fdctab`/`st_tab` are only for 68020+).
* `floppy_copybuf` (`$e566`: 80 -> 40 track-sides): only the campaign/backup copy.
* All other patches: speed/render/controls/joypad/credit, never touch the FDC or the disk logic. `jag_poll` probes `$ff8e01` (guarded; Hatari logs one harmless
  `Bus Error reading at address $ffff8e01, PC=$b9706` on an STE), nothing disk related.
* **The one change that matters for drives: the payload is read LAST by the stub, from track-sides 72-79, so the head is on track 79 when the game starts.** The unpatched floppy ends boot
  with the head on **track 71** (end of file 9; Hatari trace of the original: the game's first `restore` at `tr=0x47`, `pc=27c4e`, takes 2.006 s). v1.5 puts payload+bank on track-sides 81-126
  (last ts 126 = side 1 track 46): first game `restore` at `tr=0x2e`, 1.671 s.
* First game `restore` (spin-up is needed: the 1772's motor timer is 10 index pulses = 2 s, the game starts its first command ~1.5-1.9 s after the last stub read [MEASURED: 1.9 s STE]):
  spin-up 6 index pulses (1.0-1.2 s) + `head` steps x 12 ms + 15 ms settle + verify. Time from the command to completion or to the game's force-interrupt, Hatari STE 8 MHz [MEASURED,
  from `fdc.trace`, video_cyc differences]:

| image | head at game start | restore result | duration |
|---|---|---|---|
| original `FILES/FFA` | track 71 | completes | **2.006 s** (margin 0.18 s to the 2.18 s time-out) |
| v1.5 | track 46 | completes | 1.67 s (margin ~0.5 s) |
| **v1.4 (and v1.3)** | **track 79** | **cut by the game's own force interrupt `$d4`** (`type IV force int ... pc=27c4e`) | **2.182 s** = the time-out; restore needs 1.2 + 0.95 + verify >= 2.17 s |
| v1.4 with the time-out `$50000` -> `$44000` (test image `var_to44/`, 85 %) | track 79 | aborted **mid-stepping** at 1.85 s: `seek dest_track=0x1 ... tr=0xc0 head_track=0x10` | see 3.4 |

  In stock v1.4 Hatari the abort lands in the verify tail (TR=0 and head 0 are already correct afterwards), so it still works. [INFERENCE] On a real drive the spin-up phase
  (the first index pulse comes 0-200 ms after the command), the real step time, the head settle and the E-clock-synchronised MFP polling loop all shift this by tens of ms either way.
  The abort in the stepping phase is the failure; v1.4 is at the stock timing limit, the original 0.18 s (8 %) inside it, v1.5 0.5 s inside it. (The stub's own restore, `pc=4dd8e`, from track 71 takes 0.88 s: no spin-up, different time-out.)

## 3. Hatari reproduction (task 3)

All runs: cold boot, `--fastfdc no`, disk A = FFA, drive B disabled unless stated, wait until the FDC trace idles at the prompt, then swap/press. Driver: `work/realfloppy/drive.py`, logs `b_*.out`.

### 3.1 Normal swap sequences: no symptom [MEASURED]
| run | swap | after the swap + key press (trace growth) |
|---|---|---|
| STE TOS 1.62, v1.4, `hatari-option --disk-a ffb.st` at the logo prompt (instant) | instant | 138 B at the swap (just the media-change bookkeeping), 138 KB within 4 s of the first key, loading continues; `restore`, `seek 0`, 3 sector reads at track 0, passes, loads FFB files |
| same, eject (`--disk-a ""`), 3 s, insert, 3 s, key | with delay | 138 B at the swap, 122 KB within 4 s of the key: identical |
| same, key pressed **with FFA still in** (wrong disk), 30 s, then swap + key | wrong first | key: 17 KB (restore, seek 0, read 2 sectors of track 0: no `graf`; then drive B: `restore/seek/read/read/read` each cut by force interrupt, **546 VBL = 10.9 s with drive A deselected, no FDC activity**), then the game goes on; after swap + key: 76 KB within 4 s |
| Mega STE TOS 2.06, 8 MHz (status bar; `--cpuclock 16` on the command line was **not** honoured, run `b_mste16_instant`), v1.4, instant | instant | 133 KB within 4 s, works. First game restore from track 79 ran without spin-up (motor still on) and completed |
| Mega STE TOS 2.06, **16 MHz** (runtime `hatari-option --cpuclock 16`, status bar "16MHz", 60 Hz screen; `b_mste16_runtime.out`), v1.4, instant | instant | 667 KB (verbose trace, fast CPU) within 4 s of the key: works. See 3.3 |
| unpatched original FFA/FFB, STE, instant | instant | 129 KB within 4 s: works |
| v1.5, STE, instant | instant | 58 KB within 4 s (+ the 209 KB payload loading), works |

The first (wrong) experiment in my own logs (`b_ste_instant.out` run 1, hatari "Cannot insert same floppy to multiple drives": Hatari auto-inserts `<name>B.st` into drive B when the disk A
name ends in `A.st`; the error dialog froze emulation) was a harness artefact and is not evidence. **Hatari tolerates an instant swap, because the game never looks at a change flag;** instant vs delayed
swap makes no difference to the game, and Hatari does not hide a change signal the game wants.

### 3.2 Disk A: the sector timing Hatari assumes
[MEASURED] After the first sector of a track (10 VBL = a revolution wait), each next sector read starts 1 VBL (20 ms) later: Hatari finds sector n+1 without losing a revolution. The loader's host latency
between two commands is ~1.5-1.7 ms at 8 MHz [SOURCE: 3 DMA address writes, 3 x `sub_027c4a` pairs of `dbra #$60` delays etc.]. [INFERENCE] On a real disk this works only if the physical gap after the data CRC
is >= that latency; with a PC-formatted disk (Makedisk's GAP3 unknown) every sector may cost one revolution (9 x 0.2 s per track, ~100 s for the 240 KB game file instead of ~50 s). Slow, not a failure.

### 3.3 Mega STE
16 MHz Mega STE run [MEASURED, `/tmp/mwrf/b_mste16_runtime/fdc.trace`]: the game's FDC time-out is **1.08 s** (65 VBL at 60 Hz between `restore` and its `force int` for the second game restore from track 8, `restore tr=0x8 VBL=3018` -> `force int VBL=3083`; same for
`tr=0x10` 5728 -> 5793, `tr=0x2f` 5973 -> 6038): every `restore` that needs the **spin-up (1.0-1.2 s)** is cut by the time-out at about the end of the spin-up. The first restore from track 79 happened to run without spin-up (the faster game init stays inside the 1772's 2 s motor window): 58 VBL = 0.97 s, completed with 0.1 s to spare.
Hatari's spin-up always outlasts the time-out, so the abort lands harmlessly in the spin-up (TR and head untouched). [INFERENCE] On a real drive the spin-up ends 1.0-1.2 s after the command depending on where the first of the 6 index pulses falls: when it ends before 1.08 s the abort lands in the first
steps of the restore (TR = 255 - n, head at 79 - n), exactly the state of 3.4, with a probability of the order of 10-40 % per cold restore, for ANY head position, **including the original disks** (a restore from track 8 needs 96 ms of stepping). So a 16 MHz Mega STE can hit the same trap even with the unpatched game; the 8 MHz STE only with a long restore (original track 71: 0.18 s margin, v1.4 track 79: none).

### 3.4 Symptom reproduction: abort of the first `restore` mid-stepping [MEASURED]
Test image `var_to44/FFA_boot.st` = v1.4 FFA with the game's FDC time-out long `$27cb0` set from `$00050000` to `$00044000` (in file 9; directory XOR checksum fixed: `mkvariant.py`).
Result (STE 8 MHz, `b_ste_to44.out`, trace `/tmp/mwrf/b_ste_to44/fdc.trace`):
```
restore (head 0x4f)            ... force int 0xd4 at 1.85 s        (mid-stepping)
seek dest_track=0x1 ... tr=0xc0 head_track=0x10                    (TR 192, head track 16: out of sync)
seek ends tr=0x0 head_track=0x0 ; read sector 1,2,3 of track 0 (not 1!) -> no 'graf'
drive B probe: restore/seek/read/read/read, each ends in force int, 5 x 1.85 s = 9.3 s, drive A deselected
black screen: "Insert Graphics Disk / press any key"   (screenshot work/realfloppy/to44_prompt.png)
```
Then FFB swapped in and a key pressed: restore, `seek dest_track=0x1`, read sectors 1-2 **of track 1** (FFB's track 1 is code, no `graf`), drive B probe again (5 force interrupts: dark for 9.3 s), prompt again. Trace growth after
swap + 3 key presses (12 s): 16 KB, 22 KB, 25 KB (a short burst, then silence), versus ~140 KB/4 s in the normal runs. **This is the reported symptom: light for a moment (or not at all), nothing happens with the graphics disk, no freeze, music keeps playing from the VBL.**
**Way out, reproduced** (`b_ste_to44_keyfirst.out`, same test image): at the black prompt press a key **with FFA still in drive A**: the first check (track 1) passes (trace growth 215 KB in 5 s, 651 KB in 10 s), the game loads on and reaches the **orange logo with
"Insert Graphics Disk / press any key / v1.4 enhanced by dad_prg"** (`/tmp/mwrf/b_ste_to44_keyfirst/wrongdisk.png`); swapping FFB in there and pressing a key works (127 KB in 4 s, 358 KB in 12 s). So the black screen is
not "wrong disk" in the user's sense; it asks for a disk that only FFA satisfies.

## 4. Conclusions: ranked hypotheses

### (A) corrupt images
1. **BPB-validating writers (high):** FFB/FFC have byte13 = 0 / bytes-per-sector 0 and no boot sector, FFA's BPB contradicts its size; this is exactly what Hatari's own heuristic and `fsck`/mtools reject and what a BPB-driven
   writer would refuse or mis-geometry. Evidence: section 1 tables, Hatari warning, `floppy.c` source. Unproven which writers the user tried.
2. A writer that follows FFA's BPB (10 sectors, 1 side) writes an unreadable FFA (medium): the user got FFA to boot with Makedisk, so Makedisk uses the size; other tools may not.
3. HD (1.44 MB) media or an unformatted disk in a writer that formats from the BPB: [INFERENCE, low].
4. Not the cause: file size, extra tracks, MSA/STX/DIM confusion, non-multiple-of-512, 83/84 tracks: all ruled out above.

### (B) no disc activity with the graphics disk
1. **Failed first identity check -> black "Insert Graphics Disk" screen that only the start-up disk can satisfy, plus the 10.9 s dark drive-B probe (high that this is the *mechanism*, medium that it is what the user hit).** The mechanism is reproduced; what triggers
   the first failure on real hardware is open: (a) our v1.4/v1.3 head-on-79 layout is at the game's own restore time-out (section 2.2 table, [MEASURED] on the edge in Hatari; the original is 0.18 s inside, v1.5 0.5 s), so a real drive/STE/Mega STE can fall on either side; (b) a flaky
   read of FFA track 1 on a PC-written disk; (c) a mis-written FFA track 1 (the writer's geometry). (a) is the only one that is **our** regression versus the original floppy and is cheap to remove.
2. Wrong disk order on the user's side: pressing a key at the *orange* logo with FFA still in (the check wants FFB at track 0) gives the same 10.9 s dark period (reproduced, 3.1 row 3), and a user who inserts FFB at the *black* prompt can never pass (3.4). Both look like "no disc activity".
3. A single-drive machine always pays the drive-B probe on any failed check: 5 timeouts of ~2.2 s with drive A deselected (the light is off the whole time) [MEASURED]. On a 16 MHz Mega STE this is shorter, but not zero [INFERENCE].
4. Keyboard dead or the main loop stuck: the key wait is `sub_026fd0/$4f66` fed by the game's own ACIA handler (`$26882`) and nothing in our patches touches it before the first FDC use; no Hatari evidence of a stall; not excluded for real hardware [INFERENCE, low]. If the "music" in the report is the Amiga module
   music the user actually has v1.5 (the "module music" only exists in the v1.5 `asn_*` patches; v1.4 plays the YM tune); then 3.1's v1.5 row applies (head on track 46, 0.5 s margin), the black-prompt mechanism is unchanged, and the DMA-sound code is a second suspect (never run on real STE hardware, `amiga_sound.md`).
5. Hatari-vs-real differences checked and ruled out: instant disk change (the game has none), WP/ready bits (read only for writes), DMA above RAM (payload `$B3000-$BAFFF` and the copy buffer below it, 1 MB), 8 vs 16 MHz delays (only the time-outs matter, above), side select / drive select
   (standard PSG port A use, same as the original).

## 5. What the downloader should do now
1. If the screen is **black** with only "Insert Graphics Disk / press any key": **do not swap.** Press a key with the **start-up disk (FFA) still in drive A** and wait ~15 s (the first check wants FFA's own track 1). When the orange logo with "Insert Graphics Disk" appears, swap in FFB and press a key. [Reproduced in Hatari with the variant image, section 3.4; not tried on a real machine.]
2. Test the **unpatched** start-up disk (`FILES/FFA` of the HD zip, written the same way) as a control: it ends the boot with the head on track 71 and 0.18 s of margin (v1.4: none). If it works and v1.4 does not, the head-position race is confirmed; if it also fails, suspect the Mega STE 16 MHz case (3.3) or the writer.
3. Try v1.5's FFA (head on track 46, 0.5 s margin) instead of v1.4's.
4. Write all four disks raw, 80 x 2 x 9, **720K DD media**, with a size-driven writer (Makedisk `/write x.st /auto`, `gw write --format=atarist.720 x.st`, HxC); ignore "bad boot sector" warnings for FFB/FFC (they have none by design). Use drive A only, leave/disable drive B (a second drive costs nothing; an absent one costs 11 s of dark per failed check). On a Mega STE use 8 MHz, cache off (Control Panel) for the first test.
5. Leave the drive alone after the logo appears: the first checks can take 20-30 s (spin-up, restore, 3 sector reads, then possibly the 11 s probe) with a dark light.

## 6. Proposal for v1.6 (not applied)
1. **Park the head (fixes our regression):** after stage 1 loads the payload, read one sector of file 0 (track 0, image offset 0) with the stub's own loader (`$4DB52`, a6 = `$4E9D8`, file number word `$16(a6)` = 0, a harmless scratch destination in `[$4E9AC]`, e.g. `$4EC00`)
   so the game's first `restore` starts at track 0 with TR = 0: no stepping at all, so the abort-in-stepping window disappears at any CPU clock (restore at TR00 = spin-up only, ~1.0-1.2 s, 1 s of margin at 8 MHz); strictly better than the original (track 71). Costs 12 bytes in the dead stub block `$4DDAA-$4DDE9` (32 of 64 used). Alternative: move the payload to side-1 tracks 1-8 (ts 81-88: head ends on track 8, restore 0.1 s of stepping); v1.5's 81-126 is better than 72-79 but the bank leaves the head on 46.
2. **Lengthen the game's FDC wait on 68000 too** (`fdctab` is 020+ only): `$27cb0 $50000 -> $a0000` (4.4 s at 8 MHz, 2.2 s at 16 MHz). **This is needed in addition to item 1**: at 16 MHz the stock time-out (1.08 s) is shorter than the spin-up. Costs 2x on the drive-B probe; combine with 3.
3. **Skip the drive-B probe on single-drive machines:** the trampoline reads `_nflops` (`$4a6.w`); if 1, `nop` the `eori.w #$6,$27d34` at `$28b44` (8 bytes). Keeps the two-drive "campaign in B found without a prompt" behaviour; removes the 11 s dark loop (and its force interrupts) on the usual single-drive STE/Mega STE. [INFERENCE: `_nflops` is reliable on TOS 1.62/2.06.]
4. **Packaging:** ship `.msa` copies next to the `.st` (an MSA header carries the geometry, so BPB-less writers accept them; Makedisk reads both), a `WRITING_DISKS.TXT` (content: section 5 item 4 plus the black-prompt rule), MD5s, and a one-line statement that FFB/FFC have no boot sector by design.
5. **README additions:** how to write real floppies (tools and raw 80x2x9, DD media, ignore the boot-sector warnings), the black-prompt explanation ("press a key with the START-UP disk in"), the single-drive/drive-B note, "tested in Hatari only" -> "tested in Hatari; real-drive reports welcome".
6. **Tests to add** (`work/floppy_tests`): `--fastfdc no --trace fdc` run asserting the first game `restore` completes (`complete command`, no `type IV force int` before the first sector read) at STE 8 MHz and 16 MHz, from the shipped FFA; `var_to44`-style negative control (the check must fail the gate); original FFA as control.
7. Diagnostic build for the user (cheap): a v1.4 FFA with the head parked (item 1) so one disk answers (B)-1 conclusively.

## 7. Not done / limits
* No real drive, STE or Mega STE; every timing figure is Hatari's FDC and CPU model. The real margin of v1.4's first `restore` (the heart of hypothesis B-1) is unknown to within tens of ms: [INFERENCE] it explains the report only if the real timing falls on the abort side.
* 16 MHz Mega STE: only the Hatari model (above); the abort-in-stepping case at 16 MHz was not forced (variant image) - the argument is [INFERENCE]. Real clock/MFP wait states unknown.
* Did not test v1.4's FFC/FFD paths, the campaign creation, or other writers; did not identify which writers say "corrupt".
* Hatari's `Writing not possible` rule for FFD is read from the source, not re-run.
