# Moonshine Racers v1.2 release record (2026-11-23)

v1.2 = v1.1 + **IN-GAME TRACK EDITOR** (HD release, ST/Mega ST/STE/Mega STE with >= 2 MB; overlay `FILES\MSEDIT.OVL`, `EDVER` 5) + **per-track race length** (`MSTRACKS.TRK` version 2, `cp_len`, HD + floppy) + **F10 welcome-screen hint & boot-init fix** (`cp_welcome`, `cp_title.s` `e3`, `boot_init`).
Source commit **63025b1** (`patches/` and `tools/` clean; stamp `build: git 63025b1`, no "uncommitted"). Hatari 2.6.1, private HOME `/tmp/msr_neon/home`, one Hatari at a time; nothing run on real hardware.

## Root cause of the preview-2 test-drive crash (`$edc4`)
Reproduced on the pre-fix build (`Address Error reading at address $2475, PC=$edc4`, followed by `$fffffc6f / $e09598` exception loop and `$48f00000` bus errors):
* Pressing `F10` on the `WELCOME PARTNERS` screen (`cp_welcome` -> `cp_title.s` `e3`) opened `cp_menu` inside `$7bd0` *before* the game's one-time boot initialisation (`$71a8–$723c`) had run.
* All 9 sprite banks (`$19d0e`, `$1a12c`, `$3d16c`, `$1b074`, `$21568` = player car bank, `$25242`, `$28f0a`, `$2ca46`, `$306c2`) were still unrelocated (`$2156a` held relative offset `$278` instead of `$217e0`), sound driver `$8bb6` was uninitialised, `$1227–$1229` were uncleared, and IKBD joystick reporting (`$d140`) was not enabled.
* Fix: `e3` leaves `$7bd0` permanently (`addq.l #6,a7`), runs `boot_init` (`$71a8–$723c`) once, then calls `cp_menu`; `BACK TO THE TITLE` jumps to `$7242` (title loop), game start fades out and jumps to `$724e`.

## Section 17 usability overhaul (`patches/ovl/msedit.s`, `EDVER` 5)
* **Build-as-you-go road model**: grid displays THE ROAD (`0..vFin-1`) + chequered FINISH (`vFin`, where the BAR stays); hidden run-out absorbs length changes automatically (`700..28000` units).
* **NEW TRACK**: 5 x 200-unit straight segments (1000 units) + FINISH, ready to edit and test-drive immediately.
* **Building actions**: `I`/`Ins` (new after cursor), `Shift+I`/`Shift+Ins` (new before), `A` (add at end), `D` (duplicate), `Del` (delete segment + its objects), `Shift+B` (end road here), `+`/`-` (preset length step), `L` list ±10 units (Shift 100, FIRE/Ctrl 1), `P` on FINISH test-drives the last 1000 units.
* **1-tile hill shapes**: `shape.b` attribute on the segment record; two-half tile colours (slope at 1/4 and 3/4); `S` explodes a shaped segment into RAW pieces; `shape_scan` recovers shapes on load; kept boundaries (`flags` bit 0) survive KEEP.
* **`cp_len` integration**: `c_td` sets/clears `V_RLEN` (`CPV+16`) around `$76f4`; `store_rebuild` writes per-track race length (`+26`) and header version 1 or 2.

## Build (reproducible)
Built twice (`/tmp/msr_neon/rel1`, `rel2`): `diff -r` of every member empty for both HD and floppy.
Delivered (v1.0 / v1.0.1 / v1.1 zips untouched):
* `dist/MoonshineRacers_hd_v1.2.zip` (1,103,350 B) — md5 `76252e67b2672e409737b47ac17b9bfc`, sha256 `12bc8c9d5eccfc26c8dd3b70fca7624501bc891e1a336ea00316bf2c49e2651d`
* `dist/MoonshineRacers_floppy_v1.2.zip` (921,652 B) — md5 `dac934f2b0a4de9a502960f45a721d37`, sha256 `eef03964c1ae1b3a6e6091aefa707345ba630e3c9c85f3360261d60f637d7b71`

Key members:
* HD: `RUNME.TOS` md5 `585fb9b21301e799c7edabffa49e83e4`, `FILES/MSEDIT.OVL` md5 `4a2cfa758ccad719c3c67179578d7873`
* Floppy: `disk_a.st` md5 `7a742c7d7196fecefbb46a254a810e06`, `disk_b.st` md5 `0d0be455e4d0389ed98401c0e02d21d9` (= v1.0 / v1.1)

## Gates (Hatari 2.6.1, sound on)
| gate | target | result |
|---|---|---|
| `s17_ste` (welcome→F10→editor, NEW TRACK, TD1 to BAR with `cp_len`, `A`/`H` CREST 1-tile/`+`/`.`/`I`/`D`/`S` explode/`U` undo, FINISH panel + TD2 last-1000 to BAR, KEEP v2 + `msrtrack.validate_campaign`, re-open kept boundaries + shape, `Shift+B` + 700-unit floor, untouched stock TRACK 01 byte-exact 5770 B, 0 unexpected Bus/Addr errors) | **shipped HD zip** (`/tmp/msr_neon/ship/hd/MOONSHR`) | **ALL CHECKS PASS** |
| `s17_megaste` (same full flow, Mega STE 2 MB) | HD build | **ALL CHECKS PASS** |
| `s17_st` (same full flow, ST 2 MB) | HD build | **ALL CHECKS PASS** |
| `abs1m_ste` (1 MB STE absence: only `$7c04` patched, 1 MB welcome line drawn, 0 hits outside 1 MB path, no MSEDIT/MSTRACKS GEMDOS calls) | HD build | **ALL CHECKS PASS** |
| `abs1m_mste` (1 MB Mega STE absence) | HD build | **ALL CHECKS PASS** |
| `sitefl_1024` (1 MB floppy: `IB+4 = 0`, `$7926` stock `4eb90000edea`, 0 errors) | **shipped floppy zip** | **ALL CHECKS PASS** |
| `sitefl_2048` (2 MB floppy: `IB+4 = 0xff`, `$7926` = `cp_len`, F10 menu, 0 errors) | **shipped floppy zip** | **ALL CHECKS PASS** |
| `flhint` (2 MB floppy title `F10 = CAMPAIGNS` hint + F10 menu) | **shipped floppy zip** | **ALL CHECKS PASS** |

## Open / future work
* In-game HD save of `FILES\MSTRACKS.TRK` (Milestone 4) and floppy editor (Milestone 5) are not yet built.
* Real-hardware testing (ST, STE, Mega STE, TT, Falcon, MiSTer) has not been performed.
* Time-limit tuning knob (`cp_len.s`): `P = (Tb - 100) * L / Lb + 100` (floored at 255 passes) is tight for an un-upgraded car on 2000–6000 unit tracks on race 1 (adjustable via 3 constants in `patches/cp_len.s`).
