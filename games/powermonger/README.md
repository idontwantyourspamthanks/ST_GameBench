# Powermonger (1990, Bullfrog / Electronic Arts)

Status: **done** (release packaging, 2026-11-10). A patched floppy and a patched hard-disk folder are built from the user's original disk. Triple buffering (`p7_*`) is not in this build yet (see REPORT.md section 12).

- Plain-English account of the work: [`REPORT.md`](REPORT.md). Regression matrix: [`work/notes/regression.md`](work/notes/regression.md). Plan and decisions: [`PLAN.md`](PLAN.md).
- Build and package: `tools/package.sh` (verifies the patches, builds both versions, writes `dist/Powermonger_patched_floppy_<date>.zip` and `dist/Powermonger_patched_hd_<date>.zip`, prints md5s). Needs `disks/protected.st`.
- Play in Hatari: `tools/play.sh` (patched floppy, STE), `--hd`, `--original`, `--machine st|megast|ste|megaste|tt|falcon`, `--ram`, `--mhz`.
- Patch tool: `tools/pmpatch.py verify | list | build [--floppy|--hd] | live | boot`.

### Release md5s (default patch set, no triple buffering)

| File | MD5 |
|---|---|
| original `disks/protected.st` | `b0f6972e81067a5822c0b21e6d00b8dc` |
| `Powermonger_patched.st` (floppy, 819200 B; the build is deterministic) | `2034757f0a116358e13799492b5e7e4a` |
| HD `AUTO\WAR.PRG` (312653 B) | `d9f265af9c8568b3e4a81084570621f4` |
| HD `DATA\SPRITE40.DAT` (101608 B, patched) | `ec8579b97e7c35078d63b7d4439eedb0` |
| HD `PMLATE.DAT` (23285 B) | `cd0f828d007a68497c7b5f11d1779290` |
| `dist/Powermonger_patched_floppy_2026-11-10.zip` (the zip md5 changes with every packaging run: file times) | `1f03ac3a24e3194ff30459dd72e77693` |
| `dist/Powermonger_patched_hd_2026-11-10.zip` | `c93c6c21976651021ec856324d734ee1` |

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

Works: floppy boot, 1 MB STE, TOS 1.62 (`hatari --machine ste --memsize 1024 --tos tos/TOS_1_62.img --disk-a games/powermonger/disks/protected.st`).
Does not work yet: GEMDOS-folder run of the original (it reaches the title screens, then dies with an address error). See the notes.
