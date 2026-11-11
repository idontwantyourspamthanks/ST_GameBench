# Powermonger: rain on every rendered frame (PMRain, 2026-11-10)

User report (Hatari TT): rain shows on about 5 of the ~20 frames a second. Cause confirmed, fixed by `patches/tick_rain.s` (`; default: no`; it REPLACES `tick_wx`, same site `$130b0`).
Tags: **[obs]** raw tool output below, **[INFERENCE]** not run. Tools: `tools/pmrain.py` (new), `tools/pmstagedraw.py` (new), `tools/pmab.py --swap OLD NEW` (new option), `tools/pmtick.py` with `PM_WX=tick_rain` (new env var; adds one mask, see 4).

## 1. What `$1abaa` does (disassembly of `work/dumps/get_men.bin`, `m68dis.py 1abaa`)
| part | code | class |
|---|---|---|
| `$1abaa-$1abbe` | `$1aba0.w += $1ab9e` (`$1ab9e` = `$0100`, set only by `$1ab90` from `$1ab88`/`$1ac46` with d0 = `$100`), returns if the high byte did not change: never taken with `$100` | gate |
| `$1abc0-$1ac38` | `$57fec++` (season/animation counter), 16 steps of an LCG on `$57ff6`: `d7 = (d7*$24a1 + $24df) & $1fff` (`mulu.w #$24a1` at `$1abe4`); each step copies 16 bits (bit `d7&15`, word `d7>>4`) of the NEXT season's picture (`$ff9e + $1aba2[season]`) into the working picture `$ff9e+$e80` (the terrain texture): the season dissolve. LCG state 0 = end of the dissolve | **world** (state + texture) |
| `$1ac3c-$1ad26` | season change: `$57ff6`=0, `$57fec`=0, `$4bb42/$4bb44` cleared, `$57fd0` += 2 (mod 8), a captain record pick via RNG `$12c9a`, 4 sound calls `$1ba3e` | **world** (RNG, state, sound) |
| `$1ad2a-$1ad52` | `d7 = $4bb42` (rain kind, 0 = none): if set, `jsr $1a856` (d0=`$10` groups, d2=4, d1=`$c2` rows) **draws the rain into the back buffer `$2df7c`+`$3c0`+32**, then `$4bb44--` (ticks left; below 0 the kind goes to 0) | **draw** + world (`$4bb44`) |
| `$1ad54-$1ad9a` | rain start: when `$4bb42 == 0` and `$4bb44 >= 0` and `(($4bb4a + $57fec) & $a0) == $a0`: `$4bb42 = $1ad9c[$57fd0]` (words `2,1,0,0`: season 0 -> kind 2, season 2 -> kind 1, seasons 4/6: none), `$4bb44 = (($4bb4a+$57fec)&$3f)+$20` (32-95 ticks) | world |

`$1a856` is the ONLY caller-visible drawing in `$1abaa` (`m68dis.py --callers 1a856`: one call, `$1ad3a`). It ORs a sparse 32-bit table row into the 4 planes of the buffer: kind 1 (table `$1a8a4`, `or.w d4` on all four plane words = colour 15), kind 2 (table `$1a9c8`, plane words `or, and-not, or, and-not` = colour 5). The table row of scanline r is the byte `$1aac8` minus 4 r (wraps in 256 B = 64 rows), and `$1a856` adds `$40` to `$1aac8` per call, so a frame moves the pattern 16 rows. `$1aac8` is the only state.

**Where do the drop positions come from?** Neither the world RNG nor a visual LCG: a fixed 64-row table scrolled by the byte `$1aac8`. The LCG `#$24a1` in `$1abaa` (`$57ff6`, 16 steps per pass) belongs to the season dissolve, not to the rain; it is world state and is not touched by the fix. (The second `#$24a1` LCG, `$1aacc` on `$4bb4a`, has no caller in the loop: `--callers 1aacc` empty; it fills the map `$418ad`.)

**Live confirmation [obs]** (`python3 tools/pmstagedraw.py get_men 'w $4bb42 $00 $02' 'w $4bb44 $20 $00'`: unpatched game, both screen buffers dumped at consecutive call sites of one pass, neighbours diffed; the 76-90 word differences between other sites are the software pointer, the VBL handler draws it in any stage):
```
$13040 -> $13046 ($127e6 sound queue -> $6522): 0 screen words differ
$13046 -> $1304c ($6522 -> $d322 group scan): 0
$1304c -> $13052 ($d322 group scan -> $3e06 captains): 0
$13052 -> $13058 ($3e06 captains -> after $3e06): 0
$13090 -> $130b0 (VBL wait -> before $1abaa weather): 3316 (the render)
$130b0 -> $130b6 (before $1abaa weather -> after $1abaa): 2855 screen words differ, $1cb80..$242b4     <- the rain
$130b6 -> $130c2 (after $1abaa -> before $14b62 men): 90 (HUD/pointer)
$130c2 -> $130c8 (before $14b62 men -> after $14b62 men): 0
```
(Without the rain poke the `$130b0 -> $130b6` line is 0: get_men has season 4.)

**How to get rain.** `w $4bb42 $00 $02` (rain, colour 5; `$00 $01` = kind 1, white/snow-like, colour 15) and `w $4bb44 $20 $00` (ticks left; it counts down once per world tick, `$2000` = 34 min). The kind is only drawn while `$4bb42 != 0`. Natural start, also tested: `w $57fd0 $00 $00` (season 0), `$4bb42 = 0`, `$4bb44 = 0`: the rain started at tick 160 by itself, `$57fec & $a0 = $a0` (pmrain.py output: `39 160 2 64`, 90 of the 91 frames dumped while the clock was on have rain; the 91st is the frame that was rendered before the tick that switched it on).

**Why 5 of 20 frames.** `tick_wx` returned at once on a render-only pass (RON), so the whole of `$1abaa`, drawing included, ran once per tick (4/s). TT 32 MHz: 20 frames/s, 4 ticks/s -> one frame in five. [obs] TT floppy build with the default set and `tick_wx`, rain forced: **rain on 6 of 31 consecutive frames**; STE 16 MHz get_men: 13 of 25 (every other frame).

## 2. The fix: `tick_rain` (`patches/tick_rain.s`, blob `$b8980`, 82 B, inside tick_head's free `$b8970-$b89ff`)
Same site as `tick_wx` (`jsr $1abaa` -> `jsr $b8980`), so it replaces it: select `tick_rain` instead of `tick_wx` (both together fail pmpatch's site-overlap check). Tick pass: `jmp $1abaa` (the original). Render-only pass: if `$4bb42 != 0`, run just the drawing:
```
        move.b  $1aac8.l,-(a7)          ; world phase
        move.w  D+2.l,d0                ; ACC (tick_head, 1/300 s since the last tick, 0..74)
        mulu.w  #218,d0 ; lsr.l #8,d0   ; ACC*64/75 = 0..63 table units
        andi.w  #$fc,d0                 ; whole scanlines (long reads need an even index)
        subi.w  #$40,d0 ; add.b d0,$1aac8.l   ; $1a856 adds $40 first
        moveq #$10,d0 ; moveq #4,d2 ; move.w #$c2,d1 ; jsr $1a856.l  (d7 = kind)
        move.b  (a7)+,$1aac8.l          ; restore
```
Private visual state: none needed. The drops are a pure function of the byte `$1aac8` (+ kind), so a render-only frame draws them at "the last tick's phase + ACC/TK of the next `$40` step": the fall is smooth at any frame rate and the next tick pass (world phase +`$40`) continues exactly where the last render-only frame ended (a first version with a private phase byte advanced by `$40` per frame repeated one phase at every tick; dropped). The world's `$1aac8` is restored; nothing else is written: `$4bb44`, `$57fec`, `$57ff6` (the weather LCG), the season picture, RNG, sound: bit-identical to the tick-only build (4). Registers: d0-d3/d7/a0 clobbered, as the original call does.

## 3. Evidence: rain on every frame [obs]
`pmrain.py` dumps RAM at every main-loop top (`b pc=$12fd8`), takes the displayed buffer from `$ff8201/03/0d`, decodes the planar picture and the palette register, and tests each frame for rain by recomputing the pattern from the table in RAM: a frame HAS rain iff for one of the 64 row-aligned phases every pixel of the predicted mask (rows 13-165, x >= 80: the 3D window) carries the rain colour. Frames without rain score 0.02-0.09 (random), with rain 1.000. Montages: `work/shots/rain/strip_*.png` (rain = white/grey specks; the crop is the 3D window).

| run | rain on N of M consecutive frames |
|---|---|
| STE 16 MHz get_men snapshot, original game (per-frame world, `--orig`) | 25 of 25 |
| same, `tick_wx` | **13 of 25** (alternate frames) |
| same, `tick_rain` | **24 of 24** (`strip_get_men_16_tick_rain.png`; the pattern phase d3 per frame: 192 (T), 224/232/236 (R), 0 (next T), ... monotonic) |
| **TT** (TOS 3.06, 4 MB, 32 MHz, cold boot of the floppy build with the default set + triple buffering: buffers `$1c700/$24400/$70000`), `tick_wx` | **6 of 31** (`tt_wx/`) |
| TT, `tick_rain` | **34 of 34** (`tt/`, `strip_cold_tt_powermonger.png`: 27 of 27 in the first run) |
| STE, TOS 1.62, 1 MB, cold boot, 8 MHz | 20 of 20 (`ste/`; at 8 MHz nearly every pass is a tick pass) |
| STE, 16 MHz | 25 of 25 (`ste16/`) |
| plain ST, TOS 1.04, 1 MB, cold boot, 8 MHz | 21 of 21 (`st/`) |
| plain ST, 16 MHz | 25 of 25 (`st16/`) |

All cold boots: `pmpatch.py build --only <default set with tick_wx -> tick_rain> --floppy`, `boot_to_game`, rain forced by `w $4bb42/$4bb44` at a flip, then the dump; the 37-patch default set at the time (p3b_*, p4_*, p6_*, p7_triple_*, qol_*, snd_*, tt_ptr...). The ST and STE runs measured `h.fps(1000)` with rain on: STE 8 MHz 4.1 fps, 16 MHz 8.75; ST 8 MHz 3.3, 16 MHz 7.8; TT 15.55.

## 4. State equality (pmtick, whole RAM `$0-$60000`) [obs]
`PM_WX=tick_rain python3 tools/pmtick.py ab SNAP 16 950 --poke ...` (poke applied to BOTH the unpatched and the patched run at the first flip); loop tops of the patched run with R passes included are compared with the unpatched game's frame of the same world tick:
```
get_men  16 MHz, rain kind 2, 8192 ticks left:       124 loop tops over 70 ticks IDENTICAL, negative control 126/126, RNG differs 0, displayed frame of the tick 70 of 70 byte-identical
get_men  16 MHz, season 0, no rain, natural start:   122 loop tops over 69 ticks IDENTICAL, RNG differs 0, frame 69 of 69   (rain starts at tick 160, 1 RNG draw / `$57ff6` steps included)
battle_320 16 MHz, snow kind 1, 12 ticks left (expires inside the run): 141 loop tops over 69 ticks IDENTICAL, RNG differs 0, frame 69 of 69
```
`$1aac8`, `$4bb42`, `$4bb44`, `$57fec`, `$57ff6`, the season picture and the RNG are inside the compared range and equal at every tick. One mask added (only when `PM_WX=tick_rain`): `$1c550-$1c59e`, the tail of the pointer's save-under buffer (`$1c49e`, 16 rows x 16 B, `$1390`): it holds the SCREEN pixels under the arrow, i.e. rain pixels, which render-only frames now have (first run: DIFF only in `$1c550-$1c59c`, nothing else); the first half `$1c480-$1c550` was masked already.

## 5. Gate: `pmab` tick passes vs the current defaults [obs]
`pmab.py --swap tick_wx tick_rain --tonly --base-poke 4bb42:0002 --base-poke 4bb44:2000` (base = tick_wx set, patched = tick_rain, rain on in both, everything compared byte for byte except render-only frames, which differ by design):
```
get_men @16 MHz: IDENTICAL (back frames matched 55, shown+pointer matched 2, R frames differing (allowed) 40, flips 105 -> 98)
battle_320 @16 MHz: IDENTICAL (55 back frames matched, R frames differing 43)
map_idle @8 MHz (kind 1): IDENTICAL (20, R 0)      map_idle @16 MHz (kind 1): IDENTICAL (47, R 9)
no rain (control, no --tonly: R frames too): get_men @16 MHz IDENTICAL, back 80 / shown 79 matched, 'consecutive same-tick R frames identical 5/5', work/pass 1830489 -> 1830478 (-11 cycles)
with p3b_delta + p3b_interp in both: IDENTICAL for get_men and battle_320 only with the predict-ahead forced off for T frames (--base-poke b8a80:0001).
```
Without that poke `get_men` shows `BACK DIFFER key (tick 216, T) ... rows 93-114, 16-px columns 10-13` (men sprites, reproducible, not the rain area): `p3b_interp` draws the people on a TICK pass at `(ACC + 75) * 256/75` (its notes), ACC depends on the timing of the previous passes, and the rain draw changes the R pass time. The same pair without rain is IDENTICAL (`get_men @16 MHz: IDENTICAL, back 55`, the no-rain control with p3b). One non-reproducible mismatch of `map_idle --mhz 8 16` (rain area differed) did not recur in two repeats; [INFERENCE] the cpuclock-switch start instant (pmab's NOTE: the two runs may start one tick apart, and `$1aac8` only moves while the rain is on).

## 6. Cost of the rain drawing [obs] (`tools/pmraincost.py`, pmab's cycle windows: CPU cycles from after the VBL wait to the flip entry; get_men, 16 MHz, same instant in both runs)
```
kind 2 (rain): base T 2 102 323 (tick_wx, rain drawn on T), R 1 791 560 (no rain) | tick_rain T 2 105 685 (+0.16 %), R 2 039 215  -> +247 655 cycles per rendered R pass (+13.8 %)
kind 1 (snow): base T 2 086 939, R 1 791 656 | tick_rain T 2 089 613, R 2 021 240 -> +229 584 cycles per R pass (+12.8 %)
no rain:       R 1 789 734 -> 1 789 766 (+32 cycles: the `tst.w`/`move.w $4bb42` test)
```
The rain costs the same on a tick pass in the original (T 2 102 323 vs 1 853 785 without rain: +248 538). Frame rate: get_men 16 MHz 7.65 -> 7.15 fps (pmab, -6.5 %); **TT 32 MHz cold boot, rain on: 17.9 -> 15.55 flips/s (`h.fps(1000)`: 2.79 -> 3.22 VBL per frame)**. The 68000 draws 194 rows x 16 groups x 4 RMW words; no change was made to it. [INFERENCE] an exact speed-up: skip zero pattern words (`or 0` and `and $ffff` are no-ops): 57 of 128 table words are non-zero for kind 2 (45 %), 97 of 128 for kind 1 (76 %): about -30 % of the rain time for rain, -8 % for snow; not built.

## 7. Other visual effects in the skipped world routines (task 4)
The skipped set on a render-only pass is `$127e6 $6522 $d322 $3e06` (head of the pass), `$1abaa` and `$14b62`, plus the counters `$2df70`/`$4bb3e`. `pmstagedraw.py` (section 1 output): the screen buffers change in none of them except `$1abaa`'s rain. Static check: writers through `$2df7c` are the render/HUD/UI/sprite code, the loop's flip and `$1a858` (the rain); nothing inside `$3e06-$4xxx`, `$6522`, `$d322`, `$127e6`, `$14b62-$15xxx`.
| effect | where | flickers? |
|---|---|---|
| rain / snow (kind 2 / kind 1) | `$1a856` from `$1abaa` | **was: yes (1 frame per tick). Fixed.** Snow is the same code path (kind 1) and is fixed by the same patch |
| lightning | no such code: no other caller of `$1a856`, no second drawing in `$1abaa` | n/a |
| season dissolve | `$1abc0` writes the texture `$ff9e+$e80` (16 px per step, 16 steps' worth per tick); the renderer draws that texture on every pass | no: the texture is persistent state, it just advances at 4 Hz (as the original on an 8 MHz machine: 4 passes/s). Left as is |
| angels, men, smoke | not drawn by the skipped routines: the renderer (`$f898` -> `$115e0`, `$11xxx`) draws them from the people table `$51b66` each pass; `$14b62` only moves them (p3b_interp interpolates the walkers) | no |
| animation frames | the renderer reads the world counters `$57fec` (`$116f8 &$f`, `$117ca &3`, `$11ad8 &2`, `$11b1a &1`, `$159de`, `$55e2`) and `$4bb3e` (`$f95e`: water phase `& 3`): sprite animation frame and water shimmer change once per tick | no flicker; they animate at 4 Hz, the original's 8 MHz pace. Not changed |
| sound | `$127e6`, `$1ba3e` calls in the season change: audio, not video | n/a |

## 8. Files / integration
* `patches/tick_rain.s` (new, `; default: no`). To make the fix default: set `tick_wx` to `; default: no` and `tick_rain` to `; default: yes` (one site, `pmpatch.py` refuses both). `tick_head`, `tick_pass`, `tick_men`, `tick_click*` unchanged; `$b8980-$b89d1` is the only RAM added (`tick_` range, free tail of `tick_men`'s page).
* Gate tools: `tools/pmrain.py strip|cold`, `tools/pmstagedraw.py`, `pmab.py --swap`, `PM_WX` in `pmtick.py` (`NAMES`, one extra `MASKS` entry when `PM_WX=tick_rain`). Screenshots/strips in `work/shots/rain/`.
* Not run: real hardware; Falcon; the HD build (the floppy build was booted on every machine); a rain period of 60+ ticks WITH the p3b predict-ahead active (its T-frame offset depends on timing by design; state equality `pmtick` runs only the tick_* set).
