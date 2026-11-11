# Powermonger: the phantom click at the start of play (found and fixed 2026-11-11)

Tags: **[obs]** observed in Hatari 2.6.1 (raw output kept in `work/phantom/`); **[disasm]** `tools/m68dis.py` on `work/dumps/get_men.bin`; **[INFERENCE]** not verified.

**Report (user, STE / Mega STE / TT, the release build):** as soon as Powermonger loads into the first level it looks as if the game receives a click that
moves the troops with the captain: they end up on the side of a hill instead of in the circle around the castle.

## 0. Result

The click is not a mouse click: it is the **player's name typed at the name prompt**. `qol_keys2` (the keyboard-interrupt half of the key shortcuts)
records every make code in `PEND` from the moment the game's own keyboard handler exists - long before the 3D view - and `qol_keys` replays `PEND` one
icon click per pass from the first pass of the map. A name with `R` (Derank) disbands the starting formation, so the men never move out into their
circle around the castle; `H` (Go Home) issues an order; `A G M F Y S T` (measured) leave a command selected that the player's first real click on
the map then executes at that point.

Fix (`qol_keys` + `qol_keys2`): a key counts only while the map loop runs. The pass hook stamps `LASTV` = the VBL counter `$6f304` every pass, the
interrupt drops a press that comes more than `WIN` = 150 VBLs (3 s) after that stamp, and the first pass after a longer gap (game start, a menu, a disk
access) clears `KS`, `REP`, `OWN9E`, `ANY` and `PEND` before the scan. Cold boots with the fix (floppy and hard disk, name `Ryan`): all 26 men in the
formation (state `$0e`, 165-224 world units from the captain), byte-identical positions to the unpatched game; a real `F` afterwards still gives
`$57fd4` 6 (Get Food) and 0 again.

## 1. Reproduce (`tools/pmphantom.py`)

Cold boot the way the user plays, with a per-pass log of the click latches, the key latch (`qol_keys` data) and the captain's job from the pass before
the island click:

```
python3 tools/pmphantom.py --disk build/<kind>/floppy/powermonger.st --name Ryan --out /tmp/ph/a   # the patched floppy; <kind> = phantom (old) / phantom2 (fixed)
python3 tools/pmphantom.py --vhd dist/AtariST_enhanced_games_2026-11-11.vhd --name Ryan --out /tmp/ph/b   # the user's start: PMBOOT, P, intro, name
python3 tools/pmphantom.py --disk disks/protected.st --name Ryan --out /tmp/ph/c                  # the original (the question is answered from RAM)
```

Boot stages are separate from `pm.boot_to_game`: the pass logger (`b pc = $130fc :trace :file`) is armed **before** the island click, so pass 1 of
the map is caught, and the first pass also dumps the world tables (`savebin $4e000 $a000`).  Afterwards the tool dumps those tables and takes a
screenshot every 2.8 s for 30 s and prints the army's state, its distance to the captain and the captain's job / target.  `--snap-out` / `--snap`
take a chart-screen snapshot once and replay single keys from it (`--keys R`), `--secs`/`--step` set the capture, `PMPH_KEYS=0` skips the real-key test.

The user's start differs from the harness's only in one thing that matters: the harness types `Bench`, the user types his own name. Both flows press
`space` through the intro and `Return` at the name prompt. (`P` at PMBOOT is read by TOS's `Cnecin` before the game runs. `space` and `Return` are
recorded in `PEND` like every other scan code, but they are not in the click table `KT`, so they can never become a click.)

## 2. What the log shows (raw lines: `work/phantom/*/passes.log`)

`m` dumps of the latches at every pass (`pc = $130fc`; the site is `jsr $7202` in the original, `jsr $cf830` with the fixed `qol_keys`):

| configuration | first passes of the map: click position, latches, `$57fd4`, job, `PEND`/`ANY` |
|---|---|
| original, name `Ryan` | click `00140012` (unchanged, = `ISLAND_XY` from `goto_st`), `$2df96/$2df98/$2df9e` 0, `$57fd4` 0, job 6, no key hook; pass 5 shows `$2df96` = 1 once (the previous window's close), dropped next pass |
| original, name `Bench` | same; `$57fd4` 0, job 6 |
| old default build, name `Ryan` | pass 1: click `00140012`, `$57fd4` 0; pass 2 click `00f400bf` -> `$57fd4` `$c`; pass 3 `00ad00bc`; pass 4 `00fc00a8`; pass 5 `00480095` -> `$57fd4` `$20`; **no mouse latch ever set** (`$2df96/$2df98` stay 0) while `ANY` = 1 on every pass until the 4 letters are consumed |
| old default build, name `Bench` | pass 2 click `012a009d`, pass 3 `006400aa` (job 7 = Go Home at pass 3, back to 6 at pass 5), pass 4 `00ad00bc`, `ANY` 0 after pass 4 |
| fixed build, name `Ryan` | pass 1: click `00140012`, `$57fd4` 0, job 6, `ANY` 1 -> 0; passes 2.. stay `00140012`, `$57fd4` 0 |

The click positions are the `qol_keys` table points of the letters: `00ad 00bc` = (173,188) = `N` Drop Items, `00fc 00a8` = (252,168) = `R` Derank,
`0048 0095` = (72,149) = `Y` Spy, `012a 009d` = (298,157) = `E` Equip, `0064 00aa` = (100,170) = `H` Go Home, `00f4 00bf` = (244,191) = `A`.  They are
in `KT` order, one per pass.  At the chart, `PEND` already held them (`CD4B4`..: E, N, H, R, space, B, ... - the name, the `space` presses of the
intro and the `Return`).

So: `qol_keys2`'s interrupt records a press for every scan code (`$199c`, from the moment `$18be` exists), `qol_keys` consumes one per pass from the
first pass whose ANY/REP is set, and nothing ever cleared what was recorded before the map.

## 3. Effect on the opening (measured, `analysis.txt` in each run)

The army is the 26 live person records (people table `$51b66`, stride `$32`) near the captain's person record; the captain is record `$57ffe` of the
captain table (`$51538`, stride `$13c`, +$4c; job word at +0, the person offset at -$c, target x/z at person +$14/+$16).  State `$0e` (person byte 6)
is the formation around the castle: the records become 26/26 `$0e` and settle at 165-224 units from the captain, which is the visible circle around the
castle in the 3D view.

| run | pass 1 | t+5.6 s and later | captain job / command |
|---|---|---|---|
| original, `Ryan` | 26 near the captain at 40-56 | 26/26 state `$0e`, 165-224 | job 6, no command |
| original, `Bench` | same | 26/26 `$0e`, 165-224 | job 6 |
| old build, `Ryan` | 40-56 | **0/26 `$0e`**, a block 8-128 from the captain (behind / inside the castle, no circle) | job 6, `$57fd4` = `$20` (Spy) left selected |
| old build, `Bench` | 40-56 | 26/26 `$0e` 165-224 but the order target is set (`40,51` = Go Home) | job 6 after pass 5 |
| fixed, `Ryan` (floppy, HD, Mega STE, TT) | 40-56 | 26/26 `$0e`, 165-224 | job 6, `$57fd4` 0 |

Single keys replayed from a chart snapshot on the **old** build (`--snap chart_old.sav --keys K`), same measurement: `R` -> 0/26 `$0e` (the block);
`H` -> 26/26 `$0e` + Go Home issued (job 7 for two passes, target `40,51` - the captain is already home, so the formation survives); `A G M F Y S T X`
-> 26/26 `$0e`, `$57fd4` set to the command (`$c 2 8 6 $20 $1c $1a`), i.e. a command stays selected for the player's first click; `N` -> formation.

Unpatched game with the same input (name `Ryan` or `Bench`): no phantom click at all (`$57fd4` stays 0, the army takes its circle).  `pm_noprot` is not
involved: the patrol/decoy check never waits for a click of the player (protection.md 3.1: the trigger fakes the click itself, `$11c12`), and the
question's answer clicks are mouse clicks that land in the question box - in the original run of section 2 the click latch is set once (pass 5, the
window-close click) and dropped again the next pass, and `$57fd4` stays 0 throughout.

## 4. The fix

`patches/qol_keys.s` (pass hook, moved $cf860 -> $cf830; it grew by 44 bytes):
```
.o9:    move.l  $6f304.l,d0             ; the stamp: this pass, and the gap since the previous one
        move.l  d0,d1
        sub.l   LASTV.l,d1
        move.l  d0,LASTV.l
        cmp.l   #WIN,d1
        bls.s   .run
        lea     KS.l,a0                 ; first pass after a gap (game start / a menu / a disk access): drop every key state recorded meanwhile
        moveq   #(LASTV-D)/4-1,d0
.fl:    clr.l   (a0)+
        dbra    d0,.fl
.run:   ...
```
`LASTV` = `$cd524` (new, after the 196 bytes `KS`..`PEND` that the flush clears), `WIN` = 150.

`patches/qol_keys2.s` (interrupt hook, moved $cd530 -> $cd610: the old place has room for 48 bytes, the new code is 62 and $cd560 is qol_hover2's hook):
```
kh:     move.b  d0,$1c490.l             ; the displaced instruction
        tst.b   d0
        beq.s   .r                      ; a break code
        move.l  $6f304.l,d1             ; VBLs since the last pass hook (LASTV = 0 before the first pass: a huge difference)
        sub.l   LASTV.l,d1
        cmp.l   #WIN,d1
        bhi.s   .r                      ; the loop is not running: not a shortcut
        ...
```
Cost: 3 instructions per key press (about 50 cycles), 16 per pass (the stamp + compare; the flush runs once per gap).  The `m $cd460` dump at the
chart and every pass log in the fixed builds show no replayed keys.

Why a VBL stamp and not a flag: the loop stalls for seconds inside a disk access (the HD build's GEMDOS calls, a save-game write) while the ACIA
handler keeps running, and the game's own menu/chart loops are outside this loop: all of them are "not the map view".  `$6f304` is the game's own
counter (`addq.l #1,$6f304` at `$1286`, no other writer), so no new time base is needed.

## 5. Gates

| gate | result |
|---|---|
| `pmpatch.py verify`, `build` (floppy + HD) | ALL ok, 36 / 40 sites, no overlap; hook $cf830, KT to $cfa71 (qol_hover starts $cfa80), KH $cd610 (+62 B, ends $cd64d) |
| cold boot, patched **floppy**, STE TOS 1.62 1 MB, name `Ryan` (`work/phantom/fix2_fl_ryan/`) | 26/26 `$0e` at 165-224 from the first capture, captain not moved, job 6, `$57fd4` 0, click position constant `00140012`; a real `f` after the capture: `$57fd4` 0 -> 6 -> 0 |
| cold boot, patched **HD** (ACSI image, HDDRIVER, AUTO\PMBOOT.PRG, `P`), STE TOS 1.62 1 MB, name `Ryan` (`fix2_vhd_ryan`) | same; `f` 0 -> 6 -> 0 |
| cold boot, patched floppy, **Mega STE** TOS 2.06 4 MB, name `Ryan` (`fix2_mste`) | same |
| cold boot, patched floppy, **TT** TOS 3.06 4 MB 32 MHz, name `Ryan` (`fix2_tt`) | same |
| cold boot, **the packaged floppy** (`build/dist_build/floppy/powermonger.st`, `package.sh` output), STE, name `Ryan` (`final_fl_ryan`) | 26/26 `$0e` 165-224, `$57fd4` 0, `f` 0 -> 6 -> 0 |
| cold boot, **the rebuilt all-games image** (`dist/AtariST_enhanced_games_2026-11-11.vhd`, `make_hd_image.py --no-build` after refreshing POWERMON), ACSI + PMBOOT, STE, name **`Harold`** (`final_vhd_harold`) | 26/26 `$0e` 165-224, job 6 with no order target (an `H` used to issue Go Home), `$57fd4` 0, `f` 0 -> 6 -> 0 |
| the army's person records, fixed vs the unpatched original (same name, both at t+28 s) | **25 of 27 records byte-identical, 0 positions differ** (the 2 differences are the iteration-dependent bytes of records 21/22) |
| `tools/pmab.py` gate (base = the previous default set, patched = + p7 + the four qol patches, 3 snapshots, 8 MHz, `--walk --tipmask --c3 70000`) | **ALL IDENTICAL**: map_idle back 39/both 35, get_men 60/36, battle_320 64/45; work/pass +1.09 / +0.83 / +1.06 % (`work/phantom/ab_fix.txt`) |
| `tools/pmqol_state.py get_men 8 700 0` (key == click, the new `qol_keys` / `qol_keys2`) | **IDENTICAL** (every command issued by a key == the same command issued by a click; camera words equal) |
| `tools/pmtick.py ab get_men 8 700` / `tools/pmtriple.py state get_men 8 700 --qol` | **IDENTICAL** (54 and 75 loop tops, negative controls differ everywhere) |

## 6. Tools / files

* `tools/pmphantom.py` (new): the cold-boot repro with the pass logger and the army/captain analysis, the chart snapshot (`--snap-out`) and the
  single-key replay (`--snap ... --keys`), the real-key test.
* `tools/pmcombined.py`: the qol sites are now `$cf830` and `$cd610`.
* `work/notes/qol.md`: the layout table and the mechanism section.
* Raw output: `work/phantom/`. Per run: `out.txt` (the tool's whole stdout: boot stamps, the key-latch dump at the chart, the analysis table, the
  pass table, the real-key line), `analysis.txt`, `key_latch_at_chart.txt`, `shot_00.png` / `shot_10.png`, plus the four gate logs
  (`ab_fix.txt`, `qolstate_fix.txt`, `tickab_fix.txt`, `triple_state_fix.txt`). The per-capture world dumps and `passes.log` stay in `/tmp` (about
  10 MB per run): rerun the commands of section 1 to get them.
