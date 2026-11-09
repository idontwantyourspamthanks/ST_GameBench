# Powermonger timing (P2): fixed 4.00 Hz world tick, render between ticks

Author: PMTiming. Patches (all `; default: no`): `patches/tick_head.s` (site `$13020`, blob `$B8800`, data `$B8A00`), `tick_pass.s` (`$13074`),
`tick_wx.s` (`$130b0`), `tick_men.s` (`$130c2`), `tick_click.s` / `tick_click2.s` / `tick_click3.s` (operand sites `$12f8`, `$1354`, `$1373e`).
Gate tool: `tools/pmtick.py` (`live`, `rate`, `ab`, `input`; has its own tiny live builder, no dependency on `pmpatch.py`). Everything below was run on
1 MB STE, TOS 1.62, Hatari 2.6.1, snapshots in `work/snapshots/`, evidence = raw output or disassembly (`tools/m68dis.py` on `work/dumps/*.bin`);
`[INFERENCE]` = not run.

## 0. Result

| item | status |
|---|---|
| World tick fixed at 4.00 /s from the VBL counter `$6f304` (half-VBL accumulator), at 8 and 16 MHz | done: 4.009 / 4.009 ticks/s (get_men, battle_320), 3.97-4.01 (map_idle), cold boot 1 MB and 4 MB: 4.008 / 4.003 and 4.079 / 4.008 |
| Rendering between ticks (no world logic in those passes) | done: 16 MHz get_men 8.20 fps (original 7.85), battle_320 8.25 (8.30), map_idle 6.25 (6.25) |
| Per-tick state equality vs the unpatched game | IDENTICAL, 11 runs (3 scenes x 8/16 MHz + a forced season change), whole RAM `$0-$60000` except listed masks, with a negative control and the RNG `$2df84` included |
| Cross-clock equality (patched 8 MHz vs patched 16 MHz, per tick) | IDENTICAL (get_men, 51 ticks) |
| Displayed frame of every tick pass == unpatched frame of that tick | 32 of 32 byte-identical, get_men and battle_320 at 16 MHz |
| Pointer / click / key responsiveness | same as the original at the same clock (section 6) |
| Cold boot of a patched floppy (`pmpatch.py build --floppy`), 1 MB and 4 MB | marker `PMPO`, sites patched, 4.0 ticks/s at 8 and 16 MHz (section 7) |
| Men interpolation | built later as `p3b_interp` + `p3b_delta` (predict-ahead, `; default: no`): `interp.md`. Camera real-time scaling NOT built |

## 1. What advances once per loop pass

The loop is `sub_012fd8` .. `bra.w $12fd8` (`$13888`); one pass = one flip in the original. Method: restore a snapshot, arm one breakpoint per call site
with `b pc = $site && ($2df70).l = N :trace :file` (N = current iteration + 40, so every site fires in the SAME pass; arming too close to the
iteration fires only the first sites), `savebin $0 $80000` at each, and diff consecutive dumps; stack/IRQ noise (`$2c8xx-$2c950`, `$1af3c` sample pointer,
`$1c48e/$1c49c` mouse, `$6f306` VBL, `$2df8c`) removed. get_men, battle_320 and map_idle gave the same list.

| call site (pass order) | routine | writes (raw ranges seen) | class |
|---|---|---|---|
| `$13040` | `$127e6` | `$12a6a`, `$5805c` | sound-effect queue (59 x 14 B at `$12952`, picks the best entry, plays it via `$1ba3e`; expiry stamps from `$6f304`). Logic stage, once per tick |
| `$13046` | `$6522` | nothing | reads `$2df72` (`cmp.w $2df72.l,d0` at `$65a0`). Logic |
| `$1304c` | `$d322` | `$57fbe` | group proximity scan. Logic |
| `$13052` | `$3e06` | `$4959a..$4d742` (grid/object chains), `$4c87a-$4cbca`, `$4ccde`, `$4ccf2`, `$4cd06`, `$516cc`, `$57fbe`, `$58050`; stores `$2df72` as an event timestamp at `$3720` | captain/army upkeep. World |
| `$13090`/`$13096`/`$130a4`/`$130aa` | VBL wait, `$12ce0` window copy, `$178ae`, `$f898` landscape+objects | nothing outside the screen buffers | render |
| `$130b0` | `$1abaa` | `$1aba0`, `$57fec-$57ff8` (season tick `$57fec`, weather LCG `$57ff6`, season `$57fd0`); code also writes the season picture at `$ff9e+$e80` | world (season/weather dissolve) |
| `$130b6`, `$130bc` | `$17878`, `$165b2` | nothing | HUD |
| `$130c2` | **`$14b62`** | the people table `$51b66` (x/z `+8/+10`, timers, state), cell chains `$49018.. $4d05e`, `$4ccec` | **the men simulation** (512 records x `$32`, state jump table `$14bb4`). `hotpaths.md` calls it "status bars": wrong |
| `$130c8-$130fc` | `$6a3a $7a56 $d23a $7202` | `$57fce` (`$d23a`), UI scratch | UI / windows, input driven |
| `$130d4` | `ff9a += $12f56` | `$ff9a` camera heading | camera animation (compass click), input driven |
| `$1373c..$13864` | click expiry, key table | `$4bb3a/c` scroll, `$ff9a` +-16 rotate, `$ff96/$ff98` tilt, `$ff9c`, `$57ffc` zoom (+ `jsr $fe04` view tables), clicks | camera/input |
| `$13864` | `$187a` flip, `$1a276` | screen pointers | render |
| loop head `$1302e`/`$13034` | `$2df70`++, `$4bb3e`++ | the counters | see below |

Two counters, both WORLD time, not pass counters:
* `$2df70` (long): `$3e06` stores its low word `$2df72` as a timestamp (`003720: move.w $2df72.l,$b4(a3)`) and `$6522` compares it (`0065a0: cmp.w $2df72.l,d0`).
  First version of the patch bumped it on render-only passes: battle_260 differed in one captain word from tick 329 on (`$51774`: unpatched `0149` = tick 329,
  patched `0165` = pass 356). Watch output (`b ($51774).w ! ($51774).w`): the one write came from `pc = $3728` in both runs. Fixed by `tick_click*` (below).
* `$4bb3e` (long): read by the renderer (`$f95e`) and the HUD (`$1624e`, `$16318`), and its low word `$4bb40` by `$14b7e` (men).
* `$2df70` is also the click lifetime clock: the VBL handler copies it to `$2df74` when a button event is latched (`$12f6`, `$1352`), and the loop clears `$2df96`
  at `$1373c` when `$2df70 != $2df74`. That one must count PASSES (R passes included) so a click does not live for a whole tick: `tick_click*` redirect
  those three source operands to a pass counter PASS (`D+32`) that `tick_head` bumps in every non-paused pass.
* RNG `$2df84`: users `$12c9a` callers in logic (`$14cd0` men, `$157c4/$15cb2/$15f40/$15f56`, `$1ac82` season, `$10464-$111f6` spawns). `$ffa6` (terrain generation) is not in the loop. The renderer only READS
  `$2df84` (`$116e8`, `$11712`). No render-time RNG draw was seen; equality below includes `$2df84`.

Not world: the sound queue `$127e6` only schedules samples; its expiry stamps (`$6f304`-based) are masked in the gate (`$12952-$12ca0`, `$58050-$58070`).
The speed track `$57fee/$57ff0` (game speed slider, `$74ce`, `$af9a`; default 1) already skips window copy, landscape and the flip for `$57fee-1` passes out of `$57fee`
but still runs logic: it is a render skip, not a slowdown. [INFERENCE] with the patch it stays a render skip (tick_pass keeps its countdown); a slider != 1 was not tested.

## 2. Camera and input

Camera heading/tilt/zoom/scroll (`$ff9a $ff96 $ff98 $ff9c $57ffc $4bb3a $4bb3c`, `$fe04` view tables) are render parameters only: no world routine reads them in the
equality runs (they are masked nowhere; the runs have no input so they are equal by construction, the claim is static + the 11 runs with R passes interleaved).
Decision (as the lead asked): **input and camera stay per pass (per frame)**. Evidence of the resulting rates, `pmtick.py input` (raw lines in section 6):
a held cursor key scrolls one cell per pass (3.0-4.5 steps/s at 8 MHz, 8.5/s at 16 MHz; same patched or not); the compass click rotates 4 units per pass
(`$12f56`), 64 units = 90 degrees take 16 passes. So camera speed is proportional to the frame rate, exactly as in the original; it is NOT real-time fixed.
Option for later (not built): scale the per-pass steps by the VBLs since the last pass (the compass animation needs the stop test `((ff9a+16)&$3f)==0`, so the step must be rounded to land on it).

## 3. Rate

Original passes per second at 8 MHz, 1000 VBL, from a restore (`/tmp/pmt/rate.py`, same as `pmtick.py rate --unpatched`):
```
get_men 8 MHz fps {'vbls': 1000, 'flips': 77, 'fps': 3.85, 'vbls_per_frame': 12.99} iter 135 -> 226 in 1187 VBL = 3.833 passes/s 13.04 VBL/pass
battle_320 8 MHz fps {'vbls': 1000, 'flips': 76, 'fps': 3.8, 'vbls_per_frame': 13.16} iter 346 -> 435 in 1187 VBL = 3.749 passes/s 13.34 VBL/pass
```
map_idle 8 MHz: 2.33 passes/s (21 VBL/pass; a sample IRQ is playing, 26 % of the CPU, `hotpaths.md`). 16 MHz: get_men 7.86, battle_320 8.26, map_idle 6.26.
Approved by the lead: **TK = 25 half-VBL = 12.5 VBL = 4.00 ticks/s** (1.04-1.07 x the 8 MHz pace in busy scenes). On a 60 Hz display it would be 4.8 /s
(the VBL is the time base, as in Midwinter; the game itself boots "60hz" but ran at 50 Hz here, RGB 50 Hz in the status bar) [INFERENCE for 60 Hz].

## 4. Design (4 hooks + 3 operand redirects)

```
tick_head  $13020  lea.l $14e20.l,a2 (6 B) -> jsr $b8800.l          every pass, before `tst.w $57ff2`
tick_pass  $13074  subi.w #1,$57ff0.l (8 B) -> jsr $b8900.l ; nop    the game's own render/skip branch (bne.b $130b0 stays)
tick_wx    $130b0  jsr $1abaa -> jsr $b8940.l                        weather/season: not on a render-only pass
tick_men   $130c2  jsr $14b62 -> jsr $b8960.l                        men: not on a render-only pass
tick_click $12f8, $1354, $1373e  move.l $2df70 -> PASS ($b8a20)     click lifetime counts passes
```
Pass kinds (flags in the data block D = `$B8A00`: LAST.w ACC.w SKIP.w RON.w TICKS.l RPASS.l SPASS.l PASS.l):
* **T** (ACC >= 25 after adding the VBLs since the previous look, x2): ACC -= 25, clamp 75. The pass is the ORIGINAL pass.
* **S** (T and ACC still >= 25): `tick_pass` forces the game's skip path (no VBL wait, no window copy, no landscape, no flip) and parks `$57ff0` at 1. Logic, season, men, HUD, UI, keys still run. This is how the 8 MHz machine catches up.
* **R** (ACC < 25: ahead of real time): `tick_head` drops its return, jumps to `$13058` (so `$2df70`++, `$4bb3e`++ and `$127e6 $6522 $d322 $3e06` do not run); `tick_wx`/`tick_men` return at once. Everything else runs: view limits, window copy + landscape + objects, HUD, UI/click dispatch, camera keys, flip. A render-only frame costs about one original pass at 16 MHz (R passes are 107 of 209 passes at 16 MHz get_men).
* Pause (`$57ff2 != 0`): the head clears flags, keeps LAST, ACC = 0 and returns: the original pass, not throttled (100 flips per 100 VBL measured while paused).
* Resync: more than 50 VBL (4 ticks) since the previous look (menus, disk loads, the counter was cleared/poked) -> one tick, no burst. Catch-up clamp 3 ticks.
* Frame rate: a pass is a frame; frames come at the CPU's rate, ticks at 4.00/s. Because the pointer is drawn into the displayed buffer by the VBL handler (`$13c4-$14c0`),
  it is unaffected by any of this.

Why render-only passes are safe: `$f898`, `$12ce0`, `$178ae`, `$17878`, `$165b2`, UI and key code wrote nothing that persists (stage diffs, section 1) and the full-RAM equality (section 5) holds with R passes interleaved.
Skipping `$14b62` and `$1abaa` after the render matches the original order: the frame of a tick pass shows the men as left by the PREVIOUS tick, and the R passes after it show them after the tick.

## 5. Gate (a): per-tick state equality (raw, `python3 tools/pmtick.py ab SNAP MHZ VBLS`)

Method (`log_passes`/`cmd_ab`): both runs restore the same snapshot at the same clock; at the first flip the patch is applied live (the unpatched run executes `e VBL` there, same
debugger stop); then every loop top (`b pc=$12fd8 :trace :file`, file = `savebin cur.bin $0 $60000`, copied by a poller thread) is dumped. Pairing key = `$4bb3e` (world ticks; R passes
repeat a key). Compared: every 16-bit word of `$0-$60000` (code, all tables, people, RNG, season, camera, `$2df70`). Masks: screens `$1c700-$2c100`, stack scratch `$2c100-$2cc00`
(a one-off `$2cba4` difference at 8 MHz tick 343 in battle_290, value `ac34` vs `b9d4` = a saved pointer `$5b9d4` in dead stack, referenced by no code), sample pointer `$1af30-$1af40`, mouse/pointer `$1c480-$1c4e0`,
click latch + screen pointers `$2df74-$2df84`, VBL flag `$2df88-$2df90`, sound queue/channels `$12952-$12ca0`, `$58050-$58070`, `$e3e2-$e3e6`, `$12f58`, `$8830`, and the 7 patched sites. "Missed loop tops" = quick S passes the poller did not catch (comparison is by key, so these just reduce coverage).
Negative control: patched tick k against unpatched tick k+1 differs in every loop top.
```
get_men 8 MHz: 39 loop tops over 39 ticks IDENTICAL; negative control 39/39; RNG differs 0, 3 distinct values; men records changed 20
get_men 16 MHz: 67 loop tops (R passes included) over 33 ticks IDENTICAL; negative 68/68; RNG 0; season counter 145..185
get_men 16 MHz + poke `w $57ff6 $06 $81` (next dissolve step = 0 = forced season change, RNG draw `$1ac82`, `$57fec` 6..46): 68 loop tops over 33 ticks IDENTICAL
battle_260 16 MHz: 64 / 36 IDENTICAL (after the `$2df70` fix; before it DIFF `$51774-$51776`, see section 1)     battle_290 8 MHz: 33 / 33 IDENTICAL (6 missed loop tops)
battle_320 8 MHz: 39 / 39 IDENTICAL; RNG 4 distinct      battle_320 16 MHz: 65 / 32 IDENTICAL; RNG 5 distinct
battle_350 16 MHz: 67 / 33 IDENTICAL                       battle_380 8 MHz: 39 / 39 IDENTICAL
map_idle 8 MHz: 28 / 28 IDENTICAL (23 missed loop tops: 46 of 102 passes are S passes there)   map_idle 16 MHz: 56 / 36 IDENTICAL
displayed frame at the first loop top of each tick: get_men 16 MHz 32 of 32, battle_320 16 MHz 32 of 32 byte-identical to the unpatched frame of that tick
cross-clock: patched 16 MHz vs patched 8 MHz, get_men: 51 loop tops over 51 ticks IDENTICAL (RNG 4 distinct, men changed 19)
```
The RNG is compared in every run (`$2df84` differs in 0 loop tops; it changes 1-5 times per run). Everything above ran with NO input.

## 6. Gates (b), (c), (d): rates, fps, input

(b)+(c) `pmtick.py rate SNAP MHZ 1000 [--unpatched]` (flips over 1000 VBL; ticks and passes over the ~1270 VBL the script's reads take; Hatari runs real time):
```
get_men 8 MHz patched: 1272 VBL, flips 76 (fps 3.80), world ticks 102 (4.009/s), passes 101 (3.970/s)   tick passes 102, R 0, S 6
get_men 8 MHz orig:    1247 VBL, flips 77 (fps 3.85), world ticks 95 (3.809/s)
get_men 16 MHz patched: 1272 VBL, flips 164 (fps 8.20), world ticks 102 (4.009/s), passes 102          tick passes 102, R 107, S 0
get_men 16 MHz orig:    1247 VBL, flips 157 (fps 7.85), world ticks 196 (7.859/s)
battle_320 8 MHz patched: flips 75 (fps 3.75), world ticks 102 (4.009/s)  T 102, R 1, S 5      orig: flips 76 (fps 3.80), 3.769/s
battle_320 16 MHz patched: flips 165 (fps 8.25), world ticks 102 (4.009/s)  T 102, R 108, S 0   orig: flips 166 (fps 8.30), 8.260/s
map_idle 8 MHz patched: flips 44 (fps 2.20), world ticks 101 (3.970/s)  T 102, R 0, S 46        orig: flips 46 (fps 2.30), 2.326/s
map_idle 16 MHz patched: flips 125 (fps 6.25), world ticks 102 (4.009/s)  T 102, R 57, S 0       orig: flips 125 (fps 6.25), 6.255/s
```
**map_idle at 8 MHz (lead's question):** the original runs 2.33 passes/s (the world crawls at 58 % of the stock pace while a sample plays). Patched: world 3.97-4.00 ticks/s (+70 %), fps 2.20 (original 2.30),
i.e. the machine cannot render 4 frames/s, so 46 of 102 tick passes are S passes (logic + HUD without render, no flip) and the ACC clamp of 3 ticks keeps it bounded. The cost of an S pass is
logic + `$14b62` + HUD, about 10 % of a render pass [INFERENCE from the stage split in baseline.md: logic 2 %, HUD 6 %; not measured per S pass]. DMA sound will remove most of the 26 %; then S passes become rare there (get_men: 6 S in 102).
Cold boot, map_idle state (raw, section 7): 8 MHz 4.008 ticks/s, fps 2.70 (3.50 on the third look; [INFERENCE] the sample had stopped by then, not checked).

(d) `pmtick.py input get_men MHZ [--unpatched]` (pointer: `rel` 30 px, first change of `$1c492` after the move; compass click at ST (36,162): first `$ff9a` step; Right key held 2 s: `$4bb3a` steps; times are host wall time, +-30 ms):
```
8 MHz  orig:    pointer 33 ms | compass first step 335 ms, 12 steps/3 s (4.0/s) | Right held 2 s: 6 steps (3.0/s), first 296 ms, step 298 ms
8 MHz  patched: pointer 31 ms | compass first step 315 ms, 11 steps/3 s (3.7/s) | Right held 2 s: 8 steps (4.0/s), first 162 ms, step 241 ms
16 MHz orig:    pointer 33 ms | compass first step 162 ms, 17 steps/3 s | Right held 2 s: 17 steps (8.5/s), first 51 ms, step 120 ms
16 MHz patched: pointer 42 ms | compass first step 102 ms, 17 steps/3 s | Right held 2 s: 17 steps (8.5/s), first 31 ms, step 117 ms
```
The overview click at ST (22,51)/(40,70) did not change the scroll (already centred); not measured. The query window and icon clicks were not exercised in a patched run
(only through the shared dispatch code, which runs unchanged on every pass). Pointer, click-to-effect and key latency follow the frame time of the clock, patched or not.

Pause and resync (live, 16 MHz, `/tmp/pmt/pause.py`): `$57ff2` poked to 1: `$4bb3e` stays 181 for 3+ s while `fps(100)` shows 100 flips/100 VBL (the pause pass is the original, unthrottled);
unpoked: ticks continue 184 -> 207 in 2 s (no burst, ACC 23 / 10). `$6f306` poked from `$240e` to `$2000` (counter went backwards): ticks go on (227 -> 251 in 2 s, ACC 7 / 6): the gap resyncs instead of bursting.

## 7. Cold boot (`pmpatch.py build --only tick_head tick_pass tick_wx tick_men tick_click tick_click2 tick_click3 --floppy`, `boot_to_game`, then clocks via `set_cpuclock`)
```
1 MB STE TOS 1.62: boot True 200 s; marker b'PMPO' site $13020 4eb9000b8800 $13074 4eb9000b89004e71
  8 MHz: 711 VBL, ticks 57 (4.008/s), fps 2.70, T 57 R 0 S 18
  16 MHz: 712 VBL, ticks 57 (4.003/s), fps 7.00, T 57 R 43 S 0
  8 MHz: 711 VBL, ticks 56 (3.938/s), fps 3.50, T 57 R 0 S 7
4 MB STE TOS 1.62: boot True 188 s; marker b'PMPO' ...
  8 MHz: 711 VBL, ticks 58 (4.079/s), fps 2.20, T 57 R 0 S 26      16 MHz: 57 (4.008/s), fps 6.20, R 32      8 MHz: 57 (4.008/s), fps 3.00, S 14
```
`pmpatch.py verify` accepts all 7 sites against the file-derived resident image. HD build (`--hd`): not booted.

## 8. Rendering looks right
Screenshots from patched runs show the intact 3D view, HUD and sprites (angels rising in battle_320 at 16 MHz: `/tmp/pmt/s_16_1_2.png`, not kept in the repo). Consecutive-screenshot pixel differences (pointer + men + rain): 16 MHz patched [2864, 2820, 3100] vs original [3220, 3244, 2988]; 8 MHz patched [4608, 3752, 3756] vs original [6524, 4496, 4344].
The strong statement is the byte-identical tick-pass frames (section 5).

## 9. Options not built (report; lead decides)
**Men interpolation (p3b-style smooth walking).** Now an R pass redraws the same men: frames between ticks differ only in pointer, camera and `$1abaa` rain/season state. Men move 32 units per axis per tick; with 256 units per cell (the world is 64 x 128 cells for x/z words `$0-$4000` / `$0-$8000`; [INFERENCE] from the position words in `entities.md`) that is 1/8 cell per tick, roughly 3-4 px at the default zoom (about 8 cells across 256 px, [INFERENCE]), i.e. 4 jumps/s of 3-4 px. Only 16 MHz+ machines (frame > tick) would see a change.
* Mechanism: an R-pass wrapper around `jsr $f898` (site `$130aa`) that adds `k/n * delta` to x/z (`+8/+10`) of every live person record (`byte +5 > 0`), restores them after the render. `delta` = position now minus position at the previous tick (a 512 x 4 B copy per tick). Cost [INFERENCE]: copy ~10 k cycles per tick, wrapper 2 x 512 x ~30 = ~30 k cycles per R frame, i.e. 1.5 % of a 16 MHz pass; fewer if only records with a non-zero delta are kept in a list.
* k/n: n = frames until the next tick, known only by prediction: extrapolate (no latency; wrong by up to one step at a stop/turn) or interpolate P(k-1) -> P(k) (exact, men drawn one tick = 250 ms late). The sprite is drawn in the cell chain of its tick position, so across a cell border it is sorted one tick late (small, [INFERENCE]).
* Rotating/zoom/camera: already per frame, nothing to interpolate; real-time scaling of camera speed is the open item of section 2.
* Season dissolve (`$1abaa`, 16 px per tick) would still step at 4 Hz; terrain texture animation does not need interpolation.
Recommendation: build it after the P3 speedups, since at 8 MHz (frame >= tick) it changes nothing and at 16 MHz the first thing a user sees is 8 identical-frame pairs.

## 10. Limits / open
* World speed follows the VBL rate (50 Hz PAL: 4.00; 60 Hz: 4.8) [INFERENCE].
* Camera/scroll/rotate speed still follows the frame rate (section 2).
* Windows/messages (query, "You have been defeated", message timers) were not exercised: if a HUD/UI routine counts passes, it now counts frames (R passes). No such counter was found in the call-site diffs or by scanning the UI code for read-modify-writes on absolute words (only UI scratch `$7a30-$7a39`, `$2df6c`, `$71fd/$71fe`, `$580a0`); a UI test run is open.
* `$57fee > 1` (speed slider) not tested with the patch.
* `tools/pmtick.py` builds its own live image from `patches/tick_*.s` (vasm, `$B8800` base); the contract's `pmpatch.py live` was not used for the gates.
