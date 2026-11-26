# Nebulus v1.2 (HEAD cf52f4f) HD gate: NebGate12HD

Build: `nebrelease.py build --out /tmp/ng12hd/s/hd` from the clean committed tree (`git status` of patches/ and tools/ clean before and after). NEPATCH.BIN md5 `f471dd18e595932c00fdb0222eb6cc77`, START.TOS `4ecf26d8…`, NEBLEVEL.OVL `0829f717…`. v1.1.1 control build (git archive 20e26f7, same tool) NEPATCH `f6ba0b30937aefabf1ad0ac694eb378a` = the shipped v1.1.1 md5.
Raw logs: `gate12/logs/{ste,megaste,st,core,core2,core3,looks}/`, `s1_*.txt`, `s0_snapshots.txt`, `script_diffs.txt`; scripts: `gate12/scripts/`. Scratch /tmp/ng12hd, private HOME, one Hatari at a time.

## 1. Static
- `nepatch verify`: `33 verified sites, 3 clear ranges (332 B), 11 blocks; ZONE_STRICT=False` (`logs/s1_verify.txt`).
- `gen_ed.py` run on a copy (output .nep to scratch; regenerated .nep `cmp`-identical to committed): `CODE1 free 36; DATA 108; CODE2 $77300..$779a0 1696 B free 90; CODE3 34; CODE4 4; CODE5 2; CODE6 4 | total 9152 B` = 278 B free; CODE2 ends $779a0 < $779fa.
- Credit blob: `cr_credit.nep` site `$779fa` + hook `$3d698 4eb9000779fa4e71`; blob with `v1.2 enhanced by dad_prg` found in the NEPATCH.BIN and in the title snapshot RAM (`s1_static_extra.txt`). `nebrelease.py check` of the fresh build: 11/11 members same.

## 2. Snapshot signature proof (`logs/s0_snapshots.txt`)
Signature `SNAP_EXPECT=0203131402020202` (the `ltile` conveyor tile table, 1 occurrence in the cf52f4f NEPATCH, 0 in v1.1.1; `Conveyor left` string also checked, 2 / 0). Fresh snapshot per machine from this build, all three contain it (`v12 ste|megaste|st … present`). v1.1.1 STE snapshot: `GUARD FAIL (expected for v111): stale snapshot …v111_ste.sav: 0203131402020202 not found`; v12 STE snapshot: `GUARD PASS`. Snapshot-based gates got `--snap`/the guard (e180/e190 via SNAP_EXPECT; e200/e201/e203/e204/e205/e208 have built-in string guards).

## 3. Editor gates (PASS counts / FAIL lines; every log ends `FAILS []` unless noted)
| gate | STE TOS1.62 | Mega STE TOS2.06 | ST TOS1.04 |
|---|---|---|---|
| e200 pickers/crumble/round trip | 38/0 | 38/0 | 38/0 |
| e201 crumble+conveyor levels | 17/0 | 17/0 | 17/0 |
| e203 door pairs | 30/0 | 30/0 | 30/0 |
| e204 copy tower x16, blank, time, name | 22/0 | 22/0 | 22/0 |
| e205 fine crumble probe | **2 PASS, FAIL `open manager` + IndexError** | 8/0 | **2 PASS, same FAIL** |
| e206 crumble+exit (fixed one-col-past-door) | 7/0 after scratch fix (first run 6/1, see below) | 7/0 | 7/0 |
| e208 conveyors in play (carry) | 46/0 | 46/0 | 46/0 |
| e150 | 32/0 | 32/0 | 32/0 |
| e170 cold boot (NEPO, 33 sites) | 12/0 | 12/0 | 12/0 |
| e180 odd2 + looks.ovl `--disk` | 176/0 | 176/0 | 176/0 |
| e180 all12 `--quick` | 25/0 | 25/0 | 25/0 |
| e180 odd2+stress01+stress05 `--quick` | 65/0 | 65/0 | 65/0 |
| e190 (old Tower > Colours: next UI) | script exception, see below | same | same |
| e202 user-image flow (all-games image, NEBULUS replaced by this build, Mega STE) | n/a | 17 PASS, `FAILS []` | n/a |
| e207 | script does not exist in the repo (only gate2's log); not run | | |

Failures and notes:
- **e205** (a probe script, not in gate2's table): on STE and ST it dies in the second level: `open manager: False`, `IndexError` in `pick`; gate2's own STE log shows the same two FAILs (`work/looks/gate2/logs/e205_ste.log`); Mega STE passes 8/8. The first level (crumble walk) completes on all three. Cause not investigated [INFERENCE: manager not reachable while the frog is falling/dead at the time of the F10 poll]. e206 and e201 cover the crumble behaviour and pass.
- **e206** first STE run: 6 PASS + FAIL `no Address/Bus Error/exception`; the 6 lines are Hatari WARNs at boot (log lines 9-14 of 467: `Bus Error reading at address $fff000xx/$ffff8781/$ffff8e21, PC=$d51c/$bbc2/$1b5ec`, TOS/HDDRIVER hardware probes; the other gates run from snapshots so their logs lack them). Scratch fix: that check ignores `Bus Error reading at address $ffxxxxxx`; STE re-run: `PASS no Address/Bus Error/exception … []  FAILS []` (`logs/core2/e206_ste_rerun.txt`); Mega/ST ran with the fix (7/0). Diff in `script_diffs.txt`/`scripts/e206_fixed.py`.
- **e190** tests the pre-picker v1.2 UI (`Tower > Colours: next`), which cf52f4f replaced by `Level >` list pickers (e200 covers them): `PASS ui: F10 opens the manager`, `PASS new level starts with flags 0`, then `IndexError` in `pick` on all 3 machines. Obsolete script, not a product failure [INFERENCE from the menu change; not separately verified].
- e208 on Mega STE/ST = the in-play conveyor carry check (+1/-1 per step, crumble fall): 46/0 on all three (item 5); e201/e206 also cover crumble in play on all three.

## 4. Looks (`logs/<m>/check_looks15.txt`, `logs/looks/`)
| gate | STE | Mega STE | ST |
|---|---|---|---|
| base8 run (8 stock towers) | 8 levels | 8 | 8 |
| looks15 `check_look.py` (15 cells + 15 screenshot-crop equalities, incl. the 8 colour schemes on T3 "as-tower" = stock tower c crops `equal`) | 15 PASS, `FAILS 0` | 15 PASS, `FAILS 0` | 15 PASS, `FAILS 0` |
| st6 | – | – | 6 PASS, `FAILS 0` |
| all12 (`check_all12.py`) | 12 levels, `FAILS 0` | not run | not run |
Negative controls: (a) wrong expectation = base8 reference with tower 3 and 4 swapped: `FAILS 15` (`logs/ste/neg2_wrongexpect_check.txt`); (b) v1.1.1 build with the looks15 file: `FAILS 27` (`logs/looks/neg_check_ste.txt`, 12 `DIFF` crops).
Enemy sets 3 and 4 on screen (STE, T trainer not used for E; level played with enemies on, NOE=1): eye frame RAM `$24be0` md5 set 3 = `3892848c` = stock T3, set 4 = `d65f1a45` = stock T4 (`rsEye` 0002/0003). Screenshots `shots/eye3_play.png` (four-dot cluster beside the tower) and `shots/eye4_play.png` (blue butterflies); the two screenshots differ only in x 248..582, y 138..172 (the eye band; 10680 vs 10484 non-black px, `logs/looks/eyes_pixels.txt`). Anomaly: in the 5-level `eyes5` run the lvl3 and lvl4 screenshots are pixel-identical [INFERENCE: stale capture], the standalone runs above are the evidence.

## 5. Core (e98 / junk RAM / stall / lift / shot / trainers)
- e98 equivalence (`logs/core2/e98.txt`, same script and set as v1.1.1; the first attempt failed immediately on the 23-byte snapshot path field with my long workdir and was rerun with a short one): patched vs stock, `74 of 74 not explained: []`, `framebuffer event 1 differing bytes, rows: (5339, (3, 166))`, `simulation state differs … 1076 of 1115 loops` (v1.1.1: 1075 of 1114; identical pattern).
- Cold-boot cells (`logs/core/cg_*.txt`): STE/ST `marker NEPO sites 33`, hooks incl. `$3d698 4eb9 0x779fa`, E/T behave as v1.1.1 (`T … frozen False` text is identical to the v1.1.1 output), 20 s drive 14 rounds vbl +1046 (STE) / +1043 (ST) / +1253 (Mega, identical line to v1.1.1), crash lines 0.
- Dump compare (`logs/core/dump_*`): text md5 differs v1.1.1 vs v1.2 by design (33 vs 27 sites); marker `4e45504f00210000`.
- Junk RAM, 3 random-RAM boots per mode (seeds 1,2,3), STE and Mega STE, modes rs and all: 12/12 rows `title true, marker NEPO, sites 00210000 (33), v70 000382d8`; leftover-RAM relaunch (2 seeds each) 4/4 same.
- Trainers T/E (`train_*`): STE and Mega: T on frozen, T again runs, E again `noen 0x0`.
- Input stall sweep: STE 6 tap times + control and 8 random trials: all `alive true, isr_hits 2` (`logs/core2/ik_*`). Mega STE: the first two sweeps (`logs/core2/ik_sweep_mega.txt`, `logs/core3/ik_sweep_mega.txt`) gave `isr_hits 0, alive false` for EVERY spec including the no-tap control; I could not explain it. Control with a freshly made snapshot (`logs/core3/ik_ctl_mega.txt`): v1.1.1 none and 0.3 s tap alive, v1.2 none and 0.3 s alive; full 0.0..1.4 s sweep on that snapshot: 6/6 `alive true` (`logs/core3/ik_sweep_mega_v12_ctlsnap.txt`). [INFERENCE] the first two Mega sweeps are a snapshot/harness artifact (the no-tap control failed too); the root cause is unproven.
- np_lift (tower 6 lift ride, 2 rides, `logs/core2/lift_ana_r*.txt`): `loops 213, VBL/loop 2.005, >2VBL 1 (0.5%), state6 ride 92 loops 1 at 3 VBL, busy max 320168/320196` = the accepted v1.1 figure (1 of 92).
- np_shot sweep (`logs/core3/shot_ship.txt`): random 60 HIT 59 / MISS 1; targeted-miss 30 HIT 30; single NON-HIT k=10 — identical to the v1.1.1 output.

## 6. Not run / limits
e207 (no script), floppy gates (outside this HD scope), ST junk/stall/e98 (scripts support STE/Mega STE only), all12 look gate on Mega/ST, ikg `ctl`, f161.

## 7. Script changes (all scratch, tracked files untouched; `script_diffs.txt`)
Path rewrites of /tmp/nlg, /tmp/ne, /tmp/looksgate, /tmp/oddcore and repo work/ paths to /tmp/ng12hd; workdirs shortened to /tmp/ng12hd/q (snapshot path field limit); `sitecustomize.py` redirects `Hatari.savemem` from the shared /tmp/hatari.sav to the private HOME; `attempts.json` copied for hat_g; e206 boot-probe filter (above). Fixtures: looks/odd .ovl regenerated by `mk_looks2.py` (byte-equal to the earlier ones), odd*.ovl copied (md5 equal).

## 8. Verdict
No product failure found. Open script-side items: e205 on STE/ST (also in gate2), e190 obsolete, the unexplained first Mega STE stall sweeps (re-run clean), e207 absent.

## 9. Follow-ups (e205, e190; logs `logs/f/`)
**e205 = script timing, not product.** Evidence (STE): at the point where the script presses `q` after the fall, RAM shows `$33a20 = 8` (frog dying) or `$a`, `$33938 = 0` (game loop not running), frog (4,0,10); `q`/F10 are not polled then. Diagnostic replay with state reads + screenshot between the steps (`e205_diag_ste.txt`) already passed 8/0 on STE; replay that waits until `$33a20 = 0 and $33938 = 1` before `q` (3.2 s, 3.2 s, 0.9 s waits; `e205_paced_ste.txt`) passed 8/0. Fixed scratch script `scripts/e205_fixed.py` (diff `scripts/e205_fixed.diff`): **STE 8 PASS / 0 FAIL, ST 8 PASS / 0 FAIL** (`logs/f/e205_fixed_{ste,st}.log`); Mega STE already 8/0 unmodified. v1.1.1: the steps need the crumble ledge `$91`, which v1.1.1 does not have, so no v1.1.1 replay exists.
**e190 = obsolete.** Its only entry point is `run_ui()` (the `run_file`/`run_flow` bodies are never called; e180 covers files/flow). It asserts: new level flags 0; cycling `Tower > Colours: next` 1..8,0,1 and `Enemies: next` 1..4,0,1 with the other nibble untouched; flags `$53`; playtest palette/raster/skyline/eyes == stock; `$3390c`; back in editor flags kept; committed flags; store validates; Save/Load disk keep flags; Edit shows flags; Copy keeps flags; Delete keeps the others; Play of a `$10` record = stock tower 1 look; no errors. Coverage now: e200 (new level flags 0; Level > Colours/Enemies pickers incl. wrap-free list, cursor re-theme; pick writes tower byte / enemies nibble; playtest palette/raster/skyline/eyes == stock; `$3390c`; back in editor; committed record; validates; Save/Load disk; Edit shows pick; Copy keeps record; no errors) and e204 (Copy tower, Blank grid, time, name). The cycling items and the `$53` colour-nibble value no longer exist (the picker writes the TOWER byte). Legacy flags-nibble records (Delete keeps flags, Play of `$10`/`$53` records): looks15/all12 (campaign play of flagged records) and `e180 --flags` (flags byte preserved through edit/Load/Save/Copy/Delete), run now on all three: **STE 19/0, Mega STE 19/0, ST 19/0** (`logs/f/e180_flags_*.log`). Nothing left uncovered, so no port needed.

## 10. Recommendations for the tracked scripts
- e190.py: delete (obsolete, fully covered above).
- e205.py: update with `scripts/e205_fixed.diff` (wait for the running game loop before `q`; the diff also adds state prints; path lines already filtered out). Keep as a probe or fold into e201.
- e206.py: update with `scripts/e206_fixed.py` (ignore boot-time `Bus Error reading at address $ffxxxxxx` TOS/HDDRIVER probe warnings; 7/0 on all three). It is a scratch copy with path rewrites: apply only the one changed line 92 (see `logs/script_diffs.txt`).
- e207: no script in the repo (only gate2's log, a PATHL/PATHR crumble walk covered by e201/e205/e206): nothing to keep; do not recreate.
