# Moonshine Racers: is a track editor viable? (viability study, 2026-11-18, MSRTrackStudy)

Study only. Moonshine Racers v1.0 is frozen: nothing under `patches/`, `tools/`, `dist/`, `originals/` was touched. Work and raw outputs: `work/trackstudy/` (decoder `msrtrack.py`, plots `png/`, tables `level*_table.md`, logs `logs/`, runs `run_race.py`, `run_dump4m.py`, edited game folder `game_edit1/`).
Evidence tags: **[obs]** raw tool/Hatari output kept in `work/trackstudy/logs/` or shown here; **[disasm]** `tools/m68dis.py` on `work/dumps/ram_race_start.bin` (stock game, race, level 0); **[INFERENCE]** not proven.
Machine for every Hatari run: Hatari 2.6.1, STE, TOS 1.62, 1 MB (unless named), 8 MHz, own scratch dirs `/tmp/trackstudy_*`, one Hatari at a time.

User decision (Main, 2026-11-18): the editor must be **in-game**; it may need more than 1 MB and may be **inert at 1 MB** (the 1 MB game stays as released). Sections 5-8 are planned on that basis.

## 0. Verdict

**A track editor is viable, and unusually cheap on the data side: the track is a small, plain, fully understood stream format, and the game's own setup consumes it from exactly two fixed addresses.** The hard parts are UI work and the "only on >= 2 MB, only STE/Mega STE" delivery, not the engine.

| piece | rating | why (evidence in the section named) |
|---|---|---|
| read/decode all 15 tracks | **done, proven** | six plain word streams per track, every stream of all 15 tracks sums to exactly 32768 units; decoded, tabulated, plotted (sections 1-2) |
| PC tool (decode, validate, render PNG, build track file / patched MS2) | **high** (~8 h) | format is trivial; limits known (section 2.3); runtime proof of one file edit done (section 3) |
| overlay loading (user tracks from a file) | **high** (~12 h) | the game reads the track through ONE `jsr $d6fa` (`$77da`) and ONE `lea $58c00` (`$fda2`); redirecting those two sites to a working copy removes the 6 KB block limit; the road tables (`rd_init`) do not depend on the track (section 4) |
| in-game editor (>= 2 MB) | **medium-high** (~35-45 h) | no engine obstacle found: data model is 6 lists, the viewer can be a flat top-down/profile screen; cost is UI. Free RAM above 1 MB is ample (section 5) |
| in-game saving | **high on STE/Mega STE >= 2 MB, not Falcon/TT** (~10 h) | HAGA is the byte-identical PP loader (md5 `b34607ed…` = Populous 2's); its three TOS-window routines are present in Moonshine's RAM (signature check [obs] section 7); Populous 2 / Hunter saved files through exactly this (proven there on STE 2 MB, Mega STE 4 MB, TT 4 MB, ACSI) |
| playtest ("drive it" from the selected segment) | **medium-high** (~10 h) | game's own setup sequence is re-runnable (`$fda2 $fde0 $ff3a $ffe4 $e1e4`); a fast-forward uses the game's own ring updaters; two risks: `rd_geom` standing-reuse cache, the finish/time rule (section 6.3) |
| track list / campaign | **medium** (~10 h) | the campaign is just `$102c` = 0..14 through six per-level pointer tables; user tracks = reuse slots or extend tables by RAM patch; sky/colour/minimap art are per-level assets outside the track block (section 8) |

Total about 80-100 agent-hours for a complete editor; **first demonstrable stage (about 8 h, no emulator-side code at all): "PC tool renders all 15 tracks to PNG, edits a curve in a text/JSON and writes a patched `FILES\MS2` that Hatari plays"** (this study already did the decode and one file edit; section 9 has the stages, the first at 4 MB is the overlay loader + F10 stub).

Main risks: (1) finish line / time limit rules are only partly located (section 1.5); (2) minimap and sky art are per-track assets, so an edited track keeps the old minimap picture; (3) HAGA-window saving is not available on Falcon (and the TT needs the PMMU alias care); (4) `rd_geom` standing reuse; (5) real hardware untested everywhere (Hatari only).

## 1. Where the track data is and what it is (question 1)

### 1.1 The game has 15 tracks, loaded from MS2 per race
`$102c` is the level index (0..14): the campaign loop `$7242-$7356` does `addq #1,$102c`, `cmpi #$f`; bit 7/15 of `$102c` = retry flags (`andi.w #$f` replays the level; `007310 / 007314` [disasm]). Level tables are indexed `$102c*4`.

The race setup `$7700-$7926` [disasm] calls the game's file service six times; every call is `jsr $d6fa` with `a0` = destination, `d1` = start sector, `d2` = sector count, taken from a pair of words behind a per-level pointer:

```
00777a: lea.l $291a.w,a0 ; move.w $102c.w,d0 ; add.w d0,d0 ; add.w d0,d0 ; movea.l (a0,d0.w),a0 ; ...
007792: lea.l $57890.l,a0 ; jsr $d6fa      ; table $291a  -> $57890   minimap header + nibble path  (1-2 sectors)
0077b6: lea.l $57ad0.l,a0 ; jsr $d6fa      ; table $28de  -> $57ad0   minimap bitmap                (6-10 sectors)
0077da: lea.l $58c00.l,a0 ; jsr $d6fa      ; table $28a2  -> $58c00   TRACK BLOCK                   (7-12 sectors)   <== the track
0077fe: lea.l $5a400.l,a0 ; jsr $d6fa      ; table $2866  -> $5a400   object graphics (negative sprite indices; then $8814 unpack)
007838: movea.w #$8000,d3 ; lea.l $60800.l,a0 ; jsr $d6fa   ; table $282a -> $60800  flagged load (d3=$8000, then $166d0/$18068; background/horizon art [INFERENCE])
007734: movea.l $1008.w,a0 ; jsr $d6fa     ; table $27ee  -> $1008 buffer  scenery/background graphics (31-35 sectors, then $8814/$da86 unpack)
```
Tables of (start, length) word pairs are chained: level N's records are consecutive sectors (`$7c+$1f=$9b`, `$9b+1=$9c`, `$9c+7=$a3`, `$a3+$c=$af`, ...), so the whole level asset set is one contiguous run in MS2.

`$d6fa`: `d1 < $320` -> `d0 = 0`, else `d1 -= $320`, `d0 = 4`, then `jmp $cac0` -> PP's stub `jmp $140`; the stub at `$198`: `tst.b d0 / beq / addi.w #$320,d1 / lsl.w #4,d1 / lsl.l #5,d1` = **byte offset = sector * 512** into the image file [disasm `$140-$1b2`]. So the **level data lies in `FILES\MS2` at offset = start sector * 512**, for all 15 levels (the `$320` split only selects the floppy drive in the original game; in PP's HD conversion it is undone).
[obs] level 0 (descriptor `$28a2[0]` = sector `$a3`, 12 sectors): `MS2[0x14600:+16]` = `0190 0000 0096 0002 008c fffe 00c8 0001` and RAM `$58c00` of the racing game = the same bytes (`m $58c00` in the dump; first 24/32 bytes found at `MS2 0x14600`, search script in `work/trackstudy/logs/`).
**Plain, not packed**: no PP-LZ/`Ice!` involved for the track block (the Ice!-packed pieces of MS2 are pictures; MS2 starts with `Ice!`). Structure check: all fifteen blocks parse into six streams that end exactly at a zero count, and every one of the four ring streams sums to **32768** units (`logs/decode_all.txt`, `sumcurve 32768 left 32768 right 32768 hill 32768` on all 15 lines). That is the strongest evidence the format is understood.

### 1.2 Track block layout (RAM `$58c00`, file `MS2 + start*512`)
Parsed by `fda2` (`lea.l $58c00.l,a0 / move.l a0,$23c0.w / bsr $fdcc` skips one list ...):
```
00fda2: lea.l $58c00.l,a0 ; move.l a0,$23c0.w     ; S0 curve   : pairs (count.w, delta.w), terminated by count 0
        bsr $fdcc ; move.l a0,$1bb0.w             ; S1 left    : pairs (count, target)
        bsr $fdcc ; move.l a0,$1bb4.w             ; S2 right   : pairs (count, target)
        bsr $fdcc ; move.l a0,$27da.w             ; S3 hill    : pairs (count, accel.w signed)
        bsr $fdcc ; move.l a0,$133a.w             ; S4 objects : [gap0] then (type, lateral, gap)... , gap 0 ends
        bsr $fdd6 ; move.l a0,$1342.w             ; S5 types   : 12-byte entries (ff00, kind, size, sprite, w4, w5)
```
(`fdcc`: `tst.w (a0)+ / beq / addq.l #2,a0`; `fdd6`: `tst.w (a0)+ / beq / addq.l #4,a0`, i.e. S4 is read as 3-word groups.)

| stream | pair = | consumer (runtime ring) | meaning (derivation) |
|---|---|---|---|
| S0 curve | (steps, delta) | `$ff3a` initial fill, `$ff76` per-frame advance -> ring `$1bbc` (1024 words) | `ring[i] = ring[i-1] + delta`: **delta = curvature, ring value c = road direction**. The geometry (`road.md` section 1.2) accumulates `X1[i] = sum (c[...]-c[ref]) >> 8` per depth slice, i.e. `c` is a lateral slope. |
| S1 left, S2 right | (steps, target) | `$fde0/$fe1c`, `$fe50` -> rings `$13b0`, `$17b0` (1024 bytes each) | the half-width byte slews 1 unit per step toward the target (`cmp d4,d3 / subq-addq #1,d3`, `$fe92-$fe9c`); `wL = byte*factor>>4`, `A = C + wR`, `B = C - wL` (`road.md` loop 3) => asymmetric widths, edge thickness comes from a static table |
| S3 hill | (steps, accel) | `$ffe4/$1003c` -> ring `$23c8` (1024 bytes) | `d3 += d2; d2 += d1` (32-bit): accel is the second derivative; `byte = d3>>16`, clamped `0..$7f` (`$10006-$10012`); starts at height 0 slope 0 |
| S4 objects | (type, lateral, gap to the NEXT object); first word = distance to the first | `$e1e4`, `$e218` (object spawner) -> 32 object slots `$2d80` (56 B each) | spawner `$e230-$e2ce`: `type = word-1` selects an S5 entry; `$1c(a1) = lateral` (-128..127, multiplied by the perspective factor in `$e38c`); the distance counter `$1346` is decremented by the speed `$130c` each frame |
| S5 types | 12-byte entry (`ff00`, kind 0-3, size 1-6, sprite index, w4, w5) | `$e25e-$e2b0` | kind `$c(a1)` 0 plain / 1,3 variants / 2 = two-sided (`cmpi.w #2,$c(a0)` `$e37c`: both profile bytes used, e.g. gates); sprite index >= 0 -> `$3d16e` table, negative -> `$5a402`-based per-level frames (`$e28a-$e298`); w4/w5 = collision/size words (`$2e/$30`) |

Units: one step = one ring position = one unit of the world distance counter `$5ff8` (`007b90: add.w d0,$5ff8.w`, `$130c` = speed = units per game pass, 10 at full speed: [obs] `130c 10` in the drive log). The camera sees the first **888 units** ahead (largest `T1` entry of `$4564` = 888, [obs]); the rings hold 1024.

### 1.3 Per-level numbers (all 15 decoded, `levels_summary.md`)
| lvl | MS2 offset | block B | race len | curve | left | right | hill | objects | types | free in block |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0x14600 | 6144 | 19472 | 106 | 35 | 32 | 248 | 416 | 131 | 376 |
| 1 | 0x21400 | 4608 | 19720 | 134 | 31 | 32 | 151 | 352 | 77 | 164 |
| 2 | 0x2da00 | 5120 | 19800 | 115 | 28 | 30 | 177 | 385 | 93 | 278 |
| 3 | 0x39600 | 4608 | 19000 | 117 | 24 | 31 | 153 | 379 | 63 | 262 |
| 4 | 0x44a00 | 4608 | 19375 | 118 | 35 | 33 | 181 | 427 | 37 | 118 |
| 5 | 0x50e00 | 4096 | 18000 | 119 | 30 | 37 | 165 | 372 | 31 | 72 |
| 6 | 0x5ce00 | 4096 | 18626 | 110 | 24 | 29 | 181 | 333 | 30 | 346 |
| 7 | 0x69200 | 4096 | 20000 | 114 | 28 | 25 | 187 | 374 | 34 | 12 |
| 8 | 0x75e00 | 3584 | 19000 | 88 | 26 | 19 | 81 | 359 | 28 | 222 |
| 9 | 0x81a00 | 4096 | 20000 | 91 | 21 | 24 | 149 | 371 | 32 | 330 |
| 10 | 0x8c400 | 4096 | 20000 | 75 | 30 | 31 | 168 | 369 | 42 | 146 |
| 11 | 0x97e00 | 4608 | 22000 | 105 | 28 | 35 | 176 | 443 | 40 | 78 |
| 12 | 0xa3200 | 4096 | 18500 | 37 | 17 | 16 | 146 | 367 | 53 | 378 |
| 13 | 0xad200 | 4608 | 22000 | 48 | 30 | 36 | 181 | 444 | 36 | 316 |
| 14 | 0xb7200 | 5120 | 23000 | 85 | 36 | 27 | 225 | 462 | 32 | 456 |

"race len" = word 0 of the minimap block `$57890` (same units: the progress `$5ff8 << 8 / $57890.w` in `$fbbc`, and the time-bar rate `$10d2 = ((100+lvl)*len/200) + (10-tbl[lvl])*200`, `$ee64-$ee8e` [disasm]). The object list ends at 19-22 k as well; the four ring streams run to 32768 (padding past the finish).

### 1.4 What is NOT in the track block
* **Colours** (road, grass, edge, stripes, car): the 24-word table behind `$1362[lvl]` (`$102ba...$1055a`, 48 B each) is part of the game image (MS1-loaded), copied to `$135a` by `$7890` (`road.md`, `integration.md`: 15 tables). Patchable only by a RAM patch.
* **Sky / horizon / background / scenery sprites**: per-level graphics records (`$27ee` 31-35 sectors -> `$1008`, `$282a` -> `$60800` with `d3=$8000`, `$2866` -> `$5a400` object frames) and per-level words `$6e26[lvl]` (`$7896-$789a`).
* **Minimap**: header+nibble path `$57890` (`len`, 498 steps for L0, per step a nibble: bits 2-3 = dx -1/+1 (`8`/`4`), bits 0-1 = dy -1/+1 (`2`/`1`), step length `hdr[2]` (straight) or `hdr[3]` (diagonal); `$f270-$f2fa` [disasm]; L0 header `19472 498 34 48 195 181`, [obs]) and the pre-drawn bitmap `$57ad0` (160x169 px: header words `160 169 90 15 7`). Both are per-level art; the nibble path only drives the position dot.
* **Opponents**: four car slots `$2ca0` driven by `$1182e`, which reads the curve ring (`lea $1bbc.w,a6`), not a path list **[INFERENCE: spawn rule not traced]**. The chase target is an object of sprite index `$21` (`$faea-$fb40`: scan of `$2d80` slots for `$6(a0) == $21`, `$1018 = $10d8/(d0-$32)`), so a **"police/rival" car is an ordinary S4 object of a type whose sprite is 33**; every level has such types (levels list `levels_summary`: e.g. L0 type 25).
* **Messages/speech events**: per-level pointer `$1286[lvl*2]` -> `$12a4` stream of (distance+`$320`, sign) read by `$fd64` (`cmp.w $5ff8.w`): in the game image, not in the block.
* **Checkpoints / finish**: the "checkpoint timer" is the time bar `$10ce/$10d2` (`$11792`: `$10ce += $10d2` per frame; high word >= `$ff` -> `$1226=5` -> `$1024` = -1 and `$102c |= $8000` = time-out restart, `$117a0-$117fc`). I did **not** locate a "distance >= len" test; the only reader of `len` besides the bar rate is the progress/comment code `$fbbc`. The race result path (`$1024` 1/2/3: `$fa2c`, `$10ce8-$10d14`) hinges on the `$21` object proximity. **Open: the exact win condition [INFERENCE]; to be traced in stage 2** (set `$5ff8` near `len` in a snapshot and watch `$1024`).

### 1.5 Do tracks load per race?
Yes: `$7700` runs on every race start and restart (time-out replay `$7306-$7318` loops to `$726c`, `rd_init` is called inside the same `$78f6` setup, `integration.md` 12.x). The track block is re-read from the cache/MS2 each time; so a redirected load takes effect on every restart without reboot.

## 2. Decoded track and limits (question 2)

### 2.1 Decoded form
`work/trackstudy/msrtrack.py` (decoder, ring expanders), `dump_table.py` (table), `render_tracks.py` (PIL plots; matplotlib is not installed here). Raw table of level 0 (390 lines, union of all stream breakpoints: seg, start, length, curve delta, c at start/end, hill accel, height, left/right target and current width, #objects): `level0_table.md`; all 15: `level*_table.md`. First rows:
```
| seg | start | len | curve delta | c(start) | c(end) | hill accel | height(start) | left tgt | right tgt | left w | right w | objects |
|   0 |     0 | 400 |           0 |        0 |      0 |          0 |             0 |       36 |        34 |     36 |      34 |       7 |
|   1 |   400 |  30 |           2 |        2 |     60 |          0 |             0 |       36 |        34 |     36 |      34 |       1 |
|   2 |   430 | 120 |           2 |       62 |    300 |          0 |             0 |       29 |        34 |     36 |      34 |       1 |
|   3 |   550 | 140 |          -2 |      298 |     20 |          0 |             0 |       29 |        34 |     29 |      34 |       3 |
```
Plots: `png/level00.png` ... `level14.png` (six panels: top-down path integrated from the curve data, the game's own minimap polyline decoded from `$57890`, curve value, elevation, half-widths, objects), `png/contact_sheet.png` (all 15 paths). Check of the format reading: the **curve value correlates with the minimap's heading** (correlation 0.39/0.44/0.56/0.81/0.25/0.68 on levels 0/1/2/5/9/14, `c(s)` = heading [obs numpy run]); the minimap is a hand-drawn art path so it is only a sanity check. **The top-down scale is arbitrary** (`theta = c/600`): the game is a pseudo-3D slice renderer, it has no world-space geometry, and the 32768-unit tail does not close a loop (net `sum c` != 0 on every level).

### 2.2 Fields and ranges (all 15 levels, `logs/ranges.txt`)
| field | range | notes |
|---|---|---|
| curve delta | -9 .. +10 per step | segment length 1 .. 14176 |
| curve value `c` | -4473 .. +8876 (16-bit word) | wraps harmlessly (word adds) |
| half-width target (left/right) | 10 .. 85 | slews 1/step, so a step change is a ramp |
| hill accel | -6000 .. +4000 | height byte 0..127 clamp; max real height 73; tiny values = rolling hills, +-3000 = sharp crest |
| object lateral | -128 .. 127 | signed word, in half-road units after the factor |
| object gap | 1 .. 351 | to the next object; first gap free |
| object type | 1 .. 131 (word-1 indexes S5) | up to 131 distinct 12-byte types on L0 |
| segments per list | max 248 (hill, L0 reports 248 pairs); curve 37..134 | |
| objects | 333 .. 462 per level | all within 18 k .. 23 k units |

### 2.3 Limits
* **Track length is fixed 32768 units per ring stream** (the sums); the *race* length is `$57890.w` (18000..23000). Streams longer than 32768 would just wrap the 16-bit counters [INFERENCE]; the loader stores no stream length, the terminator (count 0) is the only end marker. A custom track must make each ring stream add up to what the game reads before it ends (race length + 1024 look-ahead = `len + 888..1024` is enough; the originals pad to 32768).
* **Size**: stock buffer `$58c00-$5a3ff` = 6144 B and the next load (`$5a400`) starts right behind it; per-level free room inside the sector padding is 12..456 B (table above). Replaceable by redirecting two sites (section 4). Per-entry sizes: 4 B per pair, 6 B per object, 12 B per type. A realistic maximum with an 8 KB working copy: about 1,100 pairs + 500 objects + 130 types.
* **Object pool**: 32 scenery slots (`$2d80`, stride 56) + 4 cars; spawner skips an object when its slot is busy (`$e24e btst #0,4(a1)`), so density near a point is capped by the pool (visible depth 888 units).
* **Hill**: 1 byte/unit, 0..127 (max seen 73).
* **RAM per track**: ring tables 1024x(2+1+1+1) = 5 KB; spawned objects 36 x 56 = 2 KB.

## 3. Runtime proof of one edit (question 3)
Edit: level 0, curve stream pair 0 `(count 400, delta 0)` -> delta `+1`. **File location: `FILES\MS2` offset `0x14602` (the delta word of pair 0; the count word `0190` is at `0x14600`), original bytes `00 00`, new `00 01`** (`MS2[0x14600:0x14610]` = `0190 0000 0096 0002 008c fffe 00c8 0001`; edited file `0190 0001 0096 0002 ...`).

Check: `cmp -l originals/MOONSHR/FILES/MS2 work/trackstudy/game_edit1/FILES/MS2` printed exactly one line, `83460   0   1` (1-based byte 83460 = offset `0x14603`, the low byte of that word) [obs]. Everything else in the folder is the unmodified `originals/MOONSHR` (copied; `originals/` untouched).

Run: cold boot STE 1 MB, `tools/msr.py` harness (`boot_to_race`, then SPACE until the race loop is set up: note `boot_to_race()` reports True on the title screen, where `$1021 = 2` already holds, so my `run_race.py` presses SPACE until `$23c0 != 0 and $100e > 30`), standing start (grid), `m` dumps, screenshots. Baseline = same boot of the untouched `originals/MOONSHR`.

```
edited : > m $1bbc 64
00001BBC: 00 01 00 02 00 03 00 04 00 05 00 06 00 07 00 08  ........       <- curve ring = 1,2,3,... (delta +1)
baseline: > m $1bbc 64
00001BBC: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
both:  m $1bb0 8 -> 00 05 8d b2 00 05 8e 3c   m $23c0 4 -> 00 05 8c 14   (stream pointers inside the RAM block, equal)
```
Screens (`work/trackstudy/png/before_after_grid.png`, left original, right edited; raw shots `shots/base_grid*.png`, `shots/edit1_grid*.png`; difference map `png/ab_grid2.png`): the standing start frame of the edited game shows the far road bending the other way and every roadside sprite following the new curve. Pixel count (game area, Hatari screenshot of the 640x400 screen):
```
rows 58-270 (sky, HUD, clouds, minimap): 0 differing pixels   (both grid0 and grid2)
rows 270-458 (road, grass, sprites):     21832 (grid0) / 21468 (grid2) differing pixels
control: same build, two grid frames of ONE run differ by 14,208 / 14,480 px only in rows 92-329 (clock needle, clouds) - never in the road rows
```
The same run driven with up held (`$6105 = 1` via `Moonshine.drive`): `5ff8` 718 / 1568 / 2408 / 3127 (edited) vs 728 / 1588 / 2428 / 3135 (baseline) at the same wall times; speed `130c = 10`; the edit sits only in units 0-399, so after about 400 units the two games are on identical road again (the later drive frames differ only by the offset between the two runs' positions). `[INFERENCE]` that position-matched frames are identical; not measured.

**What this proves**: (1) the file bytes at `MS2 + sector*512` are the live track; (2) the game's own loader reads the edited file with no other change (PP's HAGA serves `MS2` unmodified, no checksum on the track); (3) the stream value reaches the road ring `$1bbc` as predicted by the decoder (ring = running sum of delta) and changes the picture. So a PC tool that writes `MS2` (or an overlay file the loader redirects to) works.

## 4. How the game consumes the track: what an edit needs (feeds section 5)
* Setup order `$78cc-$7908` [disasm]: `jsr $fda2` (stream pointers) `$164c4 $164ea $163ba $16524 $16404 $16428` (**static tables built from constants only**, `road.md` section 1.2: they contain no read of the track data nor `$102c`) `$fde0` (fills the two width rings from S1/S2, 1024 each) `$ff3a` (curve ring) `$ffe4` (hill ring) `$e1e4` (clears the 32 object slots, loads `$1346` and advances 1023 units with `$130c = $3ff`).
* The race loop updaters `$fe50 $ff76 $1003c` (`$7aec-$7af8`) consume `$130c` steps per pass out of the streams (`dbeq d0` loops; each starts with `subq #1,d0 / bmi rts`: no work while standing) - the rings are a sliding 1024-unit window; **editing the stream ahead of `$23c0/$1bb0/$1bb4/$27da` takes effect when the window reaches it** (proof: my edit sat in the window already and needed the setup).
* **Re-init after an edit**: re-running `$fda2 $fde0 $ff3a $ffe4 $e1e4` (the game's own setup minus the static tables) is enough; `rd_geom`/`rd_draw`/`rd_init` need nothing: `rd_init`'s tables are keyed by `$1316` and the colour table `$135a`, `road.md` section 10 / `integration.md` (A/B IDENTICAL on tracks 5, 12 restarted from the same code). **One trap**: `rd_geom`'s standing reuse (33 state words as key, output `$4724-$4f77` copied back instead of recomputed when `$130c == 0`, `road.md` 6.1) assumes the rings change only through the three updaters; an editor that rewrites the rings while standing must invalidate it (poke the saved key/`RDG1` magic, or run a frame with `$130c > 0`) [INFERENCE: not run].
* Only two code addresses name the block (`xref 58c00`: `$77da`, `$fda2`) - verified with `m68dis.py --xref 58c00`.

## 5. Where the editor lives above 1 MB (Main's question 1)
Machine facts [obs, `$42e`/`$436`/`$2dc` from the dumps]: 1 MB STE: `phystop $42e = $100000`, `memtop $436 = $f8000` (HAGA moved it to phystop-$8000), `$2dc` (PP stub's pointer to HAGA) = `$f8000`; the same three values are valid at the hook instant (`ram_hook_1024.bin`: `$42e = $100000`, `$436 = $f8000`) and in the race. 4 MB STE (stock snapshot `ste4m_race_start.sav`, `work/trackstudy/ram_ste4m_stock_race.bin`): `$42e = $400000`, `$436 = $3f8000`, `$2dc = $3f8000`; HAGA signatures present there too.

Non-zero RAM at 4 MB in that stock snapshot (`msrdump`: zero runs `$0c7900-$1f5200`, `$1f8500-$1ffd00`, `$1ffe00-$3d8900`, `$3fb700-$400000`; non-zero outside the game area: `$1f5200-$1f8500` (12 KB, origin not identified), `$3dc500-$3dde00`, `$3e3800-$3e8700`, `$3ec000-$3ed900`, `$3f3300-$3f7d00` (these four = the TOS-state copy HAGA exchanges, [INFERENCE: sparse low-RAM image]), `$3f7e00-$3fb500` HAGA). In that **stock** run the HAGA whole-image mode holds MS1 at `$81000-$c6f2b` (280 KB); with `pp_bigram_cache` (default `yes`; `delivery.md` section 5) the chunk cache goes back to `$81000-$B1D40` like 1 MB.

Free map for the editor on an STE/Mega STE with `pp_bigram_cache` [stock-snapshot facts + shipped-patch layout; **the patched build was not re-dumped at 4 MB, see section 7.5**]:
| range | use | size |
|---|---|---|
| `$0B2700-$0C16FF` | existing payload (<= 61 KB cap) and `rd_*` tables `$C0000-$D7FFF` (`; ram:`) | as released, untouched |
| `$100000-$1F4FFF` | **editor image + data at 2 MB and 4 MB** | ~1 MB |
| `$1F5200-$1F8500` | avoid (12 KB, unidentified; HAGA base at 2 MB is `$1F8000`) | |
| `$200000-$3DC4FF` | additional editor data **at 4 MB only** (undo, decoded rings, 15-track working set) | ~1.9 MB |
| `$3DC500-$3FFFFF` | TOS copy + HAGA: never | |
At 2 MB: HAGA at `$1F8000`, TOS copy just below it **[INFERENCE: layout scaled from 4 MB]**, so stay below `$1D0000`; the editor needs far less (see budget). TT/Falcon: see 5.3.

### 5.1 Budget (estimates, not measured)
decoder/expanders: 64 KB (32768-word curve array + 3 x 32 KB byte arrays only if the editor expands per unit; a segment-list editor needs about 8 KB per track), working set of all 15 tracks 15 x 8 = 120 KB, undo ring 64 KB, editor code 32-48 KB, screens (own 32 KB buffers; the STE shifter accepts any ST-RAM address) 64 KB. **Total about 300-400 KB: fits the 1 MB at `$100000` even on a 2 MB machine.**

### 5.2 Hazards
* HAGA's 4 MB whole-image mode (stock) puts MS1/MS2 caches in `$81000-$13D7FF`: solved by the default `pp_bigram_cache`; the editor must **require** it (the tool already refuses `rd_*` without it).
* HAGA's TOS-window swap exchanges low RAM only (`$8..$FA28` STE+Hatari drive, `$8..$1B6C8` ACSI+HDDRIVER, from Populous 2's measurements): everything of the editor above `$100000` is outside the swapped range; the **save routine itself must run above the swapped range** (Pop2 puts part B into HAGA's top region HAGA+`$3900`).
* The payload cap `IMG_MAX_LEN = $F000`: the editor does not fit there (default set 47,360 B of 61,440): **do not put the editor into the RUNME payload**; see 6.

### 5.3 TT / Falcon / Mega STE
Pop2 (same HAGA): STE 2 MB, Mega STE 4 MB (TOS 2.06), TT 4 MB (PMMU remap: game RAM at `+$200000` during TOS; nothing may live in the first MB, data goes through a bounce buffer) saves worked; **Falcon refused** (machine type 4 swaps differently, the Falcon call died with bus errors). Practical scope: **STE and Mega STE with >= 2 MB**; TT only after a separate study (its alias window `$200000-$2FFFFF` would collide with an editor placed at `$200000`: use `$100000-$1FFFFF` there); Falcon: no editor save (the in-game editor itself could still run [INFERENCE]).

## 6. Conditional delivery on RAM size (Main's question 2)
### 6.1 What exists
The trampoline (`patches/core.s`) runs at the hook instant `$b204e` in supervisor mode, verifies and applies a site table, `jmp $1000.w`. `$42e` (phystop) is intact there [obs above], also `$2dc` (HAGA base).
### 6.2 Design (two payload sets, one tiny always-present stub)
1. **Always shipped** (default set, tiny, <= 1 KB, uses part of the 14 KB headroom): `ed_gate` = a site at the game's key/title or race-setup code + a one-instruction-test blob: `cmpi.l #$200000,$42e.w / bcs.s inert`. At 1 MB the gate returns to the stock code untouched (the sites it patches are plain `jsr`s into the blob and the blob replays the displaced instruction), so the 1 MB game **behaves as released** (inert = identical bytes executed apart from the extra `jsr`/`rts`; every A/B gate of the release repeats trivially) - or, even cleaner,
2. **trampoline table 2**: `core.s` gets a second site table `TABLE2` applied only when `$42e >= $200000` (one `cmpi.l / bcs` before pass 1; the tool marks patches `; ram: min 2MB`); then at 1 MB **no editor byte exists in RAM at all** (tool change in `msrpatch.py`, the same verify-then-apply loop).
3. **Editor image** = a separate file `FILES\MSEDIT.OVL` (code + UI data), **loaded lazily on the first F10** into `$100000` via the HAGA TOS window (6.3) - not at boot, so a missing file or a failed read changes nothing at boot. HAGA can read arbitrary files: `Fopen/Fread` through the same window as the save (Pop2 `read` = `Fopen/Fseek/Fread/Fclose`).
4. Track data = `FILES\MSTRACKS.TRK` (15 slots x up to 8 KB, header with magic/version/CRC), read on the first F10 and (if present) at each race setup by the redirect hook (section 4: the two sites `$77da`, `$fda2`), so **user tracks also play without opening the editor** at >= 2 MB; at 1 MB the redirect is not installed and the stock tracks load.
Machine test: `$42e >= $200000` and the HAGA machine-type byte at `$2dc` base `+$83` (STE = 2 here; Pop2 refused type 4 = Falcon) - the trampoline already has the 68000/020 test.
### 6.3 Why the file is loaded through the HAGA window, not by RUNME
RUNME's data segment limit (`delivery.md` section 6: refuses when bss start + `$8000` reaches `$38270` on 1 MB, `$14e790` at 4 MB) makes an in-RUNME image a 1 MB problem; and the RUNME is the same file at every RAM size. A separate file avoids it and keeps the release RUNME byte-identical for 1 MB.

## 7. In-game saving: the HAGA TOS window (Main's question 3)
### 7.1 Does HAGA/RUNME keep an equivalent of Gamex's saved TOS state?
**Yes, same idea, different plumbing.** Nebulus (Gamex): the TOS copy is addressed by the long at `$ffd80` (`$c0108` on 1 MB, `$102008` on 4 MB) and the excursion swaps `$8..$8+(n+1)*48` of low RAM with it. PP's **HAGA** (the resident loader, copied verbatim to `phystop-$8000`) **snapshots TOS's state when it is loaded** and every disk call is wrapped in: all MFP enables off, fade to grey, **exchange of low RAM with that TOS state**, private stack and usp, and the reverse afterwards (Populous 2 `pop2_save.s` header, evidence from disassembling HAGA: routines `HAGA+$17be` (save and clear MFP enables), `+$1166` (fade + swap TOS in), `+$1372` (swap out + fade back)). HAGA also writes files itself (statesave key: `Fcreate [0x1e46]`, `Fwrite [0x2a58]`, Pop2 `disks.md`; Moonshine's own README.TXT lists "savestates"). Populous 2 and Hunter prove that **a game-side blob can call GEMDOS (`Fcreate/Fwrite/Fclose/Dfree`) inside that window**.
### 7.2 Evidence in Moonshine's RAM (this study) [obs]
```
HAGA md5 originals/MOONSHR/HAGA = originals/POPUL2/HAGA = b34607ed9baecc5982a5a01ecaf5a3dd   (identical file)
$2dc (PP stub's pointer, Moonshine) = $000f8000 (1 MB)   |   $3f8000 (4 MB snapshot)
HAGA+$17be = $4dfa1c04  OK   HAGA+$1166 = $45fa0e1e  OK   HAGA+$1372 = $123aed0f  OK    (1 MB race dump AND 4 MB snapshot)
HAGA+$83 (machine type) = 2 (STE)   HAGA+$af (no-swap flag) = 0
HAGA+$8 = $0fc4 ; HAGA+$c = $1962   (PP's read entry and its init entry, used by the stub at $140)
```
Pop2 reads the HAGA base from `$328`; **Moonshine's PP stub keeps it at `$2dc`** (`movea.l $2dc(pc),a1 / move.w $8(a1),d1 / jsr (a1,d1.w)` at `$1f6/$1fe` and `$23a/$242`, [disasm]); `$328` in a race holds game data. So the port must read `$2dc` (or compute `phystop-$8000` from `$42e`, both valid).
### 7.3 What a Moonshine save needs
Port Pop2's part B (about `$700` code + `$d00` data + 8 KB bounce, position independent, installed into HAGA's top region at HAGA+`$3900` on first use; free in Moonshine's HAGA as in Pop2's: same file) and replace Pop2's `save/read/dir` front end with: `Fcreate+Fwrite(<=8 KB chunks)+Fclose+Dfree` for `FILES\MSTRACKS.TRK` (~120 KB) and `Fopen+Fread` for loading/the overlay. Same calls as Pop2's proven 56,690-byte saves; durability needs the `Dfree` after `Fclose` (Hunter/Pop2: a kill after the save loses the file without it, 6/6 clean with it). **Save without any GEMDOS: not available**: Moonshine's own file layer `$d6fa -> $140` is read-only (a read-at-offset stub; Pop2 reached the same conclusion for the same stub).
### 7.4 Costs/risks: interrupts masked for ~0.5-1 s during a call (Nebulus measured the same), IKBD state to drain afterwards (Pop2: `clr.b $2022`; Moonshine's handler `$cfb4` stores the joystick to `$6105` and the key to `$60ff`: check the parser state after a call), HDDRIVER/ACSI variants swap a larger low range, Falcon refused; real hardware untested for the whole HAGA-window family.
### 7.5 What this study could not run
**A cold boot of the *patched* v1.0 HD build (`build/hd`) at STE 4 MB did not reach the race in my harness**: both `run_dump4m.py` (my `boot_to_race` + SPACE loop) and the shipped `tools/msr_boot_test.py --mem 4096 --game build/hd` stayed in the intro/title states (`$1021 = 0`, `$100e` cycling 0..680) for 400 s (`work/trackstudy/logs/run_hd4m.txt`, `boot_hd4m.txt`). The release notes (`release_notes_draft.md` line 54) report a 4 MB cold boot of the final set into the race, so this is **[INFERENCE] a timing problem of the SPACE navigation recipe with the patched pacing, not a game/RAM fault** (the unpatched `originals/MOONSHR` reached the race at 1 MB with the same recipe, `logs/run_base.txt`); not diagnosed here (out of scope: it is the release's frozen state). Consequence: the 4 MB free-RAM table in section 5 rests on the **stock** 4 MB snapshot (`ste4m_race_start.sav`) plus the documented patched layout (`delivery.md` section 5: with `pp_bigram_cache` the cache is back at `$81000-$B1D40`), not on a fresh dump of the patched game. **Stage 2 must start with that dump** (cold boot by loading the game with a poked `$102c`/snapshot of a patched 4 MB run, `msrdump`) before placing code at `$100000`.

## 8. Editor UI sketch for a pseudo-3D racer (Main's question 4)
Own screen and palette, VBL ISR only (the game's Timer B palette split stopped, as Nebulus did; game state untouched); input = the game's own IKBD hooks: joystick byte `$6105` (bit0 up, 1 down, 2 left, 3 right, 7 fire) and the key scancode `$60ff` (`$3b` = F1 already read at `$7988`; F10 = `$44`). Fonts: the game's message font. All on the 320x200 low-res screen.
```
+--------------------------------------------------------------+
| TRACK 03  len 19000  seg 17/117  c=+210  h=12  wL=29 wR=34   |  header: slot, race length, cursor segment's numbers
|                                                              |
|   top-down path (curve integrated, scale = arbitrary)        |  120 px high map: polyline coloured by elevation,
|      .-'''-.        S = start  F = len marker                |  cursor = blinking dot, objects = small ticks,
|    .'       '.__     > = cursor, ticks = every 1000 units    |  viewport scrolls; zoom 1/2/4
|   S            ''-F                                          |
|--------------------------------------------------------------|
| elevation strip (0..127) | width strip L/R | object strip      |  3 x 24 px profile strips along the same distance axis
|--------------------------------------------------------------|
| [curve][hill][width L][width R][objects][len][test][save]    |  menu row: fire = open, left/right = field, up/down = value
+--------------------------------------------------------------+
```
* **Cursor** = position along the distance axis (units); left/right moves by one segment boundary (stream pair), fire+left/right moves by 10/100 units; up/down on a field changes the value of the segment under the cursor (curve delta -9..10, hill accel, width targets 10..85, object lateral -128..127, type); insert/split at the cursor and delete/merge are menu items.
* **Per-segment edit menu**: length (count), curve delta, hill accel, left/right width target; **objects list**: type picker (the 131 12-byte S5 entries of the level with a thumbnail through the game's own sprite blitter), lateral, gap; checks: `sum counts >= len + 1024`, the four ring streams end at the same unit, <= object slots, buffer limit.
* **Live preview**: not needed for the map; a "view" key runs the road renderer from the cursor (set rings by fast-forward, draw one frame with the game's own `$100b4/$17c42`) as a 3D preview.
* **Playtest "drive it"**: write the working copy to the overlay slot, redirect (section 4), re-run `$fda2 $fde0 $ff3a $ffe4 $e1e4`, fast-forward the rings to the cursor unit by calling the updaters (`$fe50 $ff76 $1003c` with `$130c = N`, up to 1023 per call; and the object spawner `$e218` likewise, as `$e1e4` does), set `$5ff8 = unit`, `$10ce` as the time bar for that point, invalidate `rd_geom` standing reuse, **then enter the game's loop `$7a88`**; the F-key returns to the editor. Cost of the fast-forward 3 M cycles (a few seconds at 8 MHz) per 20 k units [INFERENCE: arithmetic on `road.md` loop costs, not measured]. Restart by time-out replays `$102c` = same slot.
* **Track list / campaign** (section 1.1): the campaign is the linear `$102c` order; `$27ee/$291a/$28de/$28a2/$2866/$282a` are 15-entry pointer tables, so a track set = a permutation or replacement of slots: the TRK file header holds `order[15]` and the redirect hook maps `$102c` -> slot. Adding a 16th track needs the `cmpi #$f` at `$7322/$75e8` and `$ef46` ... touched (final-screen logic): **[INFERENCE]**, defer. Per-track art (sky/scenery, colours, minimap) stays that of the host level: the editor offers "base level" (palette and scenery of level N) + custom track data; a minimap regenerated from the integrated path (nibble codes) is a stage-3 item, otherwise the dot walks on the old picture.
* **The Nebulus site idea (user-made tracks as files)**: a `MSTRACKS.TRK` per user is a ~120 KB (or 8 KB per track) file with a text-exportable form (the decoder's table is already the interchange: `level*_table.md` / JSON); upload/download of such files needs no code change in the game.

## 9. Staged plan (first demonstrable at 4 MB)
| stage | what | demonstrable result | agent-hours |
|---|---|---|---:|
| 1 | PC tool: decode all 15 -> PNG/JSON, validate, `set`-style edit, write patched `FILES\MS2` copy (same sector budget: 12..456 free bytes/track, auto-check) | `tools/msrtrack.py render|edit|patch`: Hatari plays an edited MS2 (this study already did the decode and one edit: section 3) | 8 |
| 2 | **4 MB gate + overlay loader**: trampoline TABLE2 (>= 2 MB only), `ed_redirect` (`$77da`/`$fda2` -> `MSTRACKS.TRK` working copy at `$100000`, lazy HAGA-window Fread), `ed_boot` stub, finish/win rule located, `rd_geom` reuse invalidation | **at 4 MB the edited track from a file plays; at 1 MB the build is byte-identical to the release** (A/B gate) | 14 |
| 3 | in-game viewer: F10 screen with top-down + profile strips, scrolling cursor, no editing yet; reads the overlay track | map of the track on the ST screen (same as the PC PNG) | 12 |
| 4 | editing UI: segment menu, objects list, undo, validation; working copy only (not saved) | edit a curve in game, "view" shows it | 20 |
| 5 | playtest from the cursor, time-out/restart, return to the editor | drive the edited segment | 10 |
| 6 | in-game save (HAGA-window port of Pop2 part B) of `MSTRACKS.TRK`, `Dfree`; kill tests | save, reboot, track still there | 10 |
| 7 | track list/campaign (`order[15]`), regenerated minimap path, packaging, 1 MB regression + 2 MB/4 MB/Mega STE cold boots | zip | 12 |
Total about 86 agent-hours; stages 1-2 (about 22 h) already give a "user-made tracks as files" feature at 4 MB without any editor UI.

## 10. Reproduce
```
python3 work/trackstudy/msrtrack.py                      # all 15 levels: streams, sums, object counts
python3 work/trackstudy/dump_table.py 0                  # segment table of a level
python3 work/trackstudy/render_tracks.py                 # png/level*.png + contact_sheet.png (PIL)
python3 work/trackstudy/run_race.py $PWD/work/trackstudy/game_edit1 edit1   # edited MS2, cold boot, standing + driving shots, ring dump
python3 work/trackstudy/run_race.py originals/MOONSHR base                  # baseline
python3 work/trackstudy/cmp_shots.py shots/base_grid2.png shots/edit1_grid2.png out.png
```
