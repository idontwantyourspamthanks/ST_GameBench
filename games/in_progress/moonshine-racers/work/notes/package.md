# Moonshine Racers v1.0 packaging (MSRPackage)

## Shipped files (CURRENT; clean build line `build: git a6f87f7`, HEAD a6f87f7525cb2fcfd02b08689ee5d2b2ea37c3e2)
Rebuilt after the packaging commit with `python3 tools/msrpatch.py build --out work/pkg/zhd --zip` and `build --floppy --out work/pkg/zfl --zip`; the superseded zips were deleted (one set in `dist/`, git-ignored).

| zip | bytes | mtime | md5 | sha256 |
|---|---|---|---|---|
| `dist/MoonshineRacers_hd_v1.0.zip` | 1,083,079 | 2026-11-18 01:30:45 | 1afefab5ef6ef752e20f6d0d618e23b2 | 0382275f51c21f22c9fb46ede02d938ca063ddce9d9ded74bf3499eae007c201 |
| `dist/MoonshineRacers_floppy_v1.0.zip` | 915,921 | 2026-11-18 01:30:46 | 9c07c7c9095d1a0324ff75c8b21454d6 | 36fce30cfc21fdec1180212cda3a15898ad6228c107700ba002185d6c435f580 |

Versus the previous zips (the set the Hatari cells' payload equals, differing from the cell set only in README wording): every member md5 is equal except `MOONSHR/README.TXT`, `MOONSHR_floppy/README.TXT`, `MOONSHR_floppy/PATCHES.TXT`, and `diff` shows the ONLY text difference is the build line (`build: git bafead9 + uncommitted ...` -> `build: git a6f87f7`). Payload members (RUNME.TOS, HAGA, FILES/*, disk_a.st `31e29c6ad340dfac6957b8f6c8bc3be5`, disk_b.st `0d0be455e4d0389ed98401c0e02d21d9`) equal those the cells ran on (`work/pkg/final3_all.md5` vs `final_all.md5`, `verified_all.md5`).

Previous (superseded, deleted) set, for the record: hd md5 7defac73..., floppy a9df2033... (build bafead9 + uncommitted).

## Docs
`patches/README_HD.TXT`, `README_FLOPPY.TXT`, `PATCHES.TXT`, `PATCHES_FLOPPY.TXT` are templates (`@VERSION@`, `{GIT}`, `{PATCHES}`, `{PATCHES_FLOPPY}`); `msrpatch.py build` renders them (HD README.TXT = ours + PP's original README.TXT appended verbatim; the floppy zip had no README before). Numbers quoted: integration.md 12.14 definition A (16.0 / 28.8 / 47.9; SAFE=3 15.3 / 1.5 % late steps from release_notes_draft), the floppy 15.8 / 26.6 (12.8). Nothing about real hardware is claimed.

## Content-vs-gate check
Two builds of the same tree state (`work/pkg/b1`, `b2`, HD and floppy): HD folder md5-of-md5s `dc2bb496c5eddf7f5fcbe520d43cfb63` twice; floppy disk_a.st md5 `31e29c6a...` and disk_b.st `0d0be455...` identical; the unzipped shipped files equal the build dir byte for byte (HD `diff` of the md5 lists: identical; floppy md5s equal).
**Process note**: the Hatari cells below ran on the zips built 01:0x (unzipped to `work/pkg/s`); afterwards I changed ONE wording in the two README.TXT templates ("orange title picture" -> "title picture (the hot rod ...)") and rebuilt; the md5 lists of the old and the final unzipped zips differ ONLY in `MOONSHR/README.TXT` and `MOONSHR_floppy/README.TXT` (`diff work/pkg/verified_all.md5 work/pkg/final_all.md5`); the game payload files (RUNME.TOS, HAGA, MS1/MS2/MSR_S1.FIC, disk_a.st, disk_b.st) were byte-identical, so the cells were not re-run. If the lead wants a strict "cells on the final zip" record, rerun `work/pkg/run_hd.sh` / `run_fl.sh` with the dirs pointed at `work/pkg/s2`.

## Shipped-zip cells (unzipped into `work/pkg/s/`, raw outputs `work/pkg/res_hd.txt`, `res_fl.txt`; Hatari 2.6.1)
HD (`cold_fin.py`, 8 MHz boot, then 16 MHz for the second window; 124 s play at 16 MHz after the windows; every cell: boot_to_race True, marker MSPO, RDG1 tables OK, `$1021=2` at all samples):
```
STE 1 MB TOS 1.62:  boot vbl 5808; native window 105 passes 9.981/s, 75 extras, 17.110 fps | 16 MHz 194 extras, 28.422 fps | play 124 s alive, 3 bus/address lines (expected, integration.md 12.15)
STE 4 MB TOS 1.62:  boot vbl 5812; native 75 extras 17.110 fps | 16 MHz 193 extras 28.381 fps | play 124 s alive, 3 lines
Mega STE 1 MB TOS 2.06 (60 Hz, boots 8 MHz): vbl 6046; native 133 extras 22.631 fps | 16 MHz 117 extras 21.109 fps | play 124 s alive, 0 lines, tb_car stock kernel (INIT 2)
```
(12.6 recorded 28.476 / 28.422 and 22.536 / 21.048: the small differences are run-to-run, not a different build.) STE `STRIP CHECK ..._b ... $78000 shadow==model(RAM) False` appears on both STE cells (script's second-buffer check after 25 s of driving); strip pixels != shadow render = 0 in all; Mega STE all True. [INFERENCE] a mid-draw buffer artefact of that script; not investigated.
Floppy, STE 1 MB TOS 1.62:
```
F1 swap route, LONE disk_a.st (work/pkg/lone) + disk_b.st given to gate: prompt True t 46 vbl 2412, story screens, MSPO, after swap vbl 4099 $1021/$100e (2,216); drive native 62 s ($100e 271->902, 381 extras), 16 MHz 22 s (574 extras), END MSPO RDG1, 2 bus/address lines, alive
F2 drive-B route insB (work/fdb/fdb.py, disk 2 inserted into B at the prompt): prompt vbl 2637, 100 sector reads on drive 1, race advancing ($100e 284->354), 30 s drive $100e 741, MSPO; RESULT OK
F3 startB (disk 2 in B from power-on): race reached WITHOUT the prompt ($100e 45->102, vbl 3260), 100 reads drive 1, drive $100e 934; RESULT OK
F4 `play.sh --floppy --no-driveb` equivalent build (same `--only` list play.sh uses; work/pkg/nodb, disk_a md5 47768891f6778727cedddf882103debe, disk_b original), one drive (--drive-b false), swap route with ONE failed key press first:
   failed check at the prompt: burst vbl 3660 -> 3662 = 0.04 s (1 sector read drive 0, B never selected), then swap: race advancing ($100e 287->357), 30 s drive 743, 100 reads drive 0, MSPO; RESULT OK
```
Credit line `v1.0 enhanced by dad_prg` visible under the hot-rod picture on both: `work/pkg/credit_hd/025_vbl2535.png` (HD, fading in) and `work/pkg/credit_fl/008_vbl691.png` (floppy), screenshots read.
Not run: floppy on Mega STE; floppy 16 MHz beyond the 22 s of F1; no cell on real hardware, TT, Falcon, MiSTer.

## Lead's remaining list
- The user's real-hardware pass (checklist in README.TXT); TT/Falcon/MiSTer unproven for this set.
- `tools/msrpatch.py` was edited for the docs (`{GIT}`, README_*/PATCHES_FLOPPY templates in both build commands); `play.sh` untouched. `README.md` (project) still says "Status: in progress" (it has someone else's uncommitted edit; not touched).
- Commit the new files: `patches/README_HD.TXT README_FLOPPY.TXT PATCHES_FLOPPY.TXT`, edited `PATCHES.TXT`, `tools/msrpatch.py`, PLAN.md, patches/README.md, `work/notes/package.md`; then rebuild the zips so the README build line reads a clean `git <hash>` (zips are then a different file; content other than README.TXT identical).
