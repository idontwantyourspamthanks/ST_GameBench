# Stage 0 + 1 results (PMWW1Stage01, 2026-11-23)

Evidence contract: **[obs]** = raw lines from a command / log file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1 (`~/Code/AtariST/hattari/build/src/hatari`), private HOME per run (`<workdir>/home`), work dirs `/tmp/pmww1s1/*`, one Hatari at a time.

## Stage 0
* Intake, md5s: `intake.md`, README. `disks/ea.st` md5 `95354c89884a4cb82b62fe63400bf750` [obs: `md5sum`]; `AUTO\WW1.PRG` md5 `dc93b917458125398a072c95f452f4b0` [obs].
* Cold boot of the unmodified converted disk, STE TOS 1.62 1 MB: white screen, then (t = 20 s) the "Powermonger WW1 Data Disk / Please enter your name" title [obs: `work/shots/stage0_title_original.png`, 9 screenshots 10 s apart in `/tmp/pmww1s1/r1_*.png`].
* New game to a playable map [obs: `work/shots/stage0_map_view_original.png`]: name `WWI` -> "Welcome to the World War I Scenario" (3 buttons) -> START NEW CONQUEST -> **disk requester** (see `intake.md`) -> chart (Europe) -> small island at the top -> protection question "Between Pages 2-7: How many Houses in this land?" (answer read from RAM `$5b008+2*[$5a85c]`: 58, 59, 140 in three runs, entered with the digit arrows) -> 3D map view; world counter `$2ed90` = `0xa`, then `0x13`, `0x1b` (about 9 per second) [obs].
* Original behaviour of Retire (baseline for the payload gates) [obs, same session]: Option -> GAME -> RETIRE shows the lose picture (cursor `$2cfda` `$9fc58 -> $a7958`), a click returns to the option screen; START NEW CONQUEST again goes straight to the chart (no disk requester); with the balance forced (`$5a830 = 4` at `$d6c8`) RETIRE shows the win picture ("WELL DONE YOU HAVE WON THE BATTLE", cursor `$af658`); after a win START NEW CONQUEST asks "... are you sure you want to delete all of your conquered lands" (YES at ST (130,111)); the protection question comes again after a lost game.
* Address map: `addrmap.md` (34 patch sites + 25 routines/tables mapped and compared instruction by instruction [obs: `addrmap.py check` prints 59 rows]; 109 of the absolute operands in master's patch sources got a WW1 value by code vote, 49 of them data addresses >= $1c000 [obs: `addrmap.py vars`]; dynamic confirmations).
* Hand-over dump `work/dumps/entry576.bin` (1 MB, md5 `b10511e0b3df0d32b00fa1c188db0bfc`) and the independent depack `tools/wwdepack.py` agree byte for byte on `$576..$1d2ad`, md5 `694b94a1e1e06aa05bd6579cbb8c3778` [obs: `python3 tools/wwpatch.py verify` -> `vs work/dumps/entry576.bin: IDENTICAL`].
* Open item of the plan (does the EA game load more CODE later?): not answered; the title RAM differs from the hand-over image in 146 clusters of `$576..$24000` [obs], which are variable/table/self-modification writes, not a second stage [INFERENCE: the nested program has no loader for further code; the map view needs no disk access except the Powermonger-disk swap above].

## Stage 1 gates
All lines are raw `GATE`/`CELL` lines from `work/runs/*.txt` (chain: `tools/stage01_gates.sh`). Hatari STE TOS 1.62 1 MB unless stated.
* **Disk check** [obs, `wwpatch.py checkdisk build/default/floppy.st`]: 0 bytes differ outside FAT / size field / WW1.PRG clusters; chain 75 -> 76 clusters (cluster 369, was free); 12 files identical; no cross-links; `CHECKDISK PASS`. Negative control (one byte flipped in a data file): `CHECKDISK FAIL`.
* **Core-only build, hand-over** [obs `handover_core_only.txt`]: `GATE core_only handover game image $576-$1d2ad identical to the original's: PASS (md5 694b94a1...)`; RAM differing from the original: `$465-$4f7` (the pushed copy routine), `$72000-$727fb` (payload), `$f7fa8-$f7ff1` (user stack residue of front) only.
* **Default build (credit only), full scenario** [obs `default_ste.txt`]: `CELL DONE default/ste-1.62-1024K: OK (506s)`: marker `PMPO`, site bytes `4eb900072800`, credit visible (780 px, colour (102,102,68), rows 194-199), map view ticking, lose picture stable x3 and still there 8 s later (cursor `$9fc58 -> $a7958`), win picture stable (cursor `$af658`), third land reached after the "delete conquered lands" dialog; `payload@options/map/lose/win/round3 PASS unchanged`. (`default_ste_first_markerbug.txt` = first run, FAIL only because the gate did not expect `PMPO` in the 4 marker bytes; fixed.)
* **Pattern-fill build (23988 B of pattern in $72000-$77fff)** [obs `fill_ste.txt`]: `CELL DONE fill/ste-1.62-1024K: OK (490s)`, every payload@ line PASS: nothing in the whole scenario writes into the range.
* **Corrupted site** [obs `corrupt_ste.txt`]: marker `PMPF`, site left original, credit absent, payload unchanged, game booted on.
* **NOT finished when this was written** (chain still running in background, logs appear in `work/runs/`): corrupt map step, core-only boot/map/lose, original-disk baseline (zero-range check), Mega STE TOS 2.06 4 MB default+fill, handover register check. Not done at all: save/load (needs a formatted save disk; the game's floppy format uses write-track, unsupported by Hatari .st), TT/Falcon/ST cells, Unicorn-free but 512 KB machines.

## Explanation of `work/runs/default_ste_first_markerbug.txt` (lead's question)
Cause: the gate, not the game or the payload. `build/*/expect.bin` is the built payload image, whose marker long at `$727F8` holds its initial value (zero); the hook writes `PMPO` there at run time. The first gate version compared the whole `$72000-$77fff` with that file, so every checkpoint reported exactly the marker span and nothing else [obs, same run]:
```
GATE default/ste-1.62-1024K payload@options FAIL $727f8-$727fb   (identical line for @map, @lose, @win, @round3)
```
(the same run's `marker PASS $727f8 = b'PMPO'` line confirms the value). Fix in `tools/wwgate.py` (`cell`, right after the marker is read):
```
want = b"PMPF" if a.corrupt else b"PMPO"
expect[MARKER - IMG_BASE:MARKER - IMG_BASE + 4] = want   # the only byte the hook itself writes in the region
```
i.e. the expected image gets the marker the marker gate has just verified. Rerun `default_ste.txt` [obs]: `payload@options/map/lose/win/round3 PASS unchanged` = `$72000-$77fff` equals the expected image, marker included, so 0 other differences (the first run's failing span was only these 4 bytes, so nothing else differed there either). The first run's other lines (credit, map, pictures) were already PASS; it is kept unedited as the record.
