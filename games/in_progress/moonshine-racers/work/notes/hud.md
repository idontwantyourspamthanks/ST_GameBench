# Moonshine Racers: what the HUD costs (measurement and analysis only, nothing patched)

Machine for every number: Hatari 2.6.1, STE, TOS 1.62, 1 MB, 8.02 MHz, 50 Hz, snapshots `work/snapshots/ste1m_*.sav`, **stock game** unless a row says "shipped set"
(= `mr_edge + mr_map + mr_digit`, live-applied with the private tool `work/render/msrpatch_priv.py`). 160,256 cycles = 1 VBL.
"Pass" = one trip round the main loop, `$796a` to the flip entry `$d1ca` (interrupts included, idle wait excluded, as in `render_patches.md`).
Evidence tags: every number is from a tool run kept in `work/hud/res/` (raw: `numbers.txt`, `*.json`, `skiprun_*.log`); disassembly lines are from `work/hud/dis/` (made by
`tools/m68dis.py` on `work/dumps/ram_race_start.bin`); anything not measured or not read from code is marked **[INFERENCE]**.
Lab: `work/hud/hudlab.py` (per-pass stage cycles with a breakpoint chain, per-pass state dump, pokes, buffer captures, a poison-film that finds the bytes each call writes),
`skiprun.py` / `liverun.py` / `cum.py` (call-skip batches), `analyze.py`, `report.py`, `mktables.py`, `boxes.py`, `monitor*.py`, `flow.py`, `runAB.py`.
Scenes: `race_start` (driving, `$6105=1`; passes 63..216 used: **no speech** = passes 0x5c-0x80, **speech active** = 0x83-0xb7 and the typing/hold classes below),
`race_grid` (standing, in the time-out state `$1226=5`: AI cars keep passing and the car comments on it, so speech is active in 78 % of its passes), mid-race `race_up/race_drive` for variable reading only.

## 0. Answer in one page

1. **The HUD stage (13 calls inside `$ef7a`, clouds excluded) costs 17.9 % of a driving pass (151.6 k of 846 k cycles) with no speech, 19.4 % with a message being typed (169.8 k of 875 k);
   standing 13.6 % / 15.7 %.** Clouds (`de1c+de6c`, not HUD) are another 80.8 k = 9.5 %. Removing every HUD call (measured by nopping the 13 `bsr/jsr`s in a snapshot and re-measuring the same passes):
   **-148.4 k = 17.6 % (no speech), -168.8 k = 19.3 % (speech) driving; -108.8 k = 14.2 % / -118.1 k = 15.3 % standing.** On top of the shipped `mr_*` set the same removal saves 111.4 k = 14.8 % / 130.3 k = 16.6 %.
2. **Minimap (`f214` box fill + `f22c`): 63.4 k = 7.5 % per pass, every pass, driving or standing** (stock: `f22c` 54.4 k + `f214` 9.1 k; standing 50.0 k + 8.6 k; with `mr_map` shipped 39.4 k). It reads only `$5ff8` and its own four variables; skipping it is clean (§5.1).
3. **Speech = `11ef0` (typing) + `f90c` (face): 19.7 k per pass while a line is typed, 12.7 k while it is held, plus 2 x 35 k once per message to erase the box. Over one scripted 1,707-pass race (up held, no steering) a message was active in 76 % of the passes = 14.4 k/pass average = 1.7 %.**
   **`11ef0` must NOT be skipped: the race-end/time-out state machine waits on its state (`$11ab`, `$11b1`); measured: with it skipped the game never leaves the time-out state (soft-lock, §5.2).** The face `f90c` and the text *drawing* are removable.
4. **The cup at the bottom left is the TURBO FUEL gauge** (`$10c0`, 0..28 = `$1c`). Proven by writing the SPACE key flag `$6037=$ff`: with a turbo unit (`$176ae`!=0) the level falls 1 per 8 passes and the car's speed rises from `$5c` to `$80` (hi word of `$10d8`); without a unit the game posts "We must get a turbo!". The routine `f620` only reads it (and plays the slosh sound when you are hit); skipping it changes **no** game state (0 differing bytes in 135 passes). Cost 10.5 k per pass (1.2 %), every pass (the road repaint erases it each pass).
5. **Thermometer = engine temperature/damage (`$10ba`, 0..35)**: costs 152 cycles idle, 11.6-16.4 k per redraw (two redraws per change); the sprite is only redrawn when the value changes. **Dial = race clock** (`$10ce` long, hi byte = hand angle; 255 = time-out), 9.9 k **every pass while driving** (redraw test compares the whole long, which changes every pass, though the hand moves once per 6.6 passes). **Number under the dial = race position** (`$10ca`, 1..99), 0.2 k idle, 5.5 k per change. **Score `f3b6`** = distance score `$11c2` x 10: 36.4 k per pass (17.9 k with `mr_digit`).
6. **Speedometer `f7f0` 19.3 k + gear lever `f76a` 11.3 k + cup `f620` 10.5 k = 41 k per pass (4.9 %) are drawn every pass because the road repaint (rows 120-199) wipes them; skipping them is the cleanest removal there is: the road simply shows through (pixel diff = exactly the element box).**
7. Everything HUD-only that I skipped (all but `11ef0`) leaves the per-pass game state **identical outside HUD-owned bytes** (object slots, road tables, RNG `$dae6`, `$5ff8`, `$1000-$13ff` compared over 133-177 common passes; the only differing bytes are the element's own cache/flag/scratch bytes and the face RNG `$dafe`, §4.2).

Biggest levers per visual loss (§6): minimap 63.4 k, the three bottom items 41 k, score digits 18-36 k (no visual loss if only changed glyphs are redrawn), speech face 12.3 k per active pass, dial 9.9 k (no visual loss: redraw only when the hand byte changes, ~ -7 k).

**Gate bug found on the way (already reported to Main):** Hatari's `m addr count` takes a DECIMAL count; `tools/msrabtest.py` wrote hex digits, so its STATE gate only ever compared `$1000-$118f` and `$dae6`. Fixed by Main; my lab uses decimal counts and compares `$1000-$13ff`, `$29c8-$34ff`, `$4500-$4fff`, `$dae6`, `$dafc-$db03`, `$5ff8`.

## 0b. Master table (the table the task asked for, one per scene)

Master table per scene (stock game; cycles per pass, class means; the ticker's two 34.9 k erase passes per message are not in these means)


**race_start (driving)** (pass work: none 846,003 (n=38), typing 874,742 (n=54))

| element | routine | cycles/pass none (% of pass) | cycles/pass typing (% of pass) | redraw rule | bytes written | safe to skip? |
|---|---|---:|---:|---|---:|---|
| thermometer | `efc6` | 152 (0.0 %) | 1,089 (0.1 %) | on change of `$10ba`, 2 redraws per change | 752 | yes (clear 0,18-31,64 once) |
| engine-fire puff | `f1c0`+`f134` | 288 (0.0 %) | 377 (0.0 %) | only while `$10ba>=35` | 52 | yes |
| minimap box fill | `f214` | 9,068 (1.1 %) | 8,771 (1.0 %) | every pass | 1,152 | yes (clear once) |
| minimap | `f22c` | 54,366 (6.4 %) | 53,946 (6.2 %) | every pass | 568 | yes (clear once) |
| score | `f3b6` | 36,362 (4.3 %) | 35,475 (4.1 %) | when `$11c2` changes (every pass while driving), 2x | 336 | yes (clear once) |
| position no. | `f430` | 171 (0.0 %) | 364 (0.0 %) | when `$10ca` changes, 2x | 224 | yes |
| stopwatch dial | `f53c` | 9,859 (1.2 %) | 9,806 (1.1 %) | whole-long compare: every pass while the clock runs | 496 | yes (clear once) |
| message ticker | `11ef0` | 84 (0.0 %) | 7,437 (0.9 %) | 1 glyph/pass while typing (+1 repeat), 2 x box erase at the end | 40-48 per glyph; 4,704 erase | **NO** (race-end state machine); drawing only |
| talking face | `f90c` | 96 (0.0 %) | 12,279 (1.4 %) | every pass while a message is active | 768 | yes |
| turbo-fuel cup | `f620` | 10,450 (1.2 %) | 10,278 (1.2 %) | every pass (road erases it) | 328 | yes, clean |
| gear lever | `f76a` | 11,335 (1.3 %) | 11,076 (1.3 %) | every pass (road erases it) | 172 | yes, clean |
| speedometer | `f7f0` | 19,332 (2.3 %) | 18,943 (2.2 %) | every pass (road erases it) | 588 | yes, clean |
| **HUD total** | 13 calls | **151,563 (17.9 %)** | **169,840 (19.4 %)** | | | |

**race_grid (standing, time-out state)** (pass work: none 761,422 (n=34), typing 777,565 (n=90))

| element | routine | cycles/pass none (% of pass) | cycles/pass typing (% of pass) | redraw rule | bytes written | safe to skip? |
|---|---|---:|---:|---|---:|---|
| thermometer | `efc6` | 172 (0.0 %) | 172 (0.0 %) | on change of `$10ba`, 2 redraws per change | 752 | yes (clear 0,18-31,64 once) |
| engine-fire puff | `f1c0`+`f134` | 276 (0.0 %) | 328 (0.0 %) | only while `$10ba>=35` | 52 | yes |
| minimap box fill | `f214` | 8,571 (1.1 %) | 8,495 (1.1 %) | every pass | 1,152 | yes (clear once) |
| minimap | `f22c` | 49,961 (6.6 %) | 49,162 (6.3 %) | every pass | 568 | yes (clear once) |
| score | `f3b6` | 128 (0.0 %) | 128 (0.0 %) | when `$11c2` changes (every pass while driving), 2x | 336 | yes (clear once) |
| position no. | `f430` | 941 (0.1 %) | 445 (0.1 %) | when `$10ca` changes, 2x | 224 | yes |
| stopwatch dial | `f53c` | 168 (0.0 %) | 168 (0.0 %) | whole-long compare: every pass while the clock runs | 496 | yes (clear once) |
| message ticker | `11ef0` | 84 (0.0 %) | 7,123 (0.9 %) | 1 glyph/pass while typing (+1 repeat), 2 x box erase at the end | 40-48 per glyph; 4,704 erase | **NO** (race-end state machine); drawing only |
| talking face | `f90c` | 96 (0.0 %) | 12,107 (1.6 %) | every pass while a message is active | 768 | yes |
| turbo-fuel cup | `f620` | 10,243 (1.3 %) | 11,149 (1.4 %) | every pass (road erases it) | 328 | yes, clean |
| gear lever | `f76a` | 11,250 (1.5 %) | 13,170 (1.7 %) | every pass (road erases it) | 172 | yes, clean |
| speedometer | `f7f0` | 21,555 (2.8 %) | 19,629 (2.5 %) | every pass (road erases it) | 588 | yes, clean |
| **HUD total** | 13 calls | **103,446 (13.6 %)** | **122,075 (15.7 %)** | | | |

## 1. Where each element sits (identification evidence)

Boxes below are the bytes each call really **writes** (poison film: both buffers are filled with `$00` (run 1) and `$ff` (run 2) before the call, the union of changed bytes after it is the footprint; `work/hud/res/footprint_B.json`, `_C.json`), shown on a Hatari screenshot of the speech state
(`work/hud/shots/hud_boxed_speech.png`, driving: `hud_boxed_driving.png`; raw screenshots `raw_*.png`). Pixel coordinates are ST pixels, 16-pixel-group granular in x.

| # | element (what the user sees) | call (site) | footprint px x0,y0-x1,y1 | bytes written per redraw | reads (state) | writer of that state | evidence it is what I say |
|---|---|---|---|---:|---|---|---|
| 1 | **thermometer** (red bulb, far left) | `efc6` (`ef88`) -> `f072` | 0,18-31,64 (+ puff 0,9-31,17 by `f134`) | 752 (+52) | `$10ba` clamped 0..`$23` (`efd4..efe2`) | collisions `add.w d3,$10ba` `018a9c 018b68 018d04 018d66 018df4 018e92`; cools `subq.w #1,$10ba` every 8th pass `01158e..01159e`; >=`$1c` posts "The engine's on fire Billy Joe!" (`0114c0`), `$23` starts the fire countdown `$29ac` -> explosion `$1226=1` (`011522..0115a4`) | screenshot (bulb at x 0-31); `$10ba` stays 0 until a crash, falls by 1 every 8 passes (`work/hud/res/stock_start.json`); sprite ids 0/1/2 (`f074 f0e6 f00c`) = tube/mercury/broken tube **[INFERENCE: names from use, bitmaps not rendered]** |
| 2 | **minimap** (box, track outline, dot) | `f214` (`ef8c`) box fill + `f22c` (`efbc`) | fill 32,16-79,63; all 16,15-95,64 | 1,152 + 568 | `$5ff8` world position, `$57890` step script, `$57ad0` map bitmap, own `$10dc $10de $10e0 $10e2` (`f278..f2fa`) | `$10dc..$10e2` written only by `f22c` and initialised at `ee1c..ee28`; `$5ff8` by the main loop | `f22c` draws 4 frame lines (`127fa`), the map bitmap (`12690`) and a 5-pixel cross (`12724`) = dot; screenshot |
| 3 | **dial** (round clock) | `f53c` (`ef9c`) | 80,16-111,46 | 496 | `$10ce` long, clamped `0..$ff0000` (`f540..f554`); hand angle `$80 - hi byte` through sine table `$18fbe` (`f5ea..f618`) | `add.l $10d2,$10ce` once per pass `0117a0..0117ac`; `hi>=$ff` -> `$1226=5` time-out `0117b8..0117be` | `$10ce` rises `$2798` per pass (`vars` log) = 255 in 1,649 passes; at the time-out state (`race_grid`) the hand is at 12 o'clock (`$ff31b0`); this is the **race clock** (the user's "timer") |
| 4 | **number under the dial** | `f430` (`ef98`) -> `f496` | 80,49-111,62 | 224 | `$10ca` clamped 1..99 (`f434..f444`), digits via sprite table | `$10ca` +-1 when an AI car (`$2ca0` x4) passes / is passed `011870..011890`; init 6/7/8 `ee2e..ee44` | `race_grid` shows **82** with `$10ca=$52`; `race_start` shows **6** with `$10ca=6` => **race position** |
| 5 | **score** ("1900", top) | `f3b6` (`ef94`) -> `f3de` -> `11d42` | 32,1-79,14 | 336 | `$11c2` x 10 (`f3b6..f410`: 5 digits + `'0'`) | `add.w d0,$11c2` (d0 = speed/8) every pass `007ba6..007ba8`; +100 per fuel jug `018f06`; end-of-race bonus count `fa98..faa6` | race_start screenshot "1900" = `$11c2=$be` at pass 0x6c (`vars` log) |
| 6 | **message text** (typed in the sky) | `11ef0` (`efa0`) -> `120a4` -> `14fd4` | 112,16-271,64 (text 112,24-255,47; one glyph 8x8) | 40-48 per glyph, 4,704 per box erase | `$11ab $11ac $11ad $11ae $11af $11b0 $11b1 $11b2 $119e $11a2` (`011ef0..012266`) | posted by `11eba` (23 call sites, §5.2) | screenshot: 4-line text from x=112,y=24 |
| 7 | **talking face** (oval portrait, top right) | `f90c` (`efa6`) -> `f9ce` | 272,17-303,64 | 768 | `$10f8 $10f9 $10ec-$10f7 $10fa..` face sequence, RNG `$dafe` (`dafc`) | face id from the message post (`011eea`, `011f3a`) | screenshot |
| 8 | **cup = turbo fuel tank** | `f620` (`efaa`) -> `f662`, `f6f8` | 0,172-31,199 | 328 | `$10c0` clamped 0..`$1c` (`f620..f62e`), `$11ce $11cf` hit flags | `$10c0=$1c` at start `00eeae`, `subq.w #1,$10c0` every 8th pass while SPACE (`$6037`) is held `010e58`, +7 fuel & +100 score per jug `018ef2..018f06`, end-of-race bonus `faae..fad6` | §5.5 |
| 9 | **gear lever** (small box under the speedo) | `f76a` (`efae`) | 272,180-303,194 | 172 | `$11d9` (gear), animation `$11dc` 0..3 (`f76a..f7ee`: sprite 17+`$11dc`) | `not.b $11d9` on FIRE with sound `$3f` `010dc8..010dd6` | `$11d9` selects the speed curve `010d22..010d70` (gear 0: `$10aec/$10ae6/$10b02`, gear 1: `$10afc/$10af6/$10b06`) |
| 10 | **speedometer** (dial with needle, bottom right) | `f7f0` (`efb2`) | 256,151-319,174 | 588 | `$10d8` hi word (`f7f4`), needle `$90 - v/8` through the sine table, two lines (`f8bc`, `f8ca`) | speed long `$10d8` computed by the physics `010d8c` (`d1 -> $10d8`), `$130c = hi/9` | screenshot |
| 11 | engine-fire puff over the thermometer | `f1c0` (`ef84`) erase + `f134` (`efc0`) | 0,9-31,17 | 52 | `$10ba >= $23` and `$1226==0` (`f134..f146`) | as 1 | only visible at 35 = overheat (forced test: 52 bytes written) |

![boxed speech](shots/hud_boxed_speech.png) ![boxed driving](shots/hud_boxed_driving.png)

Other things that happen inside the HUD routines (not display): `f620` calls the sound trigger `$7bb2` with `$36` when `$11ce` (set by a hard hit, `018aa6 018b72 018d0e`) is pending (`f640..f652`); `11ef0` calls `$7bb2` with `$ff,$ff` when a message with face 7 or 8 starts (`011f0c..011f28`).
Every sprite kernel writes the scratch word `$100c` (`move.w d2,$100c.l`); it is consumed only by the same routine's next kernel call (`f19c`, `f062`, ...), never by game logic (no state difference in any skip run).
The HUD sprites also write a 1-bit occupancy map at `$6f000` (the `$3a70` kernels `1231e/1233a`: `not(and of the 4 plane words)`; readers: the cloud passes `de36`, `de74`) so that clouds are not drawn over HUD pixels; with clouds gone those writes
(`f53c.mask` 3.5 k, face 5.3 k, per score glyph the `1235e` copy) are dead work **[INFERENCE for the exact total: measured only for dial and face]**.

## 2. Cost per call per pass, per scene (stock game, cycles; % = of that class's mean pass work)

Method: `hudlab.run` (`work/hud/hudlab.py`): one-shot breakpoint chain on the return address of each call of `$ef7a` (`ef84 ... efc4`), `e VBL`/`e FrameCycles` per stop, wrap offset fitted (0 violations),
state dumped at `$7b86` every pass (`m $1000 1024` ...). A stage = cycles from the previous stop to this return, **interrupts (timer B, VBL, YM) included**. Classes by the state `$11ab` at the end of the pass:
`none` (no message), `typing` (`$11ab=1`), `hold` (`$11ab>=2`), `erase` (the 2 passes that wipe the message box, `11ef0` > 20 k). Raw per-pass data: `work/hud/res/skip_race_start_stock.json`, `skip_race_grid_stock.json`; table text `work/hud/res/tables_stage.md`.
Costs agree with the earlier stage study (`rendering.md` §5) once the labels are shifted: the labels there were guessed from pixel positions: `f214` (8.5 k, "thermometer?") is the minimap box fill, `f53c` ("digits") is the dial, `efc6` is the thermometer; `f3b6` (34 k) is the score, `f620` the cup, `f76a` the gear lever, `f7f0` the speedometer.


### race_start (driving)
| call | element | none (n=38) cyc / % | typing (n=54) cyc / % | hold (n=40) cyc / % | erase (n=3) cyc / % |
|---|---|---:|---:|---:|---:|
| `f1c0` | overheat puff erase | 184 / 0.0% | 273 / 0.0% | 184 / 0.0% | 184 / 0.0% |
| `efc6` | thermometer | 152 / 0.0% | 1,089 / 0.1% | 733 / 0.1% | 152 / 0.0% |
| `f214` | minimap box fill | 9,068 / 1.1% | 8,771 / 1.0% | 9,504 / 1.1% | 8,292 / 0.9% |
| `f22c` | minimap | 54,366 / 6.4% | 53,946 / 6.2% | 54,086 / 6.5% | 53,625 / 6.1% |
| `f3b6` | score | 36,362 / 4.3% | 35,475 / 4.1% | 30,456 / 3.6% | 36,597 / 4.2% |
| `f430` | position no. | 171 / 0.0% | 364 / 0.0% | 165 / 0.0% | 144 / 0.0% |
| `f53c` | stopwatch dial | 9,859 / 1.2% | 9,806 / 1.1% | 10,192 / 1.2% | 10,003 / 1.1% |
| `11ef0` | message ticker | 84 / 0.0% | 7,437 / 0.9% | 376 / 0.0% | 34,919 / 4.0% |
| `f90c` | talking face | 96 / 0.0% | 12,279 / 1.4% | 12,344 / 1.5% | 96 / 0.0% |
| `f620` | turbo-fuel tank | 10,450 / 1.2% | 10,278 / 1.2% | 10,526 / 1.3% | 10,215 / 1.2% |
| `f76a` | gear lever | 11,335 / 1.3% | 11,076 / 1.3% | 11,436 / 1.4% | 10,689 / 1.2% |
| `f7f0` | speedometer | 19,332 / 2.3% | 18,943 / 2.2% | 19,497 / 2.3% | 18,444 / 2.1% |
| `f134` | overheat puff | 104 / 0.0% | 104 / 0.0% | 104 / 0.0% | 104 / 0.0% |
| HUD total (13 calls) | | 151,563 / 17.9% | 169,840 / 19.4% | 159,602 / 19.1% | 183,464 / 21.0% |
| clouds `de1c`+`de6c` | | 80,783 / 9.5% | 84,737 / 9.7% | 79,051 / 9.4% | 84,333 / 9.6% |
| pass work (loop top to flip) | | 846,003 | 874,742 | 837,271 | 875,487 |

### race_grid (standing, time-out state)
| call | element | none (n=34) cyc / % | typing (n=90) cyc / % | hold (n=50) cyc / % | erase (n=6) cyc / % |
|---|---|---:|---:|---:|---:|
| `f1c0` | overheat puff erase | 184 / 0.0% | 236 / 0.0% | 184 / 0.0% | 184 / 0.0% |
| `efc6` | thermometer | 172 / 0.0% | 172 / 0.0% | 172 / 0.0% | 172 / 0.0% |
| `f214` | minimap box fill | 8,571 / 1.1% | 8,495 / 1.1% | 8,292 / 1.1% | 8,292 / 1.1% |
| `f22c` | minimap | 49,961 / 6.6% | 49,162 / 6.3% | 49,360 / 6.5% | 49,817 / 6.3% |
| `f3b6` | score | 128 / 0.0% | 128 / 0.0% | 128 / 0.0% | 128 / 0.0% |
| `f430` | position no. | 941 / 0.1% | 445 / 0.1% | 144 / 0.0% | 144 / 0.0% |
| `f53c` | stopwatch dial | 168 / 0.0% | 168 / 0.0% | 168 / 0.0% | 168 / 0.0% |
| `11ef0` | message ticker | 84 / 0.0% | 7,123 / 0.9% | 386 / 0.1% | 35,251 / 4.5% |
| `f90c` | talking face | 96 / 0.0% | 12,107 / 1.6% | 11,284 / 1.5% | 96 / 0.0% |
| `f620` | turbo-fuel tank | 10,243 / 1.3% | 11,149 / 1.4% | 9,716 / 1.3% | 11,703 / 1.5% |
| `f76a` | gear lever | 11,250 / 1.5% | 13,170 / 1.7% | 10,900 / 1.4% | 12,650 / 1.6% |
| `f7f0` | speedometer | 21,555 / 2.8% | 19,629 / 2.5% | 23,601 / 3.1% | 19,690 / 2.5% |
| `f134` | overheat puff | 92 / 0.0% | 92 / 0.0% | 92 / 0.0% | 92 / 0.0% |
| HUD total (13 calls) | | 103,446 / 13.6% | 122,075 / 15.7% | 114,427 / 15.0% | 138,387 / 17.6% |
| clouds `de1c`+`de6c` | | 80,349 / 10.6% | 79,948 / 10.3% | 80,172 / 10.5% | 79,564 / 10.1% |
| pass work (loop top to flip) | | 761,422 | 777,565 | 760,359 | 787,668 |


Inside the big calls (persistent breakpoints on every internal return, `hudlab.run_sub`, driving no-speech passes 0x6e-0x80, `work/hud/res/sub_start.json`):

| call | part | cycles |
|---|---|---:|
| `f22c` minimap | 4 frame lines `127fa` (the 2 vertical ones 6.5 k + 6.2 k, the 2 horizontal 3.2 k + 2.6 k) | 18,551 |
| | map state + bitmap `12690` (`f278..f34a`; `12690` alone = 30.6 k stock, `render_patches.md`) | 34,196 |
| | 5 dot pixels `12724` | 2,102 |
| `f53c` dial | sprite 32x31 (`jsr (a2)` at `f5ba`) | 4,684 |
| | occupancy-mask kernel (`f5dc`) | 3,476 |
| | hand line `127fa` | 1,541 |
| `f7f0` speedometer | sprite 64x24 (`f83c`) | 15,237 |
| | needle lines (two) | 1,776 + 1,486 |
| `f620` tank | `f662` (sprite 8/9 with level clip) | 10,204 |
| `f90c` face (speech passes) | sprite 32x48 | 7,026 |
| | mask + rest | 5,274 |
| `f76a` gear | one sprite call, x = 282 (`f7dc`: `move.w #$11a,d0`), **not 16-pixel aligned** (282 and 15 = 10): shifted kernel path (`13556`), 15 rows | 11,004 |

Bytes touched. Written per redraw = §1 table (poison film). Changed between two presented frames (inside the box, bytes of 4 planes, mean of 7 consecutive frames, `work/hud/res/shots_series`, driving):
no speech: thermometer 13, minimap 89, dial 11, position 2, score 24, face area 31, text area 198 (**mostly clouds drifting through**), cup 61, speedo 47, gear 14; speech typing: minimap 57, dial 8, score 20, face 22, text 150, cup 43, speedo 31, gear 16.
So the HUD rewrites 2-25 times more bytes than change (dial 496 written vs 11 changed, score 336 vs 24, speedo 588 vs 47, minimap 1,720 vs 89).

## 3. Redraw rules (read from code, confirmed by the per-pass costs)

| element | rule (code) | what the data shows |
|---|---|---|
| thermometer `efc6` | `d2=clamp($10ba)`; if `d2 != $10bc` store, `st $11c9`, draw; else if `$11c9` set: clear it, draw again (`efe4..f006`) = **2 redraws per change** (one per buffer) | idle 152 cycles; redraw 11.6 k / 16.4 k; 124 value changes in the 1,707-pass race -> 248 redraws |
| puff `f1c0/f134` | `f134` draws only while `$10ba>=$23` and `$1226==0`; `f1c0` erases it (`$10c2-$10c8`) | 184 + 104 cycles idle |
| minimap `f214`+`f22c` | **unconditional**, every pass (no flag) | 9.1 k + 54.4 k every pass, standing too (50.0 k + 8.6 k) |
| score `f3b6` | `$11c2 != $11c4` -> store, `st $11c7`, redraw; else flag -> redraw once more (`f3c0..f3d6`) | 128 cycles standing; 36.4 k every pass driving (`$11c2` +1 per pass at cruise, +0 below speed 8) |
| position `f430` | `$10ca != $10cc` -> store, `st $11cc`, redraw; flag -> once more (`f446..f458`) | 144 idle, 5.2-5.9 k per redraw; 16 changes in the race |
| dial `f53c` | `cmp.l $10d4.w,d2` on the **whole long** (`f556`), flag `$11cd` twice | the long grows by `$2798` per pass, so it redraws **every** pass while the clock runs (9.9 k), 168 cycles standing/timed-out. The hand uses only the hi byte, which changes once per 6.6 passes |
| ticker `11ef0` | state machine: one character per pass (`$11ad` countdown), glyph drawn into the back buffer, repeated next pass for the other buffer (`$11ae`, `011fd4..011ff4`); hold `$11ac` = 20 passes; then box restore (`12086`) in 2 passes | 84 idle, 3.7-12 k per typing pass (7.4 k mean), 376 in hold, 34.9 k x 2 per message end |
| face `f90c` | whole portrait **every pass while a message is typing or held** (`$11ab != 0`) or new (`$10f8`) | 96 idle, 12.3 k per active pass (11.3-18 k) |
| tank `f620` | **unconditional** sprite every pass (the road repaint erases it); `$11ce` (hit) starts a slosh animation `f6f8` + sound `$36`, only when the tank is >= 15 | 10.2-10.5 k every pass |
| gear `f76a` | unconditional every pass (`f7aa..f7ee`); `$11d9` change starts a 4-frame lever animation (`$11da $11db $11dc`) | 11.0-11.4 k every pass |
| speedo `f7f0` | unconditional every pass | 19.3 k every pass (21.5 k standing: needle in a different place) |

Why the bottom three must redraw every pass: the road span draw `17c42` repaints rows 120-199 across the full width every pass (`rendering.md` §4.2), the three boxes (rows 151-199) lie inside; the top elements are drawn into a persistent background.

## 4. Skipping calls (the experiment)

Method: the call instruction is overwritten by `4e71` nops (`w $ef..` at the first `$7a88` of the snapshot, `hudlab.skip`), the same passes (key `$100e`) of the stock and the skipped run are compared:
**work** = loop top to flip (mean over the common passes of a window), **state** = `$1000-$13ff`, `$29c8-$34ff` (object slots), `$4500-$4fff` (road geometry), `$dae6`, `$dafc-$db03`, `$5ff8` at `$7b86` of every pass,
**pixels** = both screen buffers at fixed passes (0x70, 0xa0; grid 0xe30, 0xe60). Raw: `work/hud/res/numbers.txt`, `skip_*.json`, `shots_*`.
Saving = stock work - skipped work; a +-2 k phase effect is included (when earlier work is removed, later stages meet the timer-B/VBL interrupts at different raster positions: e.g. `f22c` itself costs 1.7-2.1 k less in every skip run that removes an earlier stage).

### 4.1 Savings (cycles per pass, % of the stock pass)

driving `race_start`: no speech = passes 0x5c-0x80 (stock pass 845 k), speech = 0x83-0xb7 (875 k); standing `race_grid`: no speech 40 passes (765 k), speech 140 passes (771 k).

| removed (alone) | driving no speech | driving speech | standing no speech | standing speech | on top of shipped `mr_*` (driving no speech) |
|---|---:|---:|---:|---:|---:|
| minimap `f22c` only (box stays, empty frame) | 54.3 k (6.4 %) | 53.4 k | 49.6 k (6.5 %) | 49.2 k | |
| minimap `f214` only (box fill) | 10.1 k (1.2 %) | 10.9 k | 8.3 k | 8.4 k | |
| **minimap `f22c+f214`** | **63.3 k (7.5 %)** | 63.5 k (7.3 %) | 58.6 k (7.6 %) | 57.8 k | **39.4 k (5.2 %)** (`mr_map`: -20 k) |
| score `f3b6` | 36.5 k (4.3 %) | 34.8 k | 0.1 k | 0.1 k | 17.0 k (2.2 %) (`mr_digit`) |
| dial `f53c` | 11.1 k (1.3 %) | 11.8 k | 0.16 k | 0.16 k | 9.4 k |
| position `f430` | 0.13 k | 0.34 k | (0.1-0.9 k when it changes) | | |
| thermometer `efc6` | 0.14 k | 1.0 k | 0.17 k | 0.17 k | |
| puff `f1c0+f134` | 0.29 k | 0.28 k | | | |
| speech: face `f90c` only | 0.09 k | 12.4 k (1.4 %) | 0.2 k | 11.6 k (1.5 %) | |
| speech: ticker `11ef0` only | **not skippable (soft-lock, §5.2)** | 7.4 k | | | |
| speech: `11ef0+f90c` | 0.16 k | 19.9 k (2.3 %) | 5.9 k | 16.2 k (2.1 %) | 19.0 k (2.4 %) speech |
| cup `f620` | 11.6 k (1.4 %) | 12.5 k | 9.8 k (1.3 %) | 9.9 k | 9.9 k (1.3 %) |
| gear `f76a` | 13.1 k (1.5 %) | 13.4 k | 10.7 k (1.4 %) | 10.7 k | 10.8 k |
| speedometer `f7f0` | 21.5 k (2.5 %) | 21.8 k | 18.8 k (2.5 %) | 18.8 k | 18.7 k |
| gear+speedo | 33.6 k (4.0 %) | 33.2 k | 29.4 k (3.8 %) | 29.4 k | |
| **ALL 13 HUD calls** | **148.4 k (17.6 %)** | **168.8 k (19.3 %)** | **108.8 k (14.2 %)** | **118.1 k (15.3 %)** | **111.4 k (14.8 %)**; speech 130.3 k (16.6 %) |

Sum of the single measurements (driving, no speech) = 157.7 k against 148.4 k measured together: the difference (9 k) is the phase effect above, not an interaction.
Clouds `de1c+de6c` (not counted above) are 80.8 k driving / 80.3 k standing (stage means), see `sprites.md` for why skipping them is not pixel-identical.

Cumulative, driving, removal order chosen by saving per visual loss (§7), pass 845 k no speech / 875 k speech (`cum.py`, `numbers.txt`):

| step | removed so far | saving, no speech | saving, speech |
|---|---|---:|---:|
| 1 | minimap (`f22c f214`) | 63.3 k (7.5 %) | 63.5 k (7.3 %) |
| 2 | + cup | 73.2 k (8.7 %) | 73.1 k (8.4 %) |
| 3 | + gear | 84.8 k (10.0 %) | 85.4 k (9.8 %) |
| 4 | + face (`f90c`) | 84.7 k (10.0 %) | 97.4 k (11.1 %) |
| 5 | + speedometer | 104.0 k (12.3 %) | 116.6 k (13.3 %) |
| 6 | + score | 137.8 k (16.3 %) | 150.0 k (17.2 %) |
| 7 | + dial | 147.8 k (17.5 %) | 159.7 k (18.3 %) |
| 8 | + position, thermometer, puff (everything but the ticker) | 148.3 k (17.6 %) | 161.3 k (18.4 %) |

### 4.2 Is the game state touched? (state gate, common passes 133-177)

| skipped | bytes that differ from stock (all of them HUD-owned) |
|---|---|
| `f22c` (and `+f214`) | `$100c-$100d` (kernel scratch), `$10dd $10df $10e1-$10e3` = the minimap's own `$10dc..$10e2` (written/read only by `f22c`, `ee1c..ee28`) |
| `f214` | none |
| `f3b6` | `$11c4-$11c5` (cached score), `$11c7` (flag) |
| `f430` | `$10cd` (cache), `$11cc` (flag) |
| `f53c` | `$10d5-$10d7` (cached clock long) |
| `efc6` | `$10bd` (cache), `$11c9` (flag) |
| `f1c0+f134`, `f620`, `f76a`, `f7f0` | **none** (0 differing bytes in 135-180 passes) |
| `f90c` | `$10ef $10f1 $10f4-$10f5 $10f8` (face sequence), `$dafe-$db01` (the face's own RNG, `dafc`; read only by the face and by the title screens `db22`) |
| `11ef0` (+`f90c`) | the message machine `$119d $11a4-$11a9 $11ab-$11ac $11ae-$11b2` **and then the game flow stops** (§5.2) |
| ALL 13 | union of the above (39 / 27 bytes); `$dae6` (game RNG), object slots `$29c8-$34ff`, road tables `$4500-$4fff`, `$5ff8`, `$1000-$13ff` outside HUD bytes: identical in every common pass |

Pixels outside the element boxes were identical in all skip runs (`analyze.clusters`: every differing cluster lies inside the element's own box, §4.3), so the sprite kernels' self-modification (`stale-immediate quirk`, `extrap.md`) is not disturbed either.
Sound: skipping `f620` loses the slosh sound `$36` on hard hits; skipping `11ef0` loses the `$ff,$ff` sound at the start of face-7/8 messages. Nothing else in the HUD calls the sound trigger.

### 4.3 What a skip leaves on screen (stale pixels), and what a removal needs

Measured as the pixel difference to the stock frame at the same pass (`work/hud/res/shots_*`, `analyze.clusters`).

| skipped | stale / missing pixels | box (px) | consequence |
|---|---|---|---|
| `f620`, `f76a`, `f7f0` (bottom) | **nothing stale**: the road repaint covers the box on the next pass; the diff vs stock is exactly the element (260/100-145/493 bytes) | 0,172-31,199 / 272,180-303,195 / 256,148-319,175 | **clean removal, no extra work** |
| `f22c` alone | box contents wiped each pass by `f214`, frame lines (x 31 and 80, y 15 and 64, outside the fill) stay | 16,15-95,64 | empty frame |
| `f22c+f214` | **last minimap frozen in both buffers** (last track bitmap + dot + frame) | 16,15-95,64 | a removal must paint the box once per buffer with colour 15 (what `f214` does, 8.3 k once) and the 4 frame lines (or restore from the background) **[INFERENCE: not built]**; the occupancy map `$6f000` of the box is not written by the minimap |
| `f3b6` | last score digits frozen | 32,1-79,14 | clear/redraw once; cache `$11c4` stale: after re-enabling it redraws (value differs) |
| `f430` | last number frozen | 80,49-111,62 | same |
| `f53c` | dial frozen with the hand where it was (22-26 bytes differ after 7-60 passes) | 80,16-111,46 | same; `$10d4` stale |
| `efc6` | thermometer frozen at the last level | 0,18-31,64 | same; `$10bc`/`$11c9` stale |
| `f90c` | face not drawn; **if it was on screen when the skip started it is erased by the end-of-message box restore** (`12086`) | 272,17-303,64 | clean (the text stays) |
| `11ef0` | text and face frozen **forever** and the machine never ends | 112,16-303,64 | not allowed (§5.2) |
| `f1c0+f134` | nothing (only visible at overheat) | 0,9-31,17 | clean |

Redraw-twice flags: none of the skips breaks them. A skipped element's cache and flag bytes are simply left as they were; if the call is enabled again later the cache differs from the value (or the flag is still set) and the element redraws twice, as designed.
The one trap is a removal that clears the area and later re-enables the call while the cache already equals the value: nothing would be redrawn, so a "clear once" must also invalidate the cache (`$10bc`, `$11c4`, `$10cc`, `$10d4`) **[INFERENCE from the compare code, not tested]**.

## 5. The elements one by one

### 5.1 Minimap (user: "really of little value")
Shows: the course outline as a scrolling window of a map bitmap (`$57ad0`, size words at its head) with a 5-pixel cross at the current position; the position advances along a step script (`$57890`: nibble codes 8/4 = x -1/+1, 2/1 = y -1/+1, step length in world units, compared with `$5ff8 - $10e2`, `f2de..f2f6`), so it moves about every 3.4 passes at cruise (`$10e0` 0..14 over 48 passes in the var log). Reads `$5ff8` and its own `$10dc $10de $10e0 $10e2`; nothing else reads them.
Cost: `f214` 9.1 k + `f22c` 54.4 k = 63.4 k per pass driving (7.5 %), 58.6 k standing (it redraws although nothing moved), draw routines `f22c` (`12788` colour select 0.1 k, four frame lines `127fa` 18.6 k, state + bitmap `12690` 34.2 k, five cross pixels `12724` 2.1 k) plus `f214`'s box fill `12392` (1,152 bytes). With `mr_map` shipped: bitmap 30.6 k -> ~11 k, total 39.4 k.
Removing it entirely saves 63.3 k (7.5 %) stock, 39.4 k (5.2 %) with the shipped set; state/pixels §4.2-4.3: **safe** (the call can be nopped; the box needs a one-time clear).
Cheaper but kept (**[INFERENCE]** estimates): (a) the 4 frame lines are static (18.6 k per pass, 2.2 %), they only need redrawing when a cloud overpaints them (de6c runs before `f22c`), once per buffer if clouds go; (b) redraw box + bitmap + cross only when `$10e0/$10dc/$10de` change (every ~3.4 passes, twice for two buffers = 60 % duty): -40 % of 30-40 k.

### 5.2 Speech (`11ef0` text ticker, `f90c` face): triggers, cost, why the ticker cannot be skipped
**What it is.** A message is a record `[x/8, y/8, colour, hold, text...]` (`0e 03 b8 14` = x=112, y=24, colour `$b8`, hold 20 passes, in every message of the game; text up to 4 lines, `$0d` = newline) posted by `11eba(a0 = text, d0 = priority, d1 = face id)` (stored `$119e`, `$11b2`, `$10f9`); higher priority interrupts a running one. 23 call sites:
race start (`fa14`: at pass `$100e == $14`, one of 4 texts via `$fa1c` "Let's go Billy Joe!" ...), collisions (`018ad0`, `018afc`: tables `$1236` "Crazy fool!", "Road hog!", `$1246` "Get out of the way!", "Is that how you lost your licence, Billy?", `$1266` ...), overtaking/passing (`011b1c`, `011b58`),
turbo (`010dfa` "We must get a turbo!" `$6a80`, `010e14` "We need turbo fuel!" `$6a99`, `010e36` `$1256` "Hang on Ike!", "Yeeeeeeee harrrrrh!"), temperature (`0114c6` "Don't set fire to my moonshine boys!", `0114fa` "The engine's on fire Billy Joe!", `01153c` "Do something Ike! And do it quick!"),
time-out (`0117ce` "You're out of time boys! Try again." prio `$ff`), end-of-race commentary (`fb8e..fd98`, 8 sites), explosion states (`0116fc`, `01173a`), and two in the title/intro code (`007452`, `00db3a`). All strings are in `work/hud/res/messages.txt` (every record has x=112, y=24, colour `$b8`, hold 20).
**When active.** Typing: one character per pass (`$11ad`), 30-60 passes per message; then the line is held `$11ac` = 20 passes; then the box (x 112-303, y 16-64) is restored from the background in 2 passes (`12086 -> 1242c`).
In one scripted race of 1,707 passes (up held, no steering; `work/hud/res/monitor_race.json`, `monitor.py`): **22 messages, 933 typing passes + 370 hold passes = 1,303 passes (76 %) with speech**, message lengths 30-83 passes (typing + hold), back to back. Standing in the time-out state (`race_grid`): 140 of 180 passes.
**Cost.** Typing pass: ticker 7.4 k (a new glyph in the back buffer + last pass's glyph repeated for the other buffer, ~3.7 k per glyph draw: `120a4` = `14fd4` (4 planes x `btst/sne/and/or` per row, 8 rows) + the `1237c` mask copy) + face 12.3 k (sprite 7.0 k + mask/rest 5.3 k) = **19.7 k (2.3 % of a pass)**.
Hold pass: ticker 0.4 k + face 12.3 k = **12.7 k (1.5 %)**. Message end: **34.9 k in each of two passes (4.0 % of those passes)**. Over the scripted race: 933 x 19.7 k + 370 x 12.7 k + 22 x 2 x 35 k = 24.6 M cycles = **14.4 k per pass on average = 1.7 %**. Without speech: 84 + 96 cycles.
**Why `11ef0` is not skippable.** Two places in the race logic wait for the ticker: `0117d6: cmpi.b #$ff,$11b1 / tst.b $11ab / st.b $1024` (time-out sequence) and `fa48/fa52` (end-of-race states) only continue when the time-out message (priority `$ff`) is the active one (`$11b1 == $ff`) and has finished typing and holding (`$11ab == 0`, the pass before its box is erased), which only the ticker can bring about.
Measured on `race_start`, whole race, 1,850 passes each (`work/hud/res/monitor2_stock.json`, `monitor2_11ef0.json`):
stock: `$1226=5` (time-out) at pass 1649 (VBL 24836), the counter restarts (new race) at VBL 25369 (533 VBL = ~100 passes later); with `11ef0` skipped: `$1226=5` at pass 1649 (VBL 24802), still `$1226=5`, `$11ab=2`, `$11b1=$7f` (the very first message, never finished) at pass 1916 (VBL 25928, 1,100 VBL later): **the game never restarts: soft-lock.**
(A second test from `race_idle` is in `flow_*.json`: `$11ab` stays 2 with the ticker skipped while stock cycles 0-1-2.) The face `f90c` skipped alone is safe (flow identical to stock, `flow_f90c.json`).
**What a safe "no text / no face" must be.** Keep the state machine of `11ef0` running and only drop its drawing: the glyph draws `120a4` (`jsr $14fd4` + `jmp $1237c`) and the box restore `12086` (the `bsr.w $12086` at `011fc4`), and skip `f90c`. That removes 7.4 k per typing pass + 12.3 k per active pass + the 2 x 35 k erase = 14.4 k/pass average in the scripted race (1.7 %), 19.7 k/pass while typing.
**Cheaper but visible** (all **[INFERENCE]**): glyph kernel like `mr_digit` (one colour, byte ops: 94 cycles/row measured for the 15-row digit kernel -> ~0.75 k per 8-row glyph instead of ~2.6 k) = ticker ~7.4 k -> ~2 k per typing pass; skip the `1237c` mask copy when clouds are gone (-0.4 k per glyph); face: draw it once per message instead of every pass (no mouth animation) = -12.3 k per active pass; erase with longword fills instead of 600 `movem.w` groups: 35 k -> ~12 k per erase pass (but only 0.6 k/pass averaged). Drawing the whole line at once saves nothing (same glyph work, just moved).

### 5.3 Dial (the "timer" right of the minimap)
Routine `f53c` (`ef9c`), 32x31 stopwatch sprite (id 32 at `$1b076 + 14*32`, x=80 y=16) + occupancy-mask update + one hand line from the centre (95,33) of length `sin/16` (about 8 px): sprite 4.7 k + mask 3.5 k + hand 1.5 k + 0.2 k = **9.9 k per pass driving, 0.17 k standing** (nothing changes while stopped). It displays the **race clock** `$10ce` (long: +`$10d2` per pass, `$2798` in the first race: 255 hand steps = 1,649 passes ~ 198 s at 8.3 passes/s), the hand angle is `$80 - hi byte`; at hi = 255 the game declares the time-out (`$1226 = 5`).
Redraw rule: whole-long compare => redrawn every pass (the long changes every pass); the picture only changes when the hi byte changes: once per 6.6 passes. Bytes touched: 496 written per redraw, ~11 changed per pass. Removing: 11.1 k (1.3 %); `$10ce` itself is untouched (logic), so the time limit still works with the dial gone. Needs a clear of 80,16-111,46.
**Halving its size** (a 16x16 sprite and a half-length hand, new art needed): sprite and mask kernels scale with area and rows (aligned 32-px kernel measured 75 cycles per group-row), so about 1/4 of 8.2 k + half of the hand = ~3.1 k, saving ~6.8 k per pass (0.8 %); **[INFERENCE]**. Without any look change: compare only the hand byte (`swap/cmp.b` instead of `cmp.l $10d4` at `f556`) -> redraw 2 of 6.6 passes (two buffers) = ~3.0 k average instead of 9.9 k = **-6.9 k per pass (0.8 %)**, pixel-identical by construction (the draw depends on the hi byte only); both together ~0.9 k average = -9.0 k (1.1 %) **[INFERENCE: redraw frequency from the measured `$2798` per pass]**.

### 5.4 Thermometer, position number, puff
Thermometer: engine temperature `$10ba` (0..35), see §1. Costs 0.15 k per pass idle; each change costs 2 redraws of 11.6-16.4 k (the sprite is a full-height 32x47 draw plus the level clip). 124 value changes in the scripted race (hits, then the 1-per-8-passes cooling) = 248 redraws x ~13 k = 3.2 M cycles = ~1.9 k per pass average (0.2 %). Removal saves 0.14 k idle / ~1.9 k average; the only information of this gauge (how close the engine is to the fire at 28/35) is also given by the speech ("The engine's on fire").
Position number: race rank; 0.2 k idle, 5.2-5.9 k per redraw (2 per change, 16 changes in the race) ~ 0.1 k average. Not worth removing.

### 5.5 Cup (bottom left) = TURBO FUEL gauge
Identified by code and by experiment:
* `f620` reads `$10c0` (0..`$1c`) only (`f620..f62e`); the HUD writes just `$11ce/$11cf` (slosh flags) and triggers sound `$36`.
* Writers of `$10c0` (`work/hud/dis/all_7000_19000.txt`): init `$1c` (`00eeae`); **`subq.w #1,$10c0` every 8th pass (`010e52..010e58`) in the SPACE-held turbo path**; **+7 (cap `$1c`) and +100 score in the reaction handler for object type 6** (`018eee..018f06`, entry 6 of the collision-reaction table `$18cbc`; that type is presumably a fuel can **[INFERENCE: not triggered in my runs]**); the end-of-race routine converts the remaining fuel into cash `$17514` (`faae..fad6`).
* The SPACE key: IKBD handler `cfb4` -> `jmp $264` -> `bclr #7,d0; jmp $cffc` = `seq.b ($5ffe + scancode)`; scancode `$39` = `$6037`. `010de0: tst.b $6037` gates the turbo path.
* Experiment (`work/hud/runAB.py`, `res/turbo_*.json`, `baseline.json`, pass 0x6e, driving): baseline: `$10c0=$1c`, speed `$10d8` saturates at `$5cffff`, no message. **`$6037=$ff` only** (no turbo unit, `$176ae = 0`): the game posts message `$76` "We must get a turbo!" (`010df0..010dfa`), fuel unchanged, speed unchanged. **`$6037=$ff` plus a turbo unit `$176ae=$100`**: `$10c0` falls `1c -> 13` in 54 passes (1 per 8), `$176ae` falls 5 per pass, and the speed reaches `$80fd4c` (hi word 128 vs 92 without turbo): +39 % top speed while it lasts. When `$10c0` reaches 0 the same path posts "We need turbo fuel!" (`010e0a`).
* `$176ae` has no writer in the race code except `clr.w` at `0073cc` and the turbo countdown (`010e3e..010e4a`); it is therefore **set outside the race (a shop/garage purchase) [INFERENCE]**. In the first race it is 0, i.e. the cup is **decorative unless the player owns a turbo unit and holds SPACE**.
**Display-only check:** `f620` skipped: 0 differing bytes in the state gate (135 passes driving, 175 standing), no pixels outside its own box; the only side effect is the lost slosh sound `$36`. Removal saves 11.6 k driving (1.4 %), 9.8 k standing; clean (bottom item).

### 5.6 Speedometer and gear lever (bottom right)
Speedometer `f7f0` (`efb2`): 64x24 dial sprite at (256,151) every pass (15.2 k) + needle from `$90 - hi($10d8)/8` through the sine table, two parallel lines (3.3 k) = 19.3 k; reads `$10d8` hi word only. Gear lever `f76a`: reads `$11d9` (low/high gear, toggled by FIRE while racing, sound `$3f`), animates `$11dc` (4 frames) and draws the 32x15 lever sprite at x=272+10 (a 10-pixel shifted kernel path), 11.3 k. Both redraw every pass (road repaint). Removal: 21.5 k + 13.1 k = 33.6 k (4.0 %), clean, 0 state differences.
**Alignment test (measured, `xt_gear_x272.json`, poke of the `move.w #$11a,d0` immediate at `$f7de` to `$110`):** the gear lever sprite drawn at x=272 (16-pixel aligned) costs **5.7 k instead of 11.3 k**: it is the only HUD sprite that is not aligned (282 and 15 = 10, shifted kernel path), and the shifted path costs twice the aligned one. Moving the lever 10 pixels left saves 5.6 k per pass (0.7 %) but changes the look; a pre-shifted, aligned 3-group copy of sprites 17-20 keeps the pixels and should cost about 8 k (1.5 x the 2-group aligned cost) = **-3 k per pass [INFERENCE for the 3-group figure]**.

## 6. Ranking (saving per visual loss) and cumulative effect

Visual loss is my judgement (1 = nothing is missed, 5 = essential information gone); savings are the measured driving/no-speech numbers (stock; shipped in brackets).

| rank | candidate | saving per pass | visual loss | note |
|---|---|---:|---|---|
| 1 | minimap removed | 63.3 k (39.4 k) = 7.5 % (5.2 %) | 1 (user: little value) | needs a one-time box clear |
| 2 | cup removed | 11.6 k (9.9 k) = 1.4 % | 1-2 (turbo fuel only matters with a turbo unit) | clean |
| 3 | speech: face + typing drawing off (ticker state machine kept) | 14.4 k average, 19.7 k while typing (1.7 %-2.3 %) | 2 (charm, hints) | do NOT skip `11ef0` itself |
| 4 | gear lever removed | 13.1 k = 1.5 % | 2 | clean; moving it 10 px left to an aligned x measured -5.6 k (no removal, look changes); pre-shifted copy ~ -3 k, no loss |
| 5 | clouds (not HUD) | 80.8 k = 9.5 % | user: OK | `sprites.md`; their mask writes (-9 k+ in the HUD) go too |
| 6 | score: only changed glyphs / shipped `mr_digit` | 17.0 k (shipped), + ~13 k more estimated | 0 | not removal |
| 7 | dial: redraw only when the hand byte changes | ~ 6.9 k | 0 | `cmp.l` -> hi byte |
| 8 | speedometer -> number | 19.3 k -> ~4-9 k | 3 | see §7 |
| 9 | dial removed | 11.1 k = 1.3 % | 4 (time left is essential) | keep it |
| 10 | thermometer / position / puff | < 2 k average | 4 | keep them |

Everything removed except the ticker: 148.3 k (17.6 %) driving no speech, 161.3 k (18.4 %) speech; ranks 1-4 + the speedometer: 104 k (12.3 %).

## 7. Cheaper redraws that keep the look, and the numeric top bar (estimates)

All **[INFERENCE]** unless a measured number is cited. Measured glyph costs: score glyph path 6.06 k per glyph stock (36.4 k / 6 glyphs), **2.98 k with `mr_digit`** (17.9 k / 6; the kernel alone is 1.43 k per 15-row glyph, 8.6 k per redraw, `render_patches.md` §4); ticker glyph (8x8 font) **3.7 k per draw** (7.4 k per typing pass = 2 draws); one-colour byte kernel row = 94 cycles (`mr_digit` loop).
1. **Dial, hi-byte compare:** -6.9 k per pass, identical pixels (§5.3).
2. **Score, redraw only the changed glyphs** (`$11c2` +1 per pass at cruise: 1.1 glyphs change per pass on average, the trailing `0` never): 6 glyphs -> ~1.1-2 per pass: with `mr_digit` 17.9 k -> ~4-6 k (**-12..-14 k**), stock 36.4 k -> ~8-12 k (-25 k).
3. **Minimap:** (a) draw the frame lines once per buffer (-18.6 k; needs the clouds gone or a cloud-overlap test), (b) redraw only when its position state changes (60 % duty: ~ -40 % of the rest), (c) shrink the outline bitmap (new art) - together 40-55 k of the 63 k without removing the minimap.
4. **Gear lever:** aligned x=272 measured -5.6 k (position change); pre-shifted aligned copy of the art ~ -3 k, identical pixels.
5. **Face:** drawn once per message (static portrait): -12.3 k per active pass; looks different (no mouth movement).
6. **Numeric readouts in a one-colour top bar** instead of speedometer + gear + thermometer (user's idea). 6 characters (speed 3 digits, gear 1, temperature 2) with the existing glyph path = 6 x 2.98 k = **17.9 k worst case per redraw (everything redrawn every pass)**; with changed-glyph-only drawing (speed changes every pass only while accelerating, gear/temperature seldom): at cruise ~0-1 k, while accelerating ~3-6 k per pass (1-2 changed glyphs; each change is drawn twice for the two buffers).
   Against today's 19.3 k + 11.3 k + 0.15..13 k = 30.8 k+ per pass: **-13 k worst case, -25..-31 k typical (3.0-3.7 %)**. A dedicated one-colour 8x8 kernel (row 94 cycles as `mr_digit`: ~0.75 k per glyph + ~0.5 k call overhead) would make the worst case ~7.5 k and the typical ~1-3 k. The bar itself (one colour fill) costs one fill per buffer once.
   The top bar must not be covered by the road repaint (rows 120-199): top-of-screen elements are persistent, so a numeric bar there is redrawn only on change, unlike the bottom items.

## 8. What I could not determine / limits

* Real-hardware numbers: none, Hatari 2.6.1 8.02 MHz model only. The +-2 k phase effect between runs (raster/IRQ alignment) is inherent; single-element savings are quoted from windows of 37-53 common passes.
* **The "clear once" removal of the persistent (top) elements was not built or tested**; §4.3 lists the stale areas and what has to be repainted, the repaint recipe is inferred from `f214`'s fill (colour 15 = the sky colour that the raster palette rewrites).
* `$176ae` (turbo unit) is set outside the code image I disassembled, so how the player obtains a turbo is unknown; the +39 % speed is measured with a poked unit.
* Sprite ids -> pictures were not rendered; element names come from screen position, code (which variable, which writer) and the boxed screenshots. The thermometer sprite roles (0/1/2) are inferred.
* The no-speech/speech windows are single passes of one track (first race); the per-race speech share (76 % of passes) comes from one scripted run that never steers (it crashes into scenery and cars, which triggers most messages); a careful player will see fewer messages. Message count (22) and lengths (30-83 passes) are from that run.
* Visual-loss ratings in §6 are my judgement, not measured.
* The sub-costs of the cup, gear, thermometer sprites per row and all estimates in §7 are scaling from measured kernels, not tested patches.
* Not run: 4 MB/Mega STE/TT, cold boots, 16/32 MHz (this study never changes the code, only pokes a running snapshot).

## 9. Files

`work/hud/`: `hudlab.py` (lab), `skiprun.py`, `liverun.py`, `cum.py`, `runAB.py`, `monitor.py`, `monitor2.py`, `flow.py`, `vars.py`, `tab.py`, `analyze.py`, `report.py`, `mktables.py`, `boxes.py`, `dis.sh`; `dis/` (`all_7000_19000.txt`, `hud_f134_fa60.txt`, `msg_11ea0.txt`, `k_12392.txt`, `k_12690.txt`);
`res/` (`numbers.txt` all savings, `tables_stage.md`, `skip_*.json` per-pass stage cycles and state, `live3_*.json` with the shipped set, `sub_start.json`, `footprint_{A,B,C}.json`, `monitor_race.json`, `monitor2_*.json`, `flow_*.json`, `turbo_*.json`, `shots_*` buffer captures, `poison_*.bin`); `shots/` (`hud_boxed_speech.png`, `hud_boxed_driving.png`, `raw_*.png`).
Reproduce a skip run: `python3 work/hud/skiprun.py race_start 135 stock f22c+f214` then `python3 work/hud/report.py`.
The per-pass full-state pickles `res/gate_*.pkl` (180 MB, input of `report.py`'s state comparison) were deleted after use; the results are in `res/numbers.txt` §"savings" (state column) and §4.2; rerunning `skiprun.py` recreates them. `res/master_only.md` and `res/messages.txt` hold the master table and the message records; `res/xt_gear_*.json` the gear alignment test.
Process note: nothing outside `work/hud/` and this file was written; no patch, no change to `tools/`, `patches/`, `originals/`. Every Hatari was started through the harness with its own scratch dir. **Mistake to disclose:** once, to stop my own hung run, I used `pkill -f "hudlab|python3 -"`; that pattern can also match other agents' `python3 -...` processes, so a script of another agent may have been killed at that moment (my orphan Hatari/Xvfb were then killed by pid/scratch-dir name only).
