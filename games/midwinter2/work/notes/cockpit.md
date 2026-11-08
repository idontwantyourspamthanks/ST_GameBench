# Cockpit overlay replay ($30f2c): cost by region, opacity, and what can be skipped

Dump and snapshots: `work/dumps/ram_ingame_lobos.bin` (2 MB, on foot at Lobos), `work/snapshots/1mb_ingame_{foot,walking}.sav`.
Disassembly: `python3 tools/m68dis.py work/dumps/ram_ingame_lobos.bin <addr> --profile work/prof/walking.txt`.
All numbers below come from `work/cockpit/overlay_analysis.py` (list decode + per-record cycle model calibrated on
`work/prof/walking.txt`), `work/cockpit/writers.py`, `work/cockpit/multicmp.py`, `work/cockpit/fps_long.py`, `tools/abtest.py`.
Unobserved statements are marked `[INFERENCE]`.

## 0. Answers in one table

| | Result |
|---|---|
| Replay cost | 62,313 cycles per call, 19 calls in `walking.txt` = **3.35 %** of a frame (frame = 1,859,013 cycles). The "2.95 %" in `clears_blits.md` is the masked-record loop only (53.8 k); the 28 run-copy records add 8.5 k. |
| Where | dashboard (lines 182-199) **31.4 %** = 1.05 % of a frame; left pillar 34.0 % = 1.14 %; right pillar 34.0 % = 1.14 %; nothing else (call overhead 316 c = 0.02 %). |
| Opacity | Every pixel the list touches is either fully opaque or fully transparent (0 mixed pixels of 8,992). 11.9 % of the 3D window (5,396 of 45,298 px) is opaque; **no screen row is hidden**: the fewest visible window pixels on any row is 59 (line 198). |
| Pixel-identical skip of hidden rows, overlay drawn once | **Not possible.** The renderer writes every row and every opaque group each frame (sky fill rows 58-199; terrain overwrites all 208 opaque dashboard groups before the replay, measured). |
| Pixel-identical, implemented | **"Clean prefix" set** (section 4C): fill and replay only the rows the terrain can have touched. abtest exit 0 at `--flips 10` and `--flips 40` on both default snapshots, 7 snapshots x 10 flip counts identical. **+4.0 % / +4.3 % fps** (foot 253 -> 263, walking 276 -> 288 flips per 3000 VBL); saves 66.5 k cycles per frame on foot (3.6 %), 77 k on walking (4.2 %). Needs 384 B of blob space (does not fit $B4E00-$B4EFF; placed in the free hole $B44C0-$B4693). |
| Pixel-identical, faster loop | Not implemented: <= 0.4 % before, <= 0.15 % after the set above (section 4D). |
| Visual tradeoff (not enabled) | `p4_hud_crop_*`: 3D window ends at line 181, dashboard drawn once per buffer: **+7.5 % foot, +7.6 % walking, +8.4 % zoomed foot**; before/after in `work/cockpit/crop_compare_*.png`. |

## 1. Overlay mechanics (re-verified)

- List at `$68000`: word count-1, 382 records, 6,734 B, written only by the encoder `$30e30` (0 hits in a 256-VBL walk; callers `$28cee` <- `$28cc0` <- `$31632/$32ebc/$33016`).
  The list bytes `$68000-$69a4d` have the same md5 (`e5f54c4c7dce635598a6200ff4b4a853`) in the 2 MB dump and in both 1 MB snapshots
  while `$6888` (the HUD distance word) differs (`024a` vs `04f8`): the "overlaps `$6888`" remark in `clears_blits.md` is a mix-up with the low-memory word, the list is static.
- Record formats, from the replay loop (`$30f3a-$30f68`): masked = `delta.w, mask.l, or1.l, or2.l` (14 B, 8 destination bytes,
  `dst = (dst & mask) | or`, the same `mask.l` is used for both longs); run-copy = `~delta.w` (bit 15 set), `n-1.w`, `8n` data bytes. Records are in ascending destination order,
  a run never crosses a screen line (encoder clears its run flag `$71b4` at every line end, `$30f1a`).
  Decoded: 354 masked + 28 run-copy = 382 records, 4,496 destination bytes, list 6,732 B + count word; matches the notes.
- The encoder treats **colour 15 as transparent** (`$30ea6-$30eb0`: d4 = ~(p0&p1&p2&p3), 0 = all-white = no record).
- Replay is skipped for `$6220` in {5, $15, $11} (`$1dbee-$1dc04`), run once per frame from `$1dc0c` (`jsr $5002` -> `jmp $30f2c`), after the terrain pass, on the back buffer (`$67a6` -> `$71c0`).

## 2. Q1: cost by region

Cycle model: masked record 140.4 c (profile: head `move.w/bmi` 16.3 + body 124.1); run-copy record 48.3 c + 52.6 c per 8-byte group. Sum over the decoded list = 61,997 c vs 62,313 measured per call (call overhead 316 c).
Regions: dashboard = lines 182-199 (first line holding a run-copy record), pillars = lines 58-181 split at x = 160.

| Region | Lines | Records (masked + copy) | Dest bytes | List bytes | Cycles / frame | Share of replay | Share of a frame |
|---|---|---:|---:|---:|---:|---:|---:|
| (a) Dashboard | 182-199 | 80 (52 + 28) | 2,080 | 2,504 | 19,591 | 31.4 % | 1.05 % |
|  - upper part | 182-191 | 58 (38 + 20) | 1,008 | | 10,929 | 17.5 % | 0.59 % |
|  - solid band | 192-199 | 22 (14 + 8) | 1,072 | | 8,662 | 13.9 % | 0.47 % |
| (b) Left visor pillar | 58-181 | 151 (151 + 0) | 1,208 | 2,114 | 21,203 | 34.0 % | 1.14 % |
| (b) Right visor pillar | 58-181 | 151 (151 + 0) | 1,208 | 2,114 | 21,203 | 34.0 % | 1.14 % |
| (c) Anything else | - | 0 | 0 | 0 | 316 (movem + setup) | 0.5 % | 0.02 % |
| Total | 58-199 | 382 (354 + 28) | 4,496 | 6,732 | 62,313 | 100 % | 3.35 % |

Per line: 97 pillar lines have 2 records (one per side), 27 have 4 (the strip crosses a 16-pixel group boundary).
Dashboard run-copy groups per line: 8 on lines 182-187, 10 on 188-191, 14 on 192-195, 16 on 196-199 (208 groups = 1,664 B).
The dashboard's 28 run-copy records cost 12.3 k (0.66 % of a frame) although they are only 1,664 B, because each 8-byte group costs 52.6 c (2 x `move.l (a1)+,(a0)+` + `dbra`).

## 3. Q2: is the mask opaque? rows and columns

Pixel-exact decode (`overlay_analysis.py`, image `work/cockpit/overlay_regions.png`: dark green = opaque pillar, orange = opaque dashboard,
light = transparent pixel inside a record, blue = no record, red line = line 182):

- Mixed pixels (some planes kept, some replaced): **0**. Plane masks differ within a record: **0**. So the overlay is a binary opaque/transparent cut-out.
- Opaque pixels: pillars 1,560 (3.4 % of the window), dashboard 3,836 (8.5 %), total 5,396 = 11.9 % of the 319 x 142 = 45,298 window pixels (x 1-319, y 58-199).
  Transparent pixels inside records: pillars 3,272, dashboard 324. Colours of the opaque pixels: 0 (1,024), 1 (2,222), 3 (1,099), 5 (79), 7 (806), 8, 10, 12 (120), 13, 14 (never 15).
- **Pillars (lines 58-181): thin curved strips, 6-7 px wide, with transparent pixels on both sides** (the 3D view shows through on the outside and inside).
  Opaque x per line (left / right): line 58 14-20 / 299-305; 61 15-21 / 298-304; 100 28-34 / 285-291; 150 37-42 / 277-282; 181 38-43 / 276-281.
  There are no holes inside a strip.
- **Dashboard (lines 182-199)**: two opaque wings with a see-through gap in the middle on lines 182-191, one solid band below:
  line 182 38-120 and 199-281; 185 38-124 and 195-281; 191 35-130 and 189-284 (gap 121-198 narrowing to 131-188);
  line 192 34-285; 196 32-287; 197 31-288; 199 30-289. Left of x = 30..38 and right of x = 281..289 the 3D view shows on every dashboard line, and the middle gap shows it on lines 182-191.
- Consequence: **there is no screen row that is completely hidden**. The fewest visible window pixels on any row are 59 (line 198: x 1-29 and 290-319).
  Rows cannot be dropped from the renderer, only parts of rows.

## 4. Q3: pixel-identical options

### 4A. (i) as posed: skip rows hidden under opaque regions, draw the overlay once per buffer: not possible

Evidence (original game, `work/cockpit/writers.py` on `1mb_ingame_foot`, repeated on `1mb_ingame_walking`):
```
foot_check back buffer 0x70000
 fill exit: rows 58-199 all pure fill: True
 replay entry: first row != fill (terrain ymin): 155 ; rows 182-199 not pure fill: 18 of 18
 replay changes rows [58] .. [199]
 rows changed between replay exit and flip: []
 rows 0-57 changed between fill exit and flip: 0
```
walking: first terrain row 151, rows 182-199 not pure fill 18 of 18. Also, comparing the buffer at replay entry with the list: **all 208 run-copy groups (every fully opaque 8-byte group of the dashboard)
had been overwritten by the terrain before the replay**, in both snapshots.

- Sky fill `$1b996`: writes lines 58-199 x 160 B every frame (`$1b9a4` a6 = base + $2440, `$1b9a6 moveq #$46,d7` = 71 passes x 2 lines): the pillar and dashboard rows are rewritten every frame. (Measured here 53.8 k c per call on foot, 19 calls: 1,022,552 c; `clears_blits.md` has 46.5 k.)
- Span filler `$38c6e`: rows ymin..ymax per polygon, `d7 = ymax-ymin`, skipped if d7 < 0 or >= 200 (`$38c8c-$38c94`); the polygon clip window is lines 58-199 (`$67ae-$67b4` = 1/319/58/199, projection.md). Terrain polygons do cover the dashboard rows: measured below, all 208 opaque groups are overwritten before the replay.
- Replay: the only writer of the overlay pixels; nothing writes lines 58-199 after it (rows changed between replay exit and flip: none). The window/HUD renderer `$1cf64` (the only `jsr $5020` site, `$1d188`; stores into `$7b6b0/$7b9d0`, draws from `$78000`) has 0 profile cycles in `walking.txt`: not executed in the 3D view; `$38cd0` is hooked directly, so it would be seen anyway.
- Stopping at a row boundary is easy mechanically (sky: `moveq #$46,d7` -> `#$3d` ends the fill at line 181; filler: clamp `d7` at `$38c86`; both implemented in `p4_hud_crop_*`, section 5) but is **not pixel-identical**,
  since every row below the boundary still has visible pixels (section 3). Drawing the overlay once per buffer is pixel-identical only if nothing else writes the opaque pixels, which is false (terrain overwrote 208 of 208 opaque groups).
- Narrower variant "do not sky-fill the 208 opaque run-copy groups": needs the replay to run afterwards (it does not for `$6220` in {5,$15,$11}); saves 1,664 B x 2.03 c/B = 3.4 k c = **0.18 %**; not worth splitting the `movem.l` loop. Superseded by 4C.

### 4C. New: "clean prefix" (implemented, `default: no`): fill and replay only the rows the terrain can have touched

Observation (above): on every frame the sky fill writes pure sky, the terrain only draws from its first row `Ymin` downwards (foot 155, walking 151), and the replay is idempotent
(`(x & mask) | or` applied twice = once). Rows above `Ymin` therefore always end up as the same sky + pillar image. Keep that image in the buffer instead of rebuilding it:

1. `KB[b]` per screen buffer (b = bit 16 of the base: $60000 -> 0, $70000 -> 1) = number of 8-line blocks from line 58 that already hold the final image. `p4_hud_reset` clears KB at every 3D-view (re)entry (`$28cc0`).
2. `p4_hud_pfx_ymin` (`$38cd0`, entered by every polygon fill with d6 = first row) keeps `YMIN` = smallest first row of the frame; `p4_hud_pfx_fill` (`$1b996`) resets it to 200 and starts the fill at line 58 + 8*KB (`a6 += 1280*KB`, passes `$46 - 4*KB`).
3. `p4_hud_pfx_replay` (`$30f2c`): new KB = (YMIN-58)>>3 (0..17); replays only records at or below line 58 + 8*min(old KB, new KB). A skip loop (walks 14 B / 4+8n B records by destination)
   finds the first such record; the stop position is cached (CK/CA1/CA0/CD7) so the walk only happens when min(old,new) changes.
   Rows in [old KB, new KB) were refilled this frame but untouched by the terrain; rows in [new KB, old KB) were dirtied by the terrain: both are inside the replayed range, so every row is final.
4. The fill is also reached from the **alternate scene render `$327e6`** (`$328e2 jsr $505c`, camera from `$7584/$7588`), which never replays the cockpit. The fill hook recognises the main callers by the return addresses
   (`4(a7) = $1dbe2` for `$1dbbe -> $505c -> $1dc12 -> $1dca4`, `(a7) = $1dbee` for the direct `jsr $1b996` at `$1dbe8`); any other caller clears KB[b] first (full fill). Found while auditing `$505c`/`$1dc12` callers
   (`m68dis.py --xref 505c`: `$1dbde`, `$328e2`).

Files: `patches/p4_hud_pfx_ymin.s`, `p4_hud_reset.s`, `p4_hud_pfx_fill.s`, `p4_hud_pfx_replay.s` (all four together). Space: code 364 B (ymin 26 at $B44C0, reset 28 at $B44E0, fill 98 at $B4500, replay 250 at $B4580-$B467A) + 20 B data at $B4680 = 384 B.
The hole $B44C0-$B46BF is unused by the default set; it does **not** fit the 256 B at $B4E00 (dropping the skip cache saves about 68 B and costs about 0.7 %: still about 316 B).

Verification (final build of the four patches, live-applied):
```
== flips 10   (tools/abtest.py --only p4_hud_pfx_ymin p4_hud_reset p4_hud_pfx_fill p4_hud_pfx_replay --flips 10)
1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.1 (62 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 4.3 (87 flips)
exit 0
== flips 40
1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 3.0 (60 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 4.4 (88 flips)
exit 0
```
`multicmp.py` (both buffers captured after flips 2,3,4,6,9,14,20,28,40,60; base vs patched): ALL IDENTICAL on `1mb_ingame_walking`, `1mb_ingame_foot`, `ingame_foot_banked_turn` (horizon banked, terrain fills the view),
`ingame_foot_turning`, `ingame_foot_walking`, `ingame_lobos_foot`, and `work/cockpit/1mb_foot_zoom.sav` (cursor-up zoom of the rifle sight, a view zoom `$66e0`, no extra overlay: `foot_sight_up.png`).
The 1000-VBL abtest fps has 1.2-1.6 % resolution and drifts in game time between the two runs, so the speed was measured over 3000 VBL (`fps_long.py`):

| Snapshot | Base flips / 3000 VBL | Patched | Gain |
|---|---:|---:|---:|
| 1mb_ingame_foot | 253 (4.22 fps) | 263 (4.38) | +4.0 % |
| 1mb_ingame_walking | 276 (4.60) | 288 (4.80) | +4.3 % |
| ingame_foot_banked_turn (worst case: terrain covers the window, KB = 0) | 227 (3.78) | 228 (3.80) | +0.4 % |

Profile (Hatari `profile`, `foot`, 19 frames per window): fill 53.8 k -> 17.8 k c per frame, replay 62.3 k -> 28.1 k, `$38cd0` hook +3.7 k (34 polygon fills per frame, 106 c per hook call): **net -66.5 k = -3.6 % of a frame**. Walking: fill 53.8 k -> 11.6 k, replay 62.3 k -> 24.6 k, hook +2.6 k: -77 k (-4.2 %).
KB after 8 s on foot: 12 / 12 (96 lines skipped), YMIN 155, cache key 13 (`m $b4680 20`).

Risks (why `default: no`): the guarantee holds as long as nothing other than the sky fill, polygon fills and the replay writes lines 58-199 of the back buffer.
Checked: no writer between replay exit and flip (above), polygon fills all go through `$38cd0` (`$5020` is only called from `$1d188`, inside `$1cf64`, not executed in 3D (hook sits on `$38cd0` itself)), all `$1b996` callers (`$1dbe8`, `$1dca4`) and `$30f2c` callers (`$1dc0c`) listed,
`$328e2` handled. Not checked [INFERENCE]: other vehicle cockpits (lists differ, the logic is list-generic: ascending destinations, runs inside a line), screens that draw into the 3D rows and return without `$28cc0`,
state restore by HAGA (numpad `/` pressed once on the patched foot snapshot, screenshots 6 s and 14 s later: no artifact in the window; the only differences to the base run were the game clock and the blinking dashboard lights, which I take to be a time-dependent palette/blink [INFERENCE], not measured).
A periodic forced full refresh (clear KB every 16th frame) would bound any unknown artifact for about 6 % of the gain; not added.
Not done: a cold boot of a `mw2patch.py build` with the set (all tests above are live patches on snapshots; `build` of the set succeeds and `verify` is ALL OK), no other vehicle snapshot.

### 4D. (ii) a faster replay loop: not worth it

- Nominal 132 c per masked record (`move.w` 8, `bmi` 8, `adda` 8, `move.l` 12, `move.l` 12, `and` 8, `or` 14, `move.l` 12, `and.l` 14, `or` 14, `move.l` 12, `dbra` 10); Hatari measures 140.4. The RMW itself is ~ 98 c; the floor of any list-driven loop is ~ 125 c.
- Possible: separate masked/run-copy lists (drops `bmi`, -8 c x 354 = 2.8 k = 0.15 %), 2x unroll (-5 c per record, 0.1 %): **<= 0.3-0.4 % before 4C and <= 0.15 % on top of it** (4C already halves the records replayed).
- Blitter: not possible for the masked records (per-word varying masks; halftone RAM is 16 words); the opaque run-copy groups are 28 short runs of 64-128 B, each a blitter setup of about the same cost as the CPU copy (`blitter.md`).
- Not implemented.

## 5. Q4: visual tradeoff (implemented as an experiment, NOT enabled)

The pixel-identical set gives +4 %; the dashboard rows are the more expensive part (terrain is drawn under it every frame, then overwritten). Experiment `p4_hud_crop_*` (foot mode only, `$6220 = 13`):

- the sky fill and the span filler stop at line 181 (`p4_hud_crop_fill` at `$1b99e`: 62 passes instead of 71; `p4_hud_crop_clip` at `$38c86`: ymax clamped to 181);
- `p4_hud_crop_replay`: the first replay into each buffer blanks lines 182-199 to colour 0 and draws the whole list (dashboard band + pillars); later frames replay only the pillar records above line 182 and stop at the first record at or below it;
- `p4_hud_reset` (shared) clears the per-buffer "band drawn" flags at 3D entry. Excludes the `pfx` set (same sites).
- Visual change: lines 182-199 are no longer 3D view. The left and right slivers beside the dashboard (x < 30..38 and x > 281..289) and the notch above the middle of the dashboard (x 121-198, lines 182-191, narrowing)
  become black instead of showing the landscape. The dithered landscape above line 182 is untouched (no flat fill).

Screenshots (full Hatari captures, ST screen at (96,58), 2x): `work/cockpit/1mb_ingame_foot_before.png` / `1mb_ingame_foot_crop_after.png`, `foot_zoom_before.png` / `foot_zoom_crop_after.png`, `walking_before.png` / `walking_crop_after.png`;
the lower 75 lines side by side: `crop_compare_foot.png`, `crop_compare_foot_zoom.png`, `crop_compare_walking.png`.

Measured (3000 VBL, `fps_long.py`): foot 253 -> 272 flips (+7.5 %), walking 276 -> 297 (+7.6 %), zoomed foot 262 -> 284 (+8.4 %).
Profile on foot (19-23 frames): span-filler cycles 4.29 M -> 2.28 M (-47 %: terrain hidden under the dashboard is nearly half of the filler cost in this scene), sky fill -12 %, replay -20 %.
Estimated combined with the clean prefix: about +10-11 % [INFERENCE: not built, both patch the same three sites].
Limitations [INFERENCE]: foot only; cockpits of other modes keep the original code path; flags assume `$28cc0` runs on every return to the 3D view; the alternate render `$327e6` is not special-cased.

## 6. Pixel-identical idea not pursued: x-clipped spans under the dashboard

The terrain under the solid dashboard band (lines 192-199, opaque x 30..289 at the bottom line) is invisible, but spans are filled whole. A pixel-identical version would clip each span of those rows to the visible slivers
(x < 30..34 and x > 285..289), i.e. two spans per polygon row, through all 112 fill variants (`f38cd0.md`) or by drawing the polygon twice with clamped edge tables. The profile above bounds the gain (about half of the 5 % the crop gets;
the rest is the sky fill and the replay). High effort and risk; recommended only if the visual tradeoff is rejected.

## 7. Reproduce

```
python3 work/cockpit/overlay_analysis.py                 # sections 1-3 (tables, image)
python3 work/cockpit/writers.py work/snapshots/1mb_ingame_foot.sav foot_check   # 4A evidence
python3 tools/mw2patch.py live --only p4_hud_pfx_ymin p4_hud_reset p4_hud_pfx_fill p4_hud_pfx_replay --out /tmp/pfx
python3 tools/abtest.py --only p4_hud_pfx_ymin p4_hud_reset p4_hud_pfx_fill p4_hud_pfx_replay --flips 10   # and 40
python3 work/cockpit/multicmp.py work/snapshots/1mb_ingame_foot.sav /tmp/pfx foot 2,3,4,6,9,14,20,28,40,60
python3 work/cockpit/fps_long.py work/snapshots/1mb_ingame_foot.sav - 3000 ; ... /tmp/pfx 3000   # run both at once
python3 tools/mw2patch.py live --only p4_hud_reset p4_hud_crop_fill p4_hud_crop_clip p4_hud_crop_replay --out /tmp/crop
```
