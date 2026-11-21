# Moonshine Racers v1.1 release record (MSRCampaign3)

v1.1 = v1.0.1 + CAMPAIGNS (F10 menu, track sets from `tools/msrtrack.py`; ST/Mega ST/STE/Mega STE with >= 2 MB; HD copy, drive A and, floppy release, drive B) + the music-mode fix (mg_sync / mf_sync / mx_sync gate on the race flag `$1028`, not `$1021`, which is the fx/music sound mode: v1.0/v1.0.1 lost every extra frame in music mode). Source commit **5fd79c0** (`patches/` and `tools/` clean; stamp `build: git 5fd79c0`, no "uncommitted"). Hatari 2.6.1, private HOME, one Hatari at a time; nothing run on real hardware. Raw logs: `work/campgate/logs/` (`rel_*` = shipped-zip gates), scripts `work/campgate/*.py`, summary `work/campgate/RESULTS.md`.

## Build
Built twice (`/tmp/msrc3/rel1`, `rel2`): `diff -r` of every member empty (HD and floppy). The zip files themselves differ only in entry timestamps (HD 1,087,851 B, floppy 921,060 B; same sizes).
Delivered (copies of build 1; v1.0 / v1.0.1 zips untouched): `dist/MoonshineRacers_hd_v1.1.zip` md5 `81a57b7aa70b55d0ee7e891cd6538b0f` sha256 `42883f6587735cec439b6bc5d7bd91f36d6871101a93d603cba41e5ee6699577`; `dist/MoonshineRacers_floppy_v1.1.zip` md5 `2b19a4d82fbb8edff5be3e05120236f2` sha256 `6f5cab815ffab0757f35a0f64900fd13bd42a205c89b26db5195ca06dabf8c49`.
Members HD: RUNME.TOS `538737dd`, README.TXT `deecbe72`, PATCHES.TXT `954e8aa5`; FMR273.HST, HAGA, LMR273.HST, LOG.TXT, MR240R.BMP, FILES/MS1, MS2, MSR_S1.FIC equal the v1.0 members. Floppy: disk_a.st `81e2a7b7`, disk_b.st `0d0be455` (= v1.0), README.TXT `9ae7f288`, PATCHES.TXT `832b6858`.

## Gates on the shipped zips (unzipped to /tmp/msrc3/ship)
| gate | result |
|---|---|
| STE 1 MB HD stock smoke + real shop EXIT (`pkg101/gate.py` flow, `rel_ste1`) | race 1, shop mouse MOVES, EXIT click at (0,167) -> race 2 started, race 2 mouse FROZEN, 300 s play alive; 3 Bus/Addr lines (= STE v1.0.1 baseline) |
| STE 2 MB HD copy campaign -> ending | `rel_hd_finish_hd_ste2m` ALL CHECKS PASS |
| STE 2 MB HD, campaign from drive A | `rel_hd_finish_a_ste2m` ALL CHECKS PASS |
| Mega STE 2 MB HD copy campaign | `rel_hd_finish_hd_mste2m` ALL CHECKS PASS |
| ST 2 MB HD copy campaign | `rel_hd_finish_hd_st2m` ALL CHECKS PASS |
| floppy STE 2 MB campaign from drive A (disk-2 swap, ending) | `rel_fl_finish_a_ste2m` ALL CHECKS PASS |
| strict PSG, HD STE 2 MB, drive-A read + race 1, sound on | PASS, 0 violations, 0 warnings |
| strict PSG, floppy STE 2 MB, read from A and from B, disk-2 swap, race 1 | PASS, 0 violations, 0 warnings |

Music mode (`work/campgate/gate_music.py`: race 1 in fx mode, finish, shop, click the top-right FX at game pixel (255,38) -> race 2 reports `$1021 = 1`, EXIT, joystick up, 300 VBL window; `$1021` still reads 2 in the shop right after the click and is 1 in race 2). passes/s = logic steps/s, fps = steps + extra frames per second:

| cell | race 1 FX native fps | race 2 MUSIC steps/s, fps | race 2 MUSIC at 16 MHz fps |
|---|---|---|---|
| HD STE 1 MB | 17.03 | 10.08, 20.06 | 26.48 |
| HD Mega STE 2 MB (60 Hz) | 20.86 | 9.98, 25.21 | 21.49 |
| floppy STE 1 MB | 17.00 | 9.98, 20.06 | 26.98 |

fx-mode control (same flow without the click, `--nomusic`), v1.1 vs shipped v1.0.1 (race 2 native fps / 16 MHz fps): HD STE 1 MB 19.90 / 26.58 vs 19.90 / 26.63; HD Mega STE 2 MB 25.40 / 21.78 vs 25.45 / 21.15; floppy STE 1 MB 20.50 / 27.37 vs 20.06 / 26.88 (differences of a flip or two per window = window phase). Music mode now has about the same flips/s as fx mode (v1.0.1 had none extra there). Steps stay 10/s.
The fx-mode behaviour is identical to v1.0.1 by construction (in fx races both `$1028 != 0` and `$1021 == 2` hold), so the 1 MB A/B of the campaign build vs v1.0.1 (below) stands for fx mode; the A/B was run on the payload of bb215cd, before the music fix (bb215cd) and the music fix changes only the `.r1` test in the three sync patches.

## Campaign gates (earlier commits, same code except the music fix)
* 1 MB A/B vs v1.0.1, 8 cells (HD + floppy x ST/Mega ST/STE/Mega STE): ALL PASS, C-vs-B RAM control 0 bytes (RESULTS.md).
* HD cold-boot cells ST/Mega ST/STE/Mega STE x 2/4 MB: finish from HD copy and drive A, time-out replay, ORIGINAL GAME, 13 error cases. Floppy: STE 2/4 MB, Mega STE 2 MB, ST 2 MB: drive A, drive B, disk 2 in A / in B, time-out, ORIGINAL GAME, errors (the sampling-check flake of `fl_timeout_ste4m` fixed in `cg.py wait_race`, reruns PASS).
* TT / Falcon 4 MB HD: stock (marker MSPO, IB+4 0, all sites stock). The floppy release does not boot on TT/Falcon, v1.0.1 neither.
* 10 minute stock race at 4 MB with the gate on: STE and Mega STE alive, pace = v1.0.1.
* Empty drive A (HD): 16.9 s STE TOS 1.62, 5.6 s Mega STE TOS 2.06 (TOS' own timeout), documented in README_HD.TXT; no probe.

## Real-hardware-only risks (nothing here was run on real hardware)
Floppy campaign read and the disk-present probe (FDC / index timing, Gotek, MiSTer); the boot sector's capture of TOS `$42e` on a real TOS; Mega STE cache with the reader code HAGA's top region receives; real GEMDOS drive-A reads and TOS' empty-drive timeout; HAGA+$83 machine-type byte measured only in Hatari; the blitter/STE items of the v1.0 checklist.

## User test on MiSTer (2026-11-21)
The user ran the shipped v1.1 HD build (`MoonshineRacers_hd_v1.1.zip`, `RUNME.TOS` 538737dd…) with a 3-track test campaign (`work/testdisk/`, git-ignored: STOCK 12, STRAIGHT TEST = level 5 with every curve delta 0, STOCK 09) loaded through the F10 menu, and played from each of the three tracks: "all 3 items on the campaign behaved as you would expect, no signs of breakage". So 'play from track N' (N > 1) works on the release; the track-editor milestone-2 PLAY failure is on the editor/harness side. MiSTer machine model and RAM size, HD-copy vs drive-A load, and the race-to-race advance were not stated. User feedback from the same session: nothing tells the player that F10 exists; recorded as a requirement for the editor release in `editor_design.md` §5.1.
