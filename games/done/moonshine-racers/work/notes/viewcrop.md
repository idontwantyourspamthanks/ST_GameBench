# Moonshine Racers: cycles per row band and extra-frame road redraw (lever D)  (MSRViewCrop)

Scope after the user's decision (relayed by Main): the smaller 3D view (letterbox, row dropping, line doubling, bigger HUD bar = levers A/B/C) is REJECTED ("big negative impact on gameplay"); nothing about it was built or mocked up. Kept: (1) a short cycles-per-row-band table for the record, (2) lever D: could an EXTRA frame redraw only the road rows that differ from what the destination buffer holds, and can an extra reuse the main frame's geometry.
Nothing was enabled or shipped; `tools/`, `patches/`, `originals/` untouched. Everything is in `work/viewcrop/` (private `msrpatch_priv.py` with ROOT fixed, live images `live/F` = default set without pacer, `live/X` = default set with `mt_clock mt_pre mx_pre mx_sync`, built with that private tool on the CURRENT patch sources, `verify: ALL OK`).
Evidence tags: **[M]** = measured here (raw in `work/viewcrop/res/`), **[I]** = inference.

## 0. Result in one page
* **Lever D is worth about nothing.** Upper bounds, measured on real extra frames at their own pose (emulator, 8 start/level scenes, 190-580 extra frames each): the share of the ~86 road rows that the destination buffer already holds EXACTLY (pixel identical, which is the true bound of any "redraw only what differs" scheme) is **1.5-3.2 % of the rows at the actual 16 MHz poses (0.33-0.67 tick between the extra and the frame that drew the destination), 6.1 % at best (straight 'up' run), 0.3-0.6 % at the 8 MHz-like gap of 1.5 ticks** = 1.5-6 k of rd_draw's 99.7 k cycles, i.e. **less than the ~5 k a per-row record test would cost (86 rows x 60 cycles)**. Net saving <= 0 [M for the fractions, I for the 60-cycle test cost].
* The reason is not the road: **the rows whose span record (w0,A,B,F) is unchanged are 9-31 % (8-16 MHz gaps), but 80-85 % of those are overpainted by the player car / objects** (the car sits at pixel bytes 64-95 of rows ~150-199 and the record-equal rows are the near ones). Sprites and the HUD are drawn over the road in the same buffer, so the buffer row almost never equals the pure road row.
* **An extra cannot reuse the main frame's geometry tables without changing the picture**: against its own main frame only 13-52 % of the rows have the identical record (extra at 1/3 tick: 28-31 % on zig steering, 52 % straight; at 2/3 tick: 13-29 %); of the rest 7-23 % differ only in the stripe counter F and 35-79 % have an edge moved by a median of 2-5 px (p90 4-12, max 64). An extra with the main's records would show a road frozen at the main pose while objects/horizon/stripes move, and would not equal a full redraw. A real extra needs its own `rd_geom` call: **57.0 k cycles (Musashi, 5 scenes: 56.7-57.1 k; about 54 k fixed + 37 per record) + `rd_draw` 89-100 k** = 36 % of an extra frame. Table reuse would save at most 57 k - ~13 k (pass C: stripe machine + record emission, `road.md` 6.1) = ~44 k per extra, but it is a visible change (stale road edges, steering shown at 10 Hz): [I] not pixel-identical, so NOT a gate-able pure optimisation; the user would have to approve it as a look change. Not built.
* **Side finding, not asked for (Musashi, whole-pass model of the current default set): the extra-frame machinery itself is expensive.** `mx_sync` group start (first extra) 34.1 k, each extra 16.4 k, group end (tail after the last extra) 34.5 k, i.e. **~68.6 k fixed per tick that has any extra + 16.4 k per extra**, in the code windows `$B8A80` (25.4 k: byte-wise `move.b (a0,d2.w),(a1)+` save loops over the ring windows/static ranges), `$B87A0/$B87C0` (13.1 k), `$B8AA0` (5.5 k), tail `$B8B00` (22.6 k: 2688-byte slot restore as `move.l (a0)+,(a1)+` loop), `$B8AE0` (6.0 k), `$B8B20` (3.1 k). An extra frame measured this way costs 441-473 k (2.75-2.95 VBL) on the `start` scene, not 2.3 VBL; see section 4. This is where 50-80 k per tick can still be found (word/long moves instead of byte loops, movem for the slot copy), independent of any crop.

## 1. Tools and method (all reproducible: `python3 work/viewcrop/<script>`)
* `mlib.py` + `musashi/drv2.c` -> `musashi/libm68k2.so`: the project's Musashi core (plain 68000 cycle table, `work/road/musashi`) with a write hook that tags every instruction with the screen row (0-199, either buffer) it wrote. Plain-cycle totals match Hatari's: whole pass 441-477 k on the driving frames (Hatari 2.77-2.89 VBL = 444-464 k), `rd_geom` 57.0 k and `rd_draw` ~92-100 k vs `road.md` 57 k / 95 k.
* `cap.py DUMP NPASS NX KIND OUT`: Unicorn (`work/extrap/emu.py`, exact) runs the CURRENT default set (live image X) from a stock 1 MB dump at `$7a88` (`work/extrap/h_start_7a88.bin`: driving, speed 9-10; `work/int/mx/dumps/L0/L5/L10/L12.bin`: levels 1/6/11/13 at the race start, speed 7), `X_TEST` = NX extras per tick at f = j/(NX+1), steering `zig` (up / up+left / up / up+right, 15 passes each) or `up`. Code hooks at `$B5004` (rd_draw: records `$4b84..$4f78`, the destination rows at entry, regs), its return address (buffer after the road draw = the pure road rows), `$d1ca` (flip: the finished image), `$B4004` (rd_geom). At every rd_draw/rd_geom call after 6 warm-up passes the RAM is handed to Musashi to get its exact cycles; per-record cycles are cut at the row-loop label `$B503C`. Frames per run: 400-800.
* `ana.py` (pairs), `ana2.py` (extra vs own main, slot level), `ana3.py` (slots by gap), `mkpng.py` (picture), `band.py`/`bandana.py` (per-row-band cycles of the whole pass: Musashi runs `$7a88 -> $7b74` from the Unicorn state at passes 30-32/60-62/90-92 of `start`, stages cut at the pass-table `jsr` sites), `extracost.py`/`mxprof.py` (whole extra frame by code range), raw outputs `res/*.txt`. The big pickles (`res/c_*.pkl`, 40-80 MB) were deleted after analysis; `cap.py` regenerates them in ~60 s.
* Definitions for a pair (g, f): g = the frame whose finished image the destination buffer holds, f = the extra to draw. Road rows k = 0..n-1 (n = 66-102, mean 86; row k = screen row 199-k). **(a)** record f[k] == record g[k] (w0,A,B,F); **(b)** the 160 bytes of g's final image at that row == f's pure road row (what rd_draw writes); **(c)** a and not b = row overpainted by sprite/HUD since the road was painted; F-only = (w0,A,B) equal, F differs. With two buffers the destination of frame i is the image of frame i-2.

## 2. Cycles per row band (main pass, default set, `start`/zig passes 30-32, 60-62, 90-92, mean of 9 = 449.6 k cycles, raw `res/band_table_start_zig.txt`)
Stages (cycles): objects/sprites incl. `mx_pre` 210.9 k (89 rows written, 2.0 k not row-attributable); road draw (`mt_pre` + `rd_draw`) 98.4 k; **road geometry 57.1 k (writes no screen row)**; horizon draw 35.4 k (55 rows); object projection 11.4 k; logic/other 9.9+2.8+2.7+2.2+1.7+1.5+1.3+1.2+1.1+0.6+0.6 k; HUD stage 8.7 k (62 rows); span clear 2.1 k. Rule for rows: the cycles an instruction chain spends before a screen write are charged to that write's row (road: row control + loads + fills of that record; sprites: setup before the first written row, then the rows).

| screen rows | all stages | road draw | horizon | objects/sprites | HUD stage | cycles/row |
|---|---:|---:|---:|---:|---:|---:|
| 0-15 (top bar) | 2,902 | | | | 2,902 | 181 |
| 16-31 | 2,430 | | | | 2,430 (ticker/face) | 152 |
| 32-47 | 2,143 | | | | 2,143 | 134 |
| 48-64 | 646 | | | | 646 | 38 |
| 65-74 | 4,894 | | 4,894 | | | 489 |
| 75-84 | 7,500 | | 7,500 | | | 750 |
| 85-94 | 7,500 | | 7,500 | | | 750 |
| 95-104 | 18,468 | | 7,500 | 10,968 | | 1,847 |
| 105-114 | 61,356 | 1,414 | 6,723 | 53,219 | | 6,136 |
| 115-124 | 50,130 | 9,784 | 1,237 | 39,110 | | 5,013 |
| 125-134 | 33,550 | 11,706 | | 21,845 | | 3,355 |
| 135-144 | 26,180 | 11,589 | | 14,592 | | 2,618 |
| 145-154 | 25,026 | 11,812 | | 13,213 | | 2,503 |
| 155-164 | 21,977 | 11,689 | | 10,288 | | 2,198 |
| 165-174 | 28,814 | 11,541 | | 17,274 | | 2,881 |
| 175-184 | 31,947 | 11,581 | | 20,367 | | 3,195 |
| 185-194 | 19,490 | 11,468 | | 8,022 | | 1,949 |
| 195-199 | 5,746 | 5,746 | | | | 1,149 |
(rows written sum to 392.0 k; the other 57.6 k are geometry, logic, projection without a screen write.)
* **Road draw is flat per row: ~1.16 k per record row** whether near or far (rd_draw per record by k band, `res/road_perrow.txt`: k 0-9 1,096-1,120, k 10-76 1,138-1,170 on three scenes), 86 rows mean (66-102). 34.9 % of it (34.3 k) is in the instructions that write screen words (movem fills + window stores, `res/road_fillshare.txt`); 64.1 k is row control / loads / jumps.
* **Geometry does not scale with rows**: 54 k fixed + 37 per record (fit over 580 frames, `res/road_perrow.txt`); dropping rows would only save the 37/row emission.
* **Horizon strip 0.64-0.75 k per row** (55 rows). **Sprite cost is per sprite, not per row**: the 53 k + 39 k in rows 105-124 is the setup of far small objects (charged to the first row they write); rows 105-124 hold 41 % of the object stage.
* HUD strip and sky together are 8.1 k per pass (1.8 %): the sky rows are free.

## 3. Lever D: redraw only differing road rows in an extra [M]
Destination = the real same-buffer predecessor (frame i-2); "gap" = pose difference in ticks between f and g. `start`, zig steering; the straight run and levels 1/6/11/13 are in `res/leverD_summary.txt`.

| scene / run | extra vs frame | rows | (a) record equal | (b) pixels equal | (a)&(b) | (c) overpainted | rd_draw | skip (b) | skip (a)&(b) | skip (a)* | net a&b after 60/row |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| start zig, 1 extra/tick (8 MHz-like) | actual dest (1.0 tick older) | 86.1 | 9.2 % | 1.8 % | 1.5 % | 7.6 % | 99,765 | 1,701 | 1,469 | 9,101 | -3,699 |
| start zig, 1 extra/tick | frame 1.5 ticks older (what a thinned 8 MHz run mostly has) | 86.1 | 1.8 % | 0.6 % | 0.4 % | 1.5 % | 99,765 | 581 | 362 | 1,833 | -4,806 |
| start zig, 2 extras/tick (16 MHz) | actual dest, extra | 86.1 | 16.3 % | 2.8 % | 2.5 % | 13.9 % | 99,775 | 2,656 | 2,403 | 16,244 | -2,765 |
| start zig, 2 extras/tick | 0.33 tick older (best case, 2nd extra) | 86.1 | 28.9 % | 4.2 % | 3.8 % | 25.0 % | 99,775 | 3,993 | 3,726 | 28,753 | -1,442 |
| start zig, 3 extras/tick (32 MHz) | actual dest, extra | 86.1 | 20.8 % | 3.2 % | 2.9 % | 17.8 % | 99,764 | 3,095 | 2,820 | 20,643 | -2,348 |
| start straight ('up'), 2 extras/tick | actual dest, extra | 85.9 | 31.1 % | 6.5 % | 6.1 % | 25.0 % | 99,240 | 6,177 | 5,802 | 30,725 | +647 |
| start straight, 2 extras/tick | 0.33 tick older (best case in all runs) | 85.9 | 50.8 % | 9.5 % | 9.1 % | 41.7 % | 99,240 | 8,976 | 8,709 | 50,253 | +3,554 |
| levels 1 / 6 / 11 / 13 (L0/L5/L10/L12 dumps, speed 7 start) zig, 2 extras | actual dest, extra | 85.3 / 77.5 / 81.4 / 81.0 | 18.4 / 13.6 / 11.6 / 17.4 % | 2.7 / 4.0 / 2.3 / 2.6 % | 2.5 / 2.9 / 2.2 / 2.6 % | 15.9 / 10.7 / 9.4 / 14.8 % | 98.7 / 89.4 / 94.6 / 94.3 k | 2.6 / 3.3 / 2.2 / 2.4 k | 2.4 / 2.5 / 2.1 / 2.4 k | 18.1 / 12.0 / 11.0 / 16.3 k | -2.7 / -2.2 / -2.8 / -2.5 k |
(* skip (a) = cycles of the rows with equal records if the sprite-overpainted columns could be repaired for free, which they cannot: see below. ** the 60 cycles per row = two `cmpm.l`/`cmp.l` on the stored record of the buffer (40) + `lea 160(a0)`/loop (20) [I]. Level 13 (L12) is mostly a slow/standing stretch (only 227 extras in 200 passes; its MAIN frames are 50.6 % record-equal, 6.4 % clean, because the road barely changes there).) Exact raw lines: `res/leverD_summary.txt` (all gaps 0.25-3.0 ticks for each run).
* `b&!a` (pixel equal although the record differs) is 0.2-1.1 % of the rows: a pure pixel compare would find nothing more.
* **Why (c) is so large**: in an ad-hoc dump of frames 100-103 of `start`/zig (printout not saved) the differing bytes of the record-equal rows 177-189 are in columns 64-95 (the player car, 32 bytes = 64 px) of rows 177-189 and the same rows in every frame; the record-equal rows are the near ones, which is where the car and the AI cars are. The buffer holds g's sprites; the road under them is only restored by repainting the road (the sprite kernels composite onto the screen content). A scheme that keeps these rows needs the "overpainted row/column mask" maintained by every sprite and HUD routine that `road.md` section 5 already ruled out.
* **Slot (16-px group) level** (`res/leverD_slots.txt`): of all road slots 62.3 % are equal at gap 0.5, 53.1 % at 1.0, 44.5 % at 1.5, 36.8 % at 2.0 ticks (`start` zig, 3 extras per tick; straight run 67.5 % at 0.33). Fills (the part a skip could save) are 34.9 % of rd_draw (34.3 k), so the gross slot-skip bound is 0.35 x 0.45..0.62 = 16-22 % of rd_draw = 16-22 k at gaps 0.5..1.5, with the decision cost ignored. The decision needs, per row, the old and the new edge positions (the old record per buffer) and the sprite masks, ~100+ cycles per row = 8.6 k+, and the row control (64.1 k = 64 % of rd_draw) stays; so the net upper bound is **about 5-13 k per extra at 16 MHz poses, ~0 at 8 MHz gaps**, with very high complexity (per-buffer record store, dirty masks in the car/object/HUD routines, clipped windows) [I].
* **Visibility / risk**: a correct scheme is pixel-identical to the full redraw by construction; the risk is stale rows (a missed overpaint, a clipped window) = leftover car/edge pixels on the road in extras only (main frames are drawn full).
* **How I would gate it, if it were ever built**: in the Unicorn model (`cap.py` style, 2/3 extras per tick, zig and straight, 5 scenes, 600+ frames) compare the finished buffer at every flip of the patched run against the unpatched run's (the full redraw of the same pose): 32,000 bytes identical in every frame; negative controls that must DIFFER: (1) skip rows on record equality only (ignore overpaint), (2) drop the F bits from the compare, (3) never invalidate the stored record at a buffer's first use; plus the standard state gate (`work/int/mx/*`, 0 differing addresses) and a Hatari run at 16 MHz.
* **Recommendation for lever D: do not build** (bounded by 1.5-6 k gross for whole rows, <= 13 k for a slot scheme that is not worth its complexity and nothing at 8 MHz where the gap is 1.5 ticks).

## 4. Geometry in extras, and what an extra costs [M, Musashi, `start` zig, passes 30/31/60/90]
`res/extracost_x1.txt`, `res/extracost_x2.txt` (whole `$7a88 -> $7b7a` run with `X_TEST` extras; segments cut at the flips):
```
X_TEST=2: main pass up to its flip 460,494 (rd_draw 99.3 k, rd_geom 57.1 k, mx/mt blobs 13.3 k)
          extra 1 (incl. flip) 473,187 (rd_draw 98.9 k, rd_geom 57.0 k, mx/mt blobs 50.6 k)
          extra 2 (incl. flip) 441,544 (rd_draw 99.2 k, rd_geom 57.1 k, mx/mt blobs 16.4 k)
          tail after the last flip 34,594 (mx/mt blobs 34.5 k: group-end undo)
X_TEST=1: main 459,855; extra 473,356; tail 34,594
```
* Each extra re-runs the whole render: rd_geom 57 k + rd_draw 99 k + sprite kernels 186 k + horizon 34 k + tc_ord/tc_proj 24 k + HUD 3.4 k = ~405 k, plus `mx` overhead: 16.4 k per extra, 34.1 k at the first extra (group start), 34.5 k at the group end.
* **Per tick with >= 1 extra the pacer pays ~68.6 k fixed + 16.4 k per extra on top of the render [M]**; that is 0.43 VBL + 0.10 VBL per extra. Where (`mxprof.py`): `$B8A80` 25.4 k, `$B87C0` 7.0 k, `$B87A0` 6.1 k, `$B8AA0` 5.5 k at the start; `$B8B00` 22.6 k, `$B8AE0` 6.0 k, `$B8B20` 3.1 k at the end (disassembly: byte loops `move.b (a0,d2.w),(a1)+ / addq.w #1,d2 / dbra` = 28 cycles per byte at `$B8A80`; `move.l (a0)+,(a1)+ / dbra` over 2688 bytes for the slots at `$B8A8C`.. and `$B8AFC..`). [I] Replacing the byte loops by word/long moves and the 2688-byte slot copy by `movem.l` bursts would cut a good part of the 68.6 k; this is a code-only change inside `mx_sync` (private to the extras path, gate = the existing mx state gate). Not built here (outside the assignment); numbers are a model, not Hatari: confirm with `msrstages.py` before acting.

## 5. Files
`work/viewcrop/`: `msrpatch_priv.py`, `live/{F,X}.{img,json}`, `musashi/` (copy of the project's Musashi + `drv2.c`, `libm68k2.so`), `mlib.py`, `cap.py`, `ana.py`, `ana2.py`, `ana3.py`, `band.py`, `bandana.py`, `extracost.py`, `mxprof.py`, `mkpng.py`, `mock_leverD_rows.png` (an extra at 0.5 tick from its destination, left, and at 1.25-1.5 ticks, right: green = record equal and pixels equal, blue = record equal but overpainted, red = record differs; viewed), `res/*.txt`.

## 6. Not done / unproven
* Levers A/B/C (crop, line doubling, bigger bar): dropped by the user's decision; the per-row table above is the only residue.
* All cycle numbers are the plain-68000 Musashi model (no wait states, no interrupts, no blitter) on `start`/zig and four level dumps; Hatari was NOT run for them (the cycle totals agree with the Hatari numbers of the notes within 1-3 %).
* The 8 MHz-like case is represented by 1 extra per tick (`X_TEST=1`, gap 1.0 and 1.5 to older frames); the real 8 MHz pattern (29 % of ticks) was not replayed.
* `b8300`-window attributions in section 4 are by address windows read from the live image disassembly; I did not map them to source labels.
