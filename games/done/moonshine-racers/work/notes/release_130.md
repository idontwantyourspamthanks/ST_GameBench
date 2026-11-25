# Moonshine Racers v1.3 release record (2026-11-25)

v1.3 = v1.2 + **IN-GAME CAMPAIGN SAVING** in the Track Editor (`FILES\MSEDIT.OVL`, 2 MB+ ST family):
- From the Track Editor's track list (`top_list`), `SAVE CAMPAIGN... >` appears whenever a campaign is in memory (`CPV+1 != 0`).
- `SAVE CAMPAIGN (MSTRACKS.TRK)` offers:
  - `SAVE TO HARD DISK (FILES\MSTRACKS.TRK)` — writes `CPSTORE` to `FILES\MSTRACKS.TRK` through the HAGA TOS window (`BLK=$3900`, distinct magic `'MSWR'` co-existing with `cp_title.s`'s `'MSTK'` reader).
  - `SAVE TO FLOPPY DISK (DRIVE A:)` — opens a formatted campaign disk prompt (`INSERT A FORMATTED CAMPAIGN DISK IN DRIVE A:`, `WRITES A:\MSTRACKS.TRK`, `(ANY EXISTING FILE IS OVERWRITTEN)`), validates the floppy via `BIOS Getbpb` after invalidating BIOS BCBs (`_bufl`), writes `A:\MSTRACKS.TRK`, deletes partial files on error, and flushes dirty FAT/directory buffers via `Dfree`.
  - Error messages: `DISK IS WRITE PROTECTED`, `NO FORMATTED DISK IN DRIVE A`, `DISK FULL: NOT ENOUGH FREE SPACE`, `DISK WRITE ERROR`, `FILE ACCESS NOT AVAILABLE HERE`.
- Version bumped to `1.3` in `patches/VERSION` (in-game title credit: `v1.3 enhanced by dad_prg` in both HD `RUNME.TOS` and floppy `disk_a.st`).

## Build (reproducible)
Built twice (`/tmp/msr_v13/rel1`, `rel2`): `diff -r` of every member empty for both HD and floppy.
Delivered (v1.0 / v1.0.1 / v1.1 / v1.2 zips untouched):
* `dist/MoonshineRacers_hd_v1.3.zip` — md5 `6b35ca60c5554a63534d93bc59daad39`, sha256 `69239ffac0c12d1e719c42e5baf3d3b4a90ca14e7eac8e5208cdf870a213aef2`
* `dist/MoonshineRacers_floppy_v1.3.zip` — md5 `01b9c493e81c9f3bf701ceef2ff2fce8`, sha256 `f57a0dc5e6eeed6816f46870fa65317f2891b2a07651f70b30c56be0fa55aaf4`

Key members:
* HD: `RUNME.TOS` md5 `a8f564b41cf4ce3b00173b51d06b15a5`, `FILES/MSEDIT.OVL` md5 `7f18d808e2778c6fa953c0f33513e83a` (`25,082 B`)
* Floppy: `disk_a.st` md5 `38bef9609fb74d0d64f39a2a2e21fc1b`, `disk_b.st` md5 `0d0be455e4d0389ed98401c0e02d21d9` (= v1.0 / v1.1 / v1.2)

## Gates (Hatari 2.6.1, sound on)
| gate | target | result |
|---|---|---|
| `save_ste_2m` (NEW TRACK -> edit -> KEEP -> HD save byte-exact + `validate_campaign` -> Floppy prompt -> WP error -> Unformatted error -> Blank FAT12 save byte-exact + `validate_campaign` -> F10 reload HD + Drive A byte-exact, 0 unexpected Bus/Addr errors) | **shipped HD zip** (`/tmp/msr_v13/ship_hd/MOONSHR`) | **ALL CHECKS PASS (33/33)** |
| `save_megaste_2m` (same full flow, Mega STE 2 MB, TOS 2.06) | HD build | **ALL CHECKS PASS (33/33)** |
| `save_st_2m` (same full flow, ST 2 MB, TOS 1.04) | HD build | **ALL CHECKS PASS (33/33)** |

## Notes
* All-games HD image not yet rebuilt (deferred per user request).
* Real-hardware testing (ST, STE, Mega STE, TT, Falcon, MiSTer) has not been performed.
