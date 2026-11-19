# Powermonger (1990, Bullfrog / Electronic Arts)

Status: **done** (v1.1, 2026-11-19: Retire / win / lose no longer crashes, `pm_cachecap`; combined release build 2026-11-10). A patched floppy and a patched hard-disk folder are built from the user's original disk. Default patch set = fixed-rate world, DMA sound, faster drawing, men interpolation, no protection question, tooltips **and keyboard shortcuts and village hover (`qol_*`)**, **triple buffering (`p7_*`)**, **TT / Falcon pointer fix (`tt_ptr`)**, **real-time intro (`pm_intro_*`)**, **rain on every frame (`tick_rain`)**, **IKBD overrun fix (`p6_cpy` 4-row chunks + `p4_clamp`)**, **resource-cache cap (`pm_cachecap`, v1.1: the Retire / win / lose picture no longer overwrites the patch code; the game re-reads that picture from disk instead of caching it)**, version credit. Proof of the combined set: [`work/notes/combined.md`](work/notes/combined.md). **Fix 2026-11-11:** the letters typed at the name prompt were replayed as icon clicks when the map appeared, so the first level started with a command selected / the troops out of their circle; only keys typed in the map view count now ([`work/notes/phantom_click.md`](work/notes/phantom_click.md)).

**v1.2 (2026-11-19): Mega STE at 16 MHz with the cache on** (`pm_mste`, default yes). A Mega STE powers up at 8 MHz (speed / cache register `$FF8E21` = 0) and nothing in TOS 2.06, HDDRIVER or the game writes it, so the patched game ran at 4.5 fps there. The loader's `init` (floppy and HD builds alike, before the game has run an instruction) writes `$03` = 16 MHz + cache when (1) the `_MCH` cookie is an STE-family one (high word 1), (2) a bus-error-guarded read of `$FF8E21` answers and (3) it reads 0; a non-zero value (the user set the speed / cache before starting) is left alone; ST / STE / TT / Falcon and a machine without a cookie jar are not touched. **A 0 cannot be told from an explicit 8 MHz without cache: it is raised too**; there is no way back to 8 MHz while the game runs (no desktop / control panel), the only 8 MHz Powermonger is the v1.1 zips (still in `dist/`). The value is the constant `MSTEVAL` in `patches/pm_mste.s` (`$02` = 16 MHz without cache: only +12 % in Hatari, `work/notes/mste16.md`). **The cache is unproven on real hardware / MiSTer** (DMA-written code, self-modifying code). Notes and gates: [`work/notes/mste16.md`](work/notes/mste16.md).

- Plain-English account of the work: [`REPORT.md`](REPORT.md). Regression matrix: [`work/notes/regression.md`](work/notes/regression.md) (release candidate) and [`work/notes/combined.md`](work/notes/combined.md) (final set, per-machine table). Plan and decisions: [`PLAN.md`](PLAN.md).
- Build and package: `tools/package.sh` (verifies the patches, builds both versions, writes `dist/Powermonger_v<ver>_patched_floppy_<date>.zip` and `dist/Powermonger_v<ver>_patched_hd_<date>.zip`, prints md5s). Needs `disks/protected.st`.
- Play in Hatari: `tools/play.sh` (patched floppy, STE), `--hd`, `--original`, `--machine st|megast|ste|megaste|tt|falcon`, `--ram`, `--mhz`.
- Patch tool: `tools/pmpatch.py verify | list | build [--floppy|--hd] | live | boot`.

### Release md5s (v1.1 = final default patch set: keys, hover, triple buffering, TT / Falcon pointer, intro timing, rain, IKBD fix, resource-cache cap)

| File | MD5 |
|---|---|
| original `disks/protected.st` | `b0f6972e81067a5822c0b21e6d00b8dc` |
| `Powermonger_patched.st` (floppy, 819200 B; the build is deterministic) | `ba7cae54412e84b728e48b78dac954e3` |
| HD `AUTO\WAR.PRG` (316841 B) | `ed259a3ff25455d89221885a0563aaea` |
| HD `DATA\SPRITE40.DAT` (101608 B, patched) | `37d28ff241b94d3f493f24e236e5a73b` |
| HD `PMLATE.DAT` (26439 B) | `792409e029e1fb0c10c43333f29d1122` |
| `dist/Powermonger_v1.0_patched_floppy_2026-11-11.zip` (the zip md5 changes with every packaging run: file times) | `fabc701e02e1bdc0f149f2fa2adb240f` |
| `dist/Powermonger_v1.0_patched_hd_2026-11-11.zip` | `d1df1e73f001073fdc61f02096fc9d98` |

The previous release candidate (no triple buffering / keys / rain; `work/notes/regression.md`) was floppy `3d116a3272af50ddc9d3a5bd39dc0a58`, `WAR.PRG` `eb143fd0d92579f1fa58097de090161a`.

The HD folder also holds `DATA\*.DAT` (14 other files, identical to the disk's) and `SAVEDISK.DAT` (409600 B, a formatted empty save disk). The zips' READMEs: `patches/README_FLOPPY.TXT`, `patches/README_HD.TXT`.


Game files are git-ignored. Put your own copies here:

- `disks/`: the floppy images, named as in the table below;
- `extracted/<variant>/`: files extracted from each image, e.g. with `MTOOLS_SKIP_CHECK=1 mcopy -s -m -n -i disks/<v>.st :: extracted/<v>/`.

## Images (all 80 tracks, 10 sectors/track, 2 sides, GEMDOS FAT12, 2 sectors/cluster, BPB media `$F9`)

| Variant (`disks/`) | Source name | Size | MD5 | Boot sector | Main program (MD5) | Notes |
|---|---|---|---|---|---|---|
| `protected.st` | `[protected]` | 819200 | `b0f6972e81067a5822c0b21e6d00b8dc` | executable, "Boot 60hz III" | `AUTO/WAR.PRG` 286384 (`d569e03e487fc47011658187c361097e`) | original code, no crack wrapper |
| `007.st` | `[cr 007]` | 819200 | `8aac3a2554550e49218dec840a8ff905` | not executable | `POWERMON.007` 286384 (same MD5 as above) + 25667-byte `POWERMON.PRG` unpacker/intro | German release, ~25 s to unpack, no AUTO folder |
| `empire.st` | `[cr Empire]` | 829440 | `b8f928bc1d09a420c5478baa8bd15615` | blank, not executable | `AUTO/WARI.PRG` 293673 (`da6e5685337e59af5bf0dccd0334b2f6`) | 81 tracks; extra 10240 bytes after the 80th track |
| `empire_t.st` | `[cr Empire][t]` | 819200 | `6bed1003543565dcf3621dfd638ab2e9` | blank | same `WARI.PRG` | only `DATA/SPRITE40.DAT` (+3288 bytes) and the boot-sector serial differ from `empire.st` |
| `empire_t_b.st` | `[cr Empire][t][b]` | 819200 | `184f0714a69e32be2e14f4761fddc651` | blank | same `WARI.PRG` | byte-identical to the first 819200 bytes of `empire.st` |
| `replicants.st` | `[cr Replicants]` | 819200 | `2c1ec7a9ed74fbfc9fcdc74fd8beefb7` | executable (TDT/Altair anti-virus) | `WAR` 278624, Pack-Ice `Ice!` (`61989e34a60915d9456de54c9e47f7d1`), `MREP` 6524 `Ice!` | `AUTO/POWER.PRG` loads `A:\WAR` and `A:\MREP`; its `WAR` is not the original program |
| `replicants_t2.st` | `[cr Replicants][t +2]` | 820224 | `35876120f7f604c63f9279f9f6318371` | executable, `601c` | `AUTO/WAR.DAT` 286384 (`9117fcab17bf2a07cf74579d7df5ff69`) + `AUTO/INTRO.PRG` 1754 (Automation Packer v2.3r) | `WAR.DAT` = original with 4 bytes changed; 1024 zero bytes after track 80 |

Data files (`DATA/*.DAT`, 15 files) are identical in every variant except `SPRITE40.DAT`:
`241a3d5b…` (101608 B) in `007`, `protected`, `replicants`, `replicants_t2`; `78f36f9e…` (137816 B) in `empire`, `empire_t_b`; `bfa29c7e…` (137816 B) in `empire_t`.

## Recommended base

`disks/protected.st`. Its `AUTO/WAR.PRG` is the unmodified original program, byte-identical to the one inside `007` and (wrapped) inside `Empire`.

## Running

Works: floppy boot, 1 MB STE, TOS 1.62 (`hatari --machine ste --memsize 1024 --tos tos/TOS_1_62.img --disk-a games/in_progress/powermonger/disks/protected.st`).
Does not work yet: GEMDOS-folder run of the original (it reaches the title screens, then dies with an address error). See the notes.
