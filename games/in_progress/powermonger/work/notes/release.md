# Powermonger v1.1 release: gates of the Retire fix (PMRelease, 2026-11-19)

Tags: **[obs]** raw tool output (`work/release/runs/*.txt`, screenshots `work/release/runs/shots_*`, git-ignored with the other run output); **[INFERENCE]** not run. Hatari 2.6.1 only, real hardware not run.
Tools: `tools/pmload.py` (cold boot -> map view -> a sequence of Retire variants, each followed by the next conquest: VBL times, resource-loader trace, payload blobs, free-RAM pattern), `tools/pmloadsum.py` (per step loader summary from the logs), `tools/pmcombined.py` (cold-boot gates + fps), `tools/pmretire.py` (Retire only, PMRetire), `tools/packcheck.sh` (zips = fresh build), `tools/package.sh` (now deterministic: fixed file times, sorted members; README build stamp `git <hash>`).
Builds under test: `build/rel/cap` (default set, 38 patches incl. `pm_cachecap`; floppy md5 `ba7cae54412e84b728e48b78dac954e3`, HD `WAR.PRG` `ed259a3ff25455d89221885a0563aaea`, `PMLATE.DAT` `792409e029e1fb0c10c43333f29d1122`) and `build/rel/nocap` (= v1.0's default set: the same minus `pm_cachecap`).

## 0. Result
* `pm_cachecap` gates green on ST / STE / Mega STE / TT / Falcon (cold boots), floppy and HD: Retire lose x3, win, the last island's ending pictures, a new conquest after each, 31-32 payload blobs intact after every step, 112 209 (floppy) / 43 365-52 485 (HD) pattern bytes of the free payload space untouched.
* No load-time or behaviour change in normal play: the loader calls of a level start are the same resources with and without the patch (section 4), no loader call (so no hook execution) happens between the level start and the next screen change, and the fps / cycles per pass are equal (section 3).
* The only visible cost: from the second Retire of a session on, the lose / win / end picture is read from the disk again (section 4.3).
* Harness finding: `pmretire.py`'s win run failed in round 2 on Mega STE / HD because the harness clicked the picture with the pointer where the next screen has START NEW CONQUEST (section 7); `pmload.py` parks the pointer first.

## 1. TT and Falcon [obs, `work/retire/runs/{tt,fal}_floppy_v_*.txt`, PMRetire's queue, run to the end; build `build/retire/v_fix` = default set + cap]
| cell | result |
|---|---|
| TT TOS 3.06 4 MB, v_fix | `CELL DONE ... LOSE: OK`, 2 rounds, picture 16 colours, 31 blobs intact, back to options, next level map view, cursor `$b74f4` |
| Falcon TOS 4.04 4 MB, v_fix | OK, 2 rounds, same |
| Falcon, v_def (no cap) | FAIL: 13 blobs overwritten, `cursor_after 0`, picture never stable |
| TT, v_def | FAIL (`no screenshot (Hatari busy, dead)`); ST v_def: FAIL (halted dialog) |
(TT / Falcon without `HATARI_TTF` render one palette per frame: fine for the black-screen check.) The shipped zips are gated again on TT / Falcon in section 10.

## 2. Win and the ending [obs]
* `pmload.py --seq lose,win,lose,lose` (the win = `$57fce` forced to 4 by a breakpoint at `$d2d8`; the game then asks "delete all your conquered lands" (YES), `RESULT rN: confirm dialog ...: True`): **STE floppy, STE HD, Mega STE floppy, Mega STE HD, all OK** (`ld_{ste,mste}_{fl,hd}_cap.txt`): win picture 14 colours, back to the option screen, YES, territory chart (10 s: the game's own deletion; the original takes the same, 555 vs 554 VBL), second level map view, then two more lose rounds.
* **`--final`** = last island (`$2df6e = 4`, `$580a4 = $c2` at the `$d2d8` breakpoint): the loader calls are `12:n+skip 13:n+skip` (END_PIC1, END.DAT 60 936 B: both would have landed over the payload; both skipped by the cap); the ending picture is shown (`shots_ste_fl_final/r1_final_picture.png`), payload 31 blobs intact, free-space pattern 0 changed (STE floppy `fin_ste_fl_cap.txt`; Mega STE HD `fin_mste_hd_cap.txt`: win, then final, OK). What follows the first ending picture is checked 60 s later in the runs of section 10.
* The last island needs no savestate: the two pokes at the existing breakpoint are enough.

## 3. Cold-boot gates + fps on the final set [obs, `pmcombined.py`, `work/release/runs/cb_*.txt` (cap) and `nc_*.txt` (no cap, same host load)]
Every cell: `sites: 9 of 9 live` (the 8 combined sites + `cachecap`), `PMPO`, pointer 20/20, key F, village hover, three buffers rotating; the HD cell with save + load (`triple_sl: True`). The no-cap cells print `8 of 9 live` (expected: `cachecap` absent) and `CHECK`.
| cell | boot | map view fps / ticks (cycles per pass) | get_men fps | v1.0 table (combined.md) map / get_men | no-cap run, same conditions: map (cycles) / get_men |
|---|---:|---|---|---|---|
| ST TOS 1.04 1 MB | 148 s | 4.65 / 4.00 (160177) | 4.70 | 4.65 / 4.85 | 4.65 (160185) / 4.75 |
| STE TOS 1.62 1 MB | 148 s | 4.80 / 4.00 (160194) | 5.25 | 4.85 / 5.30 | 4.85 (160133) / 5.25 |
| Mega STE 2.06 4 MB 8 MHz | 149 s | 4.74 / 4.02 (133588) | 5.64 | 4.74 / 5.58 | 4.74 (133523) / 5.64 |
| Mega STE 16 MHz | | 10.14 / 4.02 (267032) | 12.48 | 10.20 / 12.48 | 10.20 (267202) / 12.54 |
| TT 3.06 4 MB 32 MHz | 104 s | 22.62 / 4.02 (534390) | 27.12 | 22.62 / 27.12 | - |
| Falcon 4.04 4 MB | 129 s | 11.45 / 4.00 (320344) | 12.00 | 11.40 / 12.20 | - |
| HD ACSI STE 1 MB (save+load OK) | 101 s | 4.80 / 4.00 (160255) | 5.25 | 4.85 / 5.30 | - |
**Changed numbers vs combined.md:** STE and HD STE map 4.85 -> 4.80, Mega STE 16 MHz map 10.20 -> 10.14, Falcon get_men 12.20 -> 12.00, Mega STE get_men 8 MHz 5.58 -> 5.64, ST get_men 4.85 -> 4.70, Falcon map 11.40 -> 11.45; each is one flip in 1000 VBL or the men-moving count of the get_men scenario (combined.md says it depends on the scenario), and cap against no cap in the same conditions differ by at most one flip: cycles per pass differ by 8-170 of 133 000-267 000 (<= 0.06 %). The TT row is identical to the digit. So no fps number of `combined.md` / `hotpaths.md` / `baseline.md` is stale through the cap [obs for the fps table; INFERENCE for the two older notes, which hold per-routine cycle counts of the map view, where the hook never runs].
Why the hook cannot be in these numbers [obs]: `ld_ste_fl_cap.txt`: first level done at VBL 6964, first Retire click at VBL 11008: **no loader call at all in between** (4044 VBL of map view, Option panel, GAME panel); the hook is only reached from the loader's disk path.

## 4. Load times, before (no cap = v1.0 set) and after (cap), seconds of emulated time [obs, `ld_*.txt`, `pmloadsum.py`]
Method: the VBL (`e VBL`) at the click and the VBL of the last return of the resource loader (`$e03c`) after it, from a debugger breakpoint trace (`$df5a` call with D2.w = resource, `$df96` = not cached = disk / file system, `$e03c` return, `$dc114` = cap skip). Exact to a VBL; the log's "poll" figures (screenshot polling) are only good to about 1 s. Hz: 50 on ST / STE, 60 on Mega STE (pmcombined's `hz`). 8 MHz, no other change.
### 4.1 Normal play: START NEW CONQUEST -> chart (resources 0 2 3 4 5 10 from the disk) and island -> map view (11, 1, 8 from the disk)
| cell | no cap (v1.0 set) | cap | resources loaded |
|---|---|---|---|
| STE 1 MB floppy | 953 / 610 VBL = 19.1 / 12.2 s | 958 / 587 = 19.2 / 11.7 s | the same, all from the disk |
| STE 1 MB HD | 511 / 402 = 10.2 / 8.0 s | 510 / 403 = 10.2 / 8.1 s | same |
| Mega STE 4 MB floppy | 1171 / 725 = 19.5 / 12.1 s | 1122 / 724 = 18.7 / 12.1 s | same |
| Mega STE 4 MB HD | 633 / 494 = 10.6 / 8.2 s | 631 / 493 = 10.5 / 8.2 s | same |
HD figures agree within 2 VBL; the floppy ones within 5 % (rotation phase of the emulated drive between boots: the poll figure of the second step was 672 in one cap run and 711 in a no-cap one). The original disk gives 971 VBL for the first step on STE (`ld_ste_fl_orig4.txt`, the protection step breaks the second), the same order.
### 4.2 Second and later levels (10, 11, 1, 8 come from the cache)
Cap: STE floppy 79-80 / 212-214 VBL (1.6 / 4.3 s) for the chart / map view, STE HD 77-80 / 213-214, Mega STE floppy and HD 96-98 / 260-262 VBL (1.6 / 4.3 s); the original (STE floppy) 85-89 / 247-248 VBL. **The cap does not touch the cache of the 4 normal resources**: they end at `$B74F4` < `$B8000`, so `[$2c1ba]` = `$b74f4` at the map view with and without the patch on all four cells (`RESULT cache after the first level`).
### 4.3 Which resource loads hit the disk now, and what it costs
Calls seen after the name prompt in every cell (the loader is called for 0 2 3 4 5 10 11 1 8 and, from Retire / the ending, 14 15 12 13; 6, 7 and 9 never go through it then): 0 2 3 4 5 are loaded from the disk and never cached (the cache table at the map view lists only 10, 11, 1, 8), 10 11 1 8 are cached and unchanged, so **the only resources that now go to the disk every time are 14 (LOSE), 15 (WIN), 12 (END_PIC1) and 13 (END)**: loaded as `n+skip` = from the disk, copy to the cache skipped by the cap. In the original the second and later Retire copy 14 / 15 from the cache.
Click on RETIRE -> the loader returns (picture complete):
| cell | Retire #1 (disk in both) orig / cap | Retire #3 / #4 original (cached copy) | Retire #3 / #4 with the cap (disk) | win #2 orig / cap |
|---|---|---|---|---|
| STE floppy | 386 VBL = 7.7 s / 322 = 6.4 s | 99 / 106 VBL = 2.0 / 2.1 s | 314 / 344 = 6.3 / 6.9 s | 285 / 256 VBL = 5.7 / 5.1 s |
| Mega STE floppy (60 Hz) | 438 / 373 = 7.3 / 6.2 s | 114 / 124 = 1.9 / 2.1 s | 415 / 391 = 6.9 / 6.5 s | 343 / 309 = 5.7 / 5.2 s |
| STE HD | - / 180 = 3.6 s | - | 172 / 186 = 3.4 / 3.7 s | - / 137 = 2.7 s |
| Mega STE HD | - / 225 = 3.8 s | - | 225 / 218 = 3.8 / 3.6 s | - / 178 = 3.0 s |
(the first 100-150 VBL of each figure are the game's own delay between the click and the loader call, measured on the original's cached Retire: 99-124 VBL in all.) So **a repeated Retire costs about 4.3-4.8 s more on a floppy** (the picture is read from the disk again) **and an estimated 1.4-1.6 s more on HD** [INFERENCE: no cached HD original to compare; derived from the original's 99-124 VBL cached figure]. The picture itself, the click back to the option screen (34-41 VBL in every patched round) and the next conquest are not slower.
### 4.4 The ending
`12:n+skip 13:n+skip`: +742 VBL = 14.8 s STE floppy, +500 VBL = 8.3 s Mega STE HD from the click to the last loader return (both pictures are loaded once; the original would cache both [INFERENCE: it overwrites the payload region in a patched build; unpatched it has the RAM on 4 MB machines]).

## 5. What the cap changes for the other default patches [obs / argument]
The hook runs only inside the resource loader's disk path (`$e000`, reached only after a decompress), is 24 bytes, uses only `d0` / `a1` (`d0` is reloaded at `$e00e`, `a1` is the cursor register that the displaced instruction loaded), and its only effect is that a resource ending above `$B8000` is not copied to the cache. It cannot influence code that does not call the loader:
* `p3b_interp` / `p3b_delta`, `tick_*`, `p7_triple_*`, `qol_*`, `snd_*`, `p4_*`, `p6_*`, `tt_ptr`, `pm_tooltip`: none loads a resource and none reads `[$2c1ba]` / `e040[]` (`m68dis --xref 2c1ba` on the stage 2 dump = the loader and the start-up probe only; `grep` of the patch sources for `2c1ba` / `e040`: only `pm_cachecap`). They run on a cache with the same four entries as before. `p7_triple_*` uses `$70000`, the buffer that the lose / win / end picture is decompressed into (`[$2df78]` = buffer C): unchanged, the cap only removes the later cache copy.
* Timing: the loads of the four normal resources are the same, from the same place (cache or disk); the longer loads exist only on the Retire / ending screens, where the main loop is not iterating.
* No behaviour change in normal play: map, level start, Options, Retire, new conquest ran for 4 rounds on 4 machines (section 6), payload intact each time.

## 6. Long sequence, no crash [obs, `ld_*_cap.txt`: cold boot -> map view -> Retire lose -> next level -> Retire win (YES) -> next level -> lose -> next level -> lose -> next level]
| cell | result | payload blobs after each of 9 steps | free-RAM pattern after each |
|---|---|---|---|
| STE TOS 1.62 1 MB floppy | `CELL DONE ... OK` | 31, 0 differ x 9 | 112 209 B, 0 changed x 9 |
| STE 1 MB HD ACSI | OK | 32, 0 differ x 9 | 52 485 B + swap spill, 0 changed x 9 |
| Mega STE TOS 2.06 4 MB floppy | OK | 31 x 9 | 112 209 B, 0 changed x 9 |
| Mega STE 4 MB HD ACSI | OK | 32 x 9 | 43 365 B, 0 changed x 9 |
plus the cold-boot cells of section 3 (map view, get_men, 20 screenshots, F, hover). The unfixed build fails the same sequence everywhere (retire.md section 2).

## 7. Harness note: round 3 went to the chart instead of the option screen (not a game difference) [obs]
`pmload.py`'s first runs showed, in round 3 (the lose after a win), that clicking the picture led straight to the territory chart (`ptr_ste_fl_cap_keep.txt`: `r3: picture click -> TERRITORY CHART (no option screen)`, pointer `(143, 87)`; PMRetire's win round 2 on Mega STE / HD failed with `option screen again: False`, same position `(143, 87)` in its logs). In round 1 the Retire button was at `(31, 54)`, after a win + new conquest it is at `(143, 87)`, and START NEW CONQUEST of the option screen is at `(160, 85)`: the click, still held when the option screen appears, presses it. Parking the pointer first (`pmload.py` default; `--keep-pointer` for the old behaviour) gives `r3: picture click -> option screen: 34 VBL` (`ptr_ste_fl_cap_park.txt`) with the same build. The original disk reached the option screen in all rounds (its click -> option screen takes 115-127 VBL). Not a defect of the patch [obs: the same build, two harness behaviours, two outcomes].

## 8. Payload range check ($DC100) [obs]
* `EXTRA_RANGES["pm_cachecap"] = [(0xDC100, 0xDC1FF)]`; the blob is `$DC100-$DC117` (24 B). Manifest `used` spans of the floppy and HD builds around it: `$DB000-$DB010 $DB100-$DB168 $DB200-$DB210 $DB300-$DB318` (p7), `$DC000-$DC022` (fal_ym), **`$DC100-$DC118` (cachecap)**; no two `used` spans overlap (checked on both manifests; `build` checks it too), the neighbours are inside their own ranges (`fal_` `$DC000-$DC0FF`, `p7_` `$DB000-$DBFFF`), the `p6_` / `snd_` ranges (`$D5000-$DCFFF`) contain the page but nothing else is placed in it.
* The page lies in the HD overlay window (PMLATE.DAT `$BD000-$DCFFF`): the HD build restores it from `PMLATE.DAT` after stage 1 (32 HD blobs in RAM = the build, incl. cachecap, after every step).
* What the game itself uses there: **nothing, in any screen I ran** [obs]. Pattern proof: the free spans of `$B8800..$EFFFF` of the build (floppy: 36 spans, 112 209 B, incl. `$DC022-$DC0FF` and `$DC118-$EFFFF`; HD: 38 spans 52 485 B / 43 365 B and the swap buffer spill) are filled with a position-dependent non-zero pattern at the hand-over (floppy: stage 1, before the intro; HD: stage 2) and compared after: **0 changed** at the map view, after the lose picture, after the win picture, after the ending picture, after each next level, over 4 Retire rounds on STE and Mega STE, floppy and HD (`ld_*_cap.txt`, 9 reports per cell; `fin_ste_fl_cap.txt`: map view and after the ending picture), and on HD STE with the game's own Save + Load, get_men and the battle (`fill_hd_ste_saveload.txt`: saved vs loaded 0 differ, SAVEDISK.DAT slot A == saved, fill 0 changed at the map view, get_men, battle). The intro, name prompt and options screens are inside the floppy window; the HD proof begins at the game's hand-over (the stage-1 half of the HD run is the floppy's, as in `pmpatch.cmd_boot`).
* Static: the game's resource destinations (`$e0c4`, loading.md 2.2) are all below `$B8000`; the loader's own cache is the only writer above, and it is now capped.
* Not run: a floppy save + load with the fill (needs the second SAVE disk; `pmpatch.run_saveload` is HD only); the floppy save code is the original's and does not touch `$DC100` [INFERENCE].

## 9. Packaging, pre-commit build [obs]
`tools/package.sh` x2: floppy zip `aadaa6a007e0f07d86eeaedabbb03a44`, HD zip `99600ab6a8fd6941be3cb3403dc0a25b`, identical both runs (README stamp `1f534d2+dirty`). `tools/packcheck.sh`: `PACKCHECK OK` (floppy `.st` and every HD member md5 against an independent `pmpatch.py build`, member lists equal, README version and stamp, credit text `v1.1 enhanced by dad_prg` in the image). The v1.0 zips are untouched.

## 10. Final builds from the clean commit `5e4d931` [obs]
* `tools/package.sh` x2 from the clean tree: floppy zip `dist/Powermonger_v1.1_patched_floppy_2026-11-19.zip` **`e19c2c31a4e8a830a06ed46bec8f10de`**, HD zip `dist/Powermonger_v1.1_patched_hd_2026-11-19.zip` **`17a6d374ebacfad5c61a2236531bdd26`**, identical in both runs; READMEs say `Build: v1.1, git 5e4d931`; `tools/packcheck.sh`: `PACKCHECK OK`. Members (md5): `Powermonger_patched.st` `ba7cae54412e84b728e48b78dac954e3`, HD `AUTO/WAR.PRG` `ed259a3ff25455d89221885a0563aaea`, `DATA/SPRITE40.DAT` `37d28ff241b94d3f493f24e236e5a73b`, `PMLATE.DAT` `792409e029e1fb0c10c43333f29d1122` (same as section 9: only the README text changed). The v1.0 zips are untouched.
* Shipped-zip gates: both zips unzipped to `work/release/ship/`, the builds under test are the zips' own members (`work/release/runs/sh_*.txt`):
| cell | sequence | result |
|---|---|---|
| floppy STE 1.62 1 MB, pattern | lose, win, lose + 60 s idle | OK, payload 31 intact, fill 0 changed, main loop iterating |
| floppy ST 1.04 1 MB | lose, win | OK |
| floppy Mega STE 2.06 4 MB, pattern | lose, win, lose, lose | OK |
| floppy TT 3.06 / Falcon 4.04 4 MB | lose, win | OK / OK |
| HD STE (ACSI + HDDRIVER) | lose, win, lose + 60 s idle | OK (32 blobs) |
| HD Mega STE | lose, win, lose + 60 s idle | OK |
| the last island's ending | floppy STE (pattern), HD Mega STE | OK; 68 s after the click the ending screen is still up (non-black 0.17, 10 colours), CPU not parked in STOP |
| `pmretire.py` against the unzipped floppy | Mega STE lose x2 rounds; STE `--win` x2 | OK / OK |
| `pmcombined.py` cold boot (title/intro skipped, map, pointer 20/20, F, hover, fps) | floppy STE (map 4.85 fps), HD STE ACSI + save/load (4.85 / 5.20) | OK / OK |
The cold boots of these cells pass the title / intro and name prompt on every machine (the gates `name`, `options`, `chart`, `game` of the harness are screenshot-matched).
* **All-games image: NOT rebuilt.** Nebulus tree has uncommitted editor changes: `nebrelease.py build` of the current tree gives `NEPATCH.BIN` `11520b153461194803cc661e68e0d202` (release v1.1: `6b122b9b...`), START.TOS `4ecf26d8...` matches, so `make_hd_image.py` would stage a different Nebulus. Left to the lead after the Nebulus v1.1.1 release; then `python3 tools/make_hd_image.py` and `tools/pmretire.py --img <img> --hopts "--cpuclock 16"` (the user's repro: `run_megaste.sh` = Mega STE TOS 2.06 4 MB 16 MHz, `--gemdos-drive skip --acsi 0=<img>`, no other options) are the two remaining steps. The pmretire `--img` path itself ran (PMRetire, `img_megaste_dist*.txt`) on the stale image only.
