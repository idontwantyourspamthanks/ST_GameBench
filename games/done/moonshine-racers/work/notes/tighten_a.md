# Moonshine Racers: tighten wave A (horizon strip, speech, interrupt costs)

Machine for every number: Hatari 2.6.1, STE TOS 1.62, 1 MB, 8 MHz, 50 Hz; cycles per pass = loop top `$796a` -> flip `$d1ca`, interrupts included, tick patches OFF (`work/hud/build/cyc3.py` recipe = `work/tightA/cyc.py`: scenes `race_start` driving, `race_grid` standing; "speech" = `$11ab != 0` at the end of the pass; deltas are taken on the SAME pass keys `$100e`). 1 VBL = 160,256 cycles. Reference R = the current default set (hd_*, rd_* (new addresses), mr_edge, mt_*, mx_*; for the cycle runs without mt_/mx_). Raw files: `work/tightA/res/`, scripts `work/tightA/`. `[INFERENCE]` marks what no tool output proves. Nothing here changes a shipped patch: every new patch is `default: no`, **no default was flipped**.

## 0. Result in one page

New patches (all `patches/ta_*.s`, `default: no`, blob/data inside `$BE000-$BEFFF`, `verify` ALL OK in the private tool copy `work/tightA/msrpatch_priv.py`, resynced from `tools/msrpatch.py` after MSRMegaSTE's RAM-map change):

| patch | site | what | gain (driving, cycles/pass, matched passes) | pixels / state |
|---|---|---|---|---|
| `ta_erase` | `$1209c` (`jsr $1242c` in the ticker's box restore) | the 49-row box restore as two `movem.l` per row; owner of the face-shadow data `$BEF00` | each of the 2 erase passes per message **-24.2 k / -24.4 k / -21.6 k / -26.1 k** (measured on 4 passes); 0.0 on other passes | identical |
| `ta_init` | `$edea` (race init) | **replaces `hd_init`** (conflicts): same work (clears both `painted` bytes) + forgets the face shadows | 0 | identical |
| `ta_face` | `$f994` (inside the face `$f90c`) | draws the face only if the sprite index differs from what that buffer shows | **-4.4 k per speech pass** on average (38 % of the face draws skipped: -12 k on those) | identical |
| `ta_facestat` | same site (conflicts `ta_face`) | face drawn once per message and buffer (mouth frozen) | **-6.6 k per speech pass** on average (a further -2.2 k vs ta_face) | **VISIBLE**: mouth/eye pixels only, section 3.3 |
| `ta_glyph` | `$14fd4` (ticker glyph kernel) | MOVEP-based rewrite | -1.2 k per speech pass average (-1.7 k on typing passes) | identical |
| `ta_ymw` | `$8e2c` (YM player write loop) | skip register writes whose value did not change | -1.4 k | identical chip state |
| `ta_rb` | `$d5e6` (end of the VBL raster-list builder) | drops Timer B interrupts that only re-write the sky colour it already has (4 of 8 per VBL on track 1) | -3.0 k | identical |
| `ta_rb0` (requires `ta_rb`) | `$d57c` | skips the stock list builder on a cache hit | a further -1.5 k (rb + rb0 = -4.5 k) | identical |
| `ta_nomouse` | `$d486` | no IKBD mouse query (command `$0D` + 6 ACIA interrupts) while `$1021 == 2` | **-8.3 k** | identical; **behaviour risk, section 4.4** |

Cumulative (matched passes), pixel-identical set = erase+init+face+glyph+rb+rb0+ymw+nomouse: **driving -15.6 k no speech (3.065 -> 2.968 VBL/pass), -19.5 k with speech (3.228 -> 3.105); standing -13.5 k / -16.4 k (2.589 -> 2.505, 2.608 -> 2.506)**. With `ta_facestat` instead of `ta_face` another -1 .. -2 k with speech. Without the risky `ta_nomouse` the set gives -7.3 k / -11.2 k driving. So these three items do NOT reach the 2.7 VBL target by themselves (2.97 / 3.10 VBL); they are worth about 0.10 / 0.12 VBL.

Item (1), the horizon strip skip: **NOT WORTH BUILDING: 6.8 k per pass upper bound (0.04 VBL), CLOSED** (section 2). The user's idea "speech in the top bar" was NOT built; its estimate is in section 3.5.

## 1. Gates run (all raw outputs below)

1. `msrpatch_priv.py verify` ALL OK with all `ta_*` files present (sites checked against the 1 MB STE dumps and the floppy RAM dump).
2. Exact 68000 model (Unicorn, `work/extrap/emu.py` via `work/hud/build/emuhud.py`), `work/tightA/gate_emu.py`: reference live image vs candidate live image, per pass the whole RAM below `$70000` and both complete 32,000-byte screen buffers (not a masked rectangle: stricter than `tools/msrmask.py`), 15 levels were available, 4 used x 2 inputs x 160 passes, with 3 extra frames per tick (`X_TEST`): all frames, main and extra. Negative controls on the three pixel routines.
3. Unit tests in the model: YM writer (chip register file + RAM, random sound triggers), glyph kernel (all 256 colour bytes x 4 byte parities), raster list (random inputs, decoded to colour-per-line and palette-switch line).
4. Hatari per-pass game state at `$7b86` (`work/tightA/exp_state_ta.py`, `cmpstate_ta.py`; the `work/hud/build/exp_state_hd.py` recipe: `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6 $1bb0 $23bc $27c8 $3500 $dafe $6100-$6117`, 7,3xx bytes per pass), tick ON and OFF, race_start (driving, `$6105` held) and race_drive (time-out + restart inside), plus extras at 16 and 32 MHz.
5. Hatari A/B pixels: full buffers, flips 10/40/90/150 after the live apply, 4 scenes; section 5.3 (first run, whose face control did not fire) and **5.3b (sensitive controls on the SAME captures, the gate of record)**.
6. Hatari raster trace (`--trace video_color`): the colour-15 and palette-B writes per scanline.
7. Cycles per pass (tick OFF) per item and cumulative, both scenes; interrupt costs per VBL by the Hatari CPU profile.
8. Real IKBD joystick through host keys (for `ta_nomouse`); cold boots STE 1 MB and 4 MB; 5-minute play with time-out and restart.

Bug found by gate 4 (kept for the record): the first `ta_init` called the `hd_init` blob `$BB700`, which does not exist when `hd_init` is not selected: the game crashed at the first race restart (bisection `res/bisect.log`: only the `ta_init` builds crashed). The emulator gates cannot see this (they never reach a restart: the model stops at the time-out). Fixed: `ta_init` now clears the two `painted` bytes itself. Everything below was measured after the fix.

```
== ta_init,ta_erase
CRASH detected
hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geo race_drive hits 85 bytes/hit 7322
== ta_init,ta_erase,ta_face,ta_glyph
CRASH detected
hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geo race_drive hits 85 bytes/hit 7322
== ta_ymw
hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geo race_drive hits 137 bytes/hit 7322
== ta_rb
hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geo race_drive hits 137 bytes/hit 7322
== ta_nomouse
hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geo race_drive hits 138 bytes/hit 7322
DONEB
```
(that bisect ran with the broken `ta_init`: "CRASH detected" lines; the rows without `ta_init` completed.)

## 2. Item 1: horizon strip skip (`$18318`)

What the strip is (disassembly `work/hud/dis/all_7000_19000.txt` line 24027 ff.): `$12f0` = destination (end of the road area in the back buffer), `$12f6` rows skipped at the top of the 48-row source, `$12f8` the scroll (`d2 & $f0` column, `d2 & $c` one of the four pre-shifted copies), `$1304` the fill rows (`move.l d0.. = $ffffffff` blocks `$18378`). Source copies `$60800/$62600/$64400/$66200` (48 rows x 160 B each) are static between level inits. The copy is `movem.l (a2),d0-d6/a3-a5` / `movem.l d0-d6/a3-a5,-(a0)`: 8 + 8 cycles per longword = the bus floor, 4.5 cycles/byte, ~720 cycles per row, 35-40 k for 48-55 rows. A blitter copy costs the same (16 cycles per longword): no gain there.

Output key per buffer = (`$12f0`, `$12f6`, `$12f8 & $fc`, `$1304`). The output of the stage for THIS buffer is unchanged iff the key equals the key of the last pass into this buffer AND nothing overpainted rows 65-119 since. Measured in the model (`work/tightA/hz_exp.py`, current default build, 15 levels x {up, zig} x 130 passes, raw `hz_exp_all.json`):

* key identical to the previous pass into the same buffer: **29.8 % of the passes** (3,900 passes; 42 % level 0, 28 % level 1, ... 8-9 % on levels 6 and 8, 56 % on level 14); it changes with the horizon scroll (`$12f8`, curves: 962 of 3,900 consecutive-pass changes), the hill (`$12f6` 913, `$1304` 345).
* overpainted since: the object stage `e406` draws sprites over rows 104-119 (and, near the horizon, as high as row 73: minimum measured), HUD/face/ticker only paint rows 0-64, the road repaint rows 120-199. So even when the key matches, the rows from the TOP of last pass's sprite footprint to row 119 must be restored: measured mean first dirty row 96.6 on the key-identical passes.
* ideal saving = rows above the footprint x 720 cycles on the key-identical passes: **6.8 k per pass on average** (per level 1.6 k .. 14.8 k):

| level | passes (up+zig) | key identical to 2 passes ago (same buffer) | ideal saving, cycles/pass |
|---|---:|---:|---:|
| 0 | 260 | 108 (42 %) | 10988 |
| 1 | 260 | 72 (28 %) | 4477 |
| 2 | 260 | 76 (29 %) | 4037 |
| 3 | 260 | 87 (33 %) | 4466 |
| 4 | 260 | 104 (40 %) | 10755 |
| 5 | 260 | 74 (28 %) | 8687 |
| 6 | 260 | 24 (9 %) | 1561 |
| 7 | 260 | 68 (26 %) | 4572 |
| 8 | 260 | 22 (8 %) | 2353 |
| 9 | 260 | 133 (51 %) | 14834 |
| 10 | 260 | 47 (18 %) | 3184 |
| 11 | 260 | 74 (28 %) | 7823 |
| 12 | 260 | 62 (24 %) | 4901 |
| 13 | 260 | 66 (25 %) | 7368 |
| 14 | 260 | 145 (56 %) | 11711 |

**Not worth building (6.8 k upper bound; CLOSED).** An exact version needs the footprint of the previous pass, and there is no cheap exact source for it: all sprite kernels store the row offset to `$100c` at ~60 distinct instructions (`move.w d2,$100c.l` = `33c2 0000100c` at `$e9ea $eb98 $ec8c $11d6c $12af8 ... $161f2` and more, `grep 100c` in `all_7000_19000.txt`), the type 0/1/2/3 and the two player slots go through 15 different dispatch sites (`sprites.md` section 1), and tb_/tc_ patch parts of exactly that path, so a hook of mine would be silently bypassed. The data above is the upper bound; jitter would be 0 on the key-identical passes and +full strip on the others (a 6.8 k mean over a 40 k stage). A fixed row threshold (restore rows >= 73) saves only 8 rows on 30 % of the passes (about 1.7 k). Uniform sky rows in the source (rows 0-8 of 48 on levels 3/6/12, none on 2/4/8/13) would save about 370 cycles per row by filling instead of copying: under 3 k, not built.

## 3. Item 2: speech

### 3.1 What was found (all re-verified in disassembly)
* Ticker `$11ef0`: state machine `$11ab/$11b1` untouched by every patch here (the patches only replace drawing).
* Face `$f90c`: during typing (`$11ab == 1`) the sprite index at `$f994` follows the face RNG (the mouth), while held (`$11ab >= 2`) it is constant (`$f988`..`$f992`: base + table byte). The routine draws a masked sprite on a persistent sky, so drawing the same index again over a buffer that already shows it is idempotent.
* The box restore `$12086 -> $1242c` fills 49 rows x 192 pixels (rows 16-64, x 112-303, colour 15 = all planes set) with `movem.w d1-d4,(a0)` per 16 pixels and also writes the dead occupancy map: 35 k per call, 2 calls (one per buffer) per message.
* Glyph kernel `$14fd4`: per row and plane `btst/sne/and/btst/beq/or` + `and.b/or.b` to memory (~460 cycles per row, ~3.7 k per glyph).

### 3.2 Patches (details in the headers)
`ta_erase`: two `movem.l` of 12 registers per row, 49 rows, 11.6 k; writes `$100c` as the stock kernel (`2616`). `ta_init`: see above. `ta_face`: compares the sprite index with `FV0/FV1` (`$BEF00/$BEF02`: last index drawn into `$70000/$78000`; invalidated by the box restore (ta_erase) and the race init (ta_init), the only other writers of the area); returns exactly as the stock routine's `rts` at `$f9f8`. Also runs inside the extra frames (mx_sync calls `$f90c`). `ta_glyph`: `movep.l` read and write of the four plane bytes (alternate bytes), replicate table (1 KB) and plane-select table; result `a3` as the stock epilogue.

### 3.3 `ta_facestat` (VISIBLE, not default)
The face is drawn once per message and buffer with the mouth frame of the message's first pass (key = message pointer `$11a8`). Pixels that change: only the mouth/eye pixels of the face box (x 272-303, y 17-64); measured on 480 frames (levels 0/5/9, 160 passes each, up): 99 frames differ, at most 111 pixels per frame, bounding box **rows 43-60, columns 280-294** (`work/tightA/bbox_diff.py`). Picture: `work/tightA/res/facestat_vs_face.png` (3 differing frames; left of each pair = ta_face = stock pixels, right = ta_facestat). The face no longer moves its mouth while a message is typed.

### 3.4 Measurements (cycles per pass, matched passes)
### driving (race_start)
| variant | no speech: mean (n) | delta | VBL/pass | speech: mean (n) | delta | VBL/pass | max pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| current default (reference R) | 491171 (83) |  | 3.065 | 517265 (151) |  | 3.228 | 610324 |
| ta_erase (+ta_init)  [erase+glyph, no face] | 490013 (83) | -1158 | 3.058 | 515761 (151) | -1290 | 3.218 | 610336 |
| ta_erase+ta_init+ta_face | 489983 (83) | -1188 | 3.058 | 513101 (153) | -4371 | 3.202 | 604760 |
| speech set: erase+face+glyph (pixel-identical) | 489843 (83) | -1328 | 3.057 | 511758 (153) | -5572 | 3.193 | 604196 |
| speech set with ta_facestat (VISIBLE) | 489843 (83) | -1328 | 3.057 | 509579 (153) | -7791 | 3.180 | 604260 |
| ta_ymw | 489787 (83) | -1384 | 3.056 | 515684 (152) | -1474 | 3.218 | 609000 |
| ta_rb | 488189 (83) | -2982 | 3.046 | 514378 (153) | -3120 | 3.210 | 606484 |
| ta_rb + ta_rb0 | 486658 (83) | -4513 | 3.037 | 512825 (153) | -4520 | 3.200 | 605016 |
| ta_nomouse (risk) | 482857 (83) | -8314 | 3.013 | 508475 (156) | -8517 | 3.173 | 600872 |
| interrupts: rb+ymw+nomouse | 478323 (83) | -12848 | 2.985 | 503155 (148) | -12819 | 3.140 | 589980 |
| ALL pixel-identical: speech set + rb + ymw + nomouse (no rb0) | 477201 (83) | -13970 | 2.978 | 498697 (151) | -18331 | 3.112 | 589536 |
| ALL pixel-identical incl. rb0 | 475584 (83) | -15587 | 2.968 | 497609 (152) | -19525 | 3.105 | 588068 |
| ALL with ta_facestat (VISIBLE), no rb0 | 477491 (83) | -13680 | 2.980 | 496724 (152) | -20442 | 3.100 | 589572 |
### standing (race_grid)
| variant | no speech: mean (n) | delta | VBL/pass | speech: mean (n) | delta | VBL/pass | max pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| current default (reference R) | 414960 (74) |  | 2.589 | 418016 (159) |  | 2.608 | 461460 |
| ta_erase (+ta_init)  [erase+glyph, no face] | 413230 (74) | -1730 | 2.579 | 416896 (159) | -1120 | 2.601 | 459664 |
| speech set: erase+face+glyph (pixel-identical) | 413230 (74) | -1730 | 2.579 | 413291 (159) | -4725 | 2.579 | 459768 |
| speech set with ta_facestat (VISIBLE) | 413231 (74) | -1729 | 2.579 | 411050 (158) | -6988 | 2.565 | 459812 |
| ta_ymw | 414292 (74) | -668 | 2.585 | 417406 (159) | -610 | 2.605 | 460864 |
| ta_rb | 411944 (74) | -3016 | 2.571 | 415024 (158) | -3014 | 2.590 | 458440 |
| ta_rb + ta_rb0 | 410970 (74) | -3990 | 2.564 | 414024 (159) | -3992 | 2.584 | 457484 |
| ta_nomouse (risk) | 407898 (74) | -7062 | 2.545 | 410947 (158) | -7091 | 2.564 | 454388 |
| ALL pixel-identical: speech set + rb + ymw + nomouse (no rb0) | 402452 (74) | -12508 | 2.511 | 402576 (159) | -15440 | 2.512 | 449180 |
| ALL pixel-identical incl. rb0 | 401474 (74) | -13486 | 2.505 | 401595 (159) | -16421 | 2.506 | 448196 |
| ALL with ta_facestat (VISIBLE), no rb0 | 402452 (74) | -12508 | 2.511 | 400339 (159) | -17701 | 2.498 | 449224 |

Reading: with the pixel-identical speech set (erase+face+glyph) a typing/held pass is **-5.6 k** (driving) / **-4.7 k** (standing) cheaper on average and the two erase passes per message lose their +24 k spike (the maximum pass falls 610,324 -> 604,196: the maximum is not an erase pass any more, it is a different pass). In the scripted 1,707-pass race with 76 % speech passes (hud.md section 0) this is about -4.3 k per pass averaged. The standing scene has speech in 68 % of its passes.

### 3.5 The floated "speech in an extension of the top bar" (not built; estimate)
`[INFERENCE]` From the measured pieces: with ta_* the remaining speech costs are the ticker glyph (about 2 draws x 1.8 k per typed character, but one character per two passes), the face (about 6 k per speech pass: 12.3 k x (1 - 0.38) for ta_face, ~0 for ta_facestat) and the two box restores (11.6 k each per message). A top-bar speech line (one row of text, drawn only on change, no face, no 49-row sky box) would keep the glyph draws (they are per character in both layouts) and remove the face and the restore: about -6 k per speech pass and -23 k per message on top of ta_face/ta_erase, i.e. about -4.5 k per pass averaged over the 76 % speech race (-0.03 VBL), and the sky rows 16-64 would never need the message-box repaint at all. It is a design change (the face and 4-line text go away): not built.

## 4. Item 3: interrupts

### 4.1 Measured costs per VBL (Hatari CPU profile `profile on/save`, 200 VBL, race_start with the default set; `work/tightA/isr_prof.py`, `isr_sum.py`; instruction cycles only, so exception entry/exit overhead is not in these)
Reference R:
```
flips (544, 34)
VBL d11e-d138                                    cycles/VBL       289  insn/VBL      5.1
d486-d616 (VBL body: palette setup, d138/d19a)   cycles/VBL       887  insn/VBL     75.7
d138-d1a8 (ikbd cmd)                             cycles/VBL        80  insn/VBL      5.1
TimerB d616-d6fa                                 cycles/VBL      1986  insn/VBL    108.0
YM 8bf0-9100                                     cycles/VBL      3341  insn/VBL    303.4
ACIA cfb4-d060                                   cycles/VBL       846  insn/VBL     62.1
d2d4-d486 fades/etc                              cycles/VBL         0  insn/VBL      0.0
mt_clock b8000                                   cycles/VBL       116  insn/VBL      6.0
ta blobs BE000-BEFFF                             cycles/VBL         0  insn/VBL      0.0
total cycles/VBL 136648.72
```
With ta_erase, ta_ymw, ta_rb, ta_rb0, ta_nomouse:
```
flips (592, 37)
VBL d11e-d138                                    cycles/VBL       289  insn/VBL      5.1
d486-d616 (VBL body: palette setup, d138/d19a)   cycles/VBL       469  insn/VBL     29.8
d138-d1a8 (ikbd cmd)                             cycles/VBL         0  insn/VBL      0.0
TimerB d616-d6fa                                 cycles/VBL      1061  insn/VBL     57.0
YM 8bf0-9100                                     cycles/VBL      2372  insn/VBL    209.1
ACIA cfb4-d060                                   cycles/VBL         0  insn/VBL      0.0
d2d4-d486 fades/etc                              cycles/VBL         0  insn/VBL      0.0
mt_clock b8000                                   cycles/VBL       116  insn/VBL      6.0
ta blobs BE000-BEFFF                             cycles/VBL      1134  insn/VBL     76.6
total cycles/VBL 136649.46
```
Interrupt total per VBL 7,545 -> 5,441 cycles by this count (the blob line includes the two erase passes of the scene, about 116/VBL). **The lead's "Timer B ISR ~12 k per pass" is 1,986 per VBL x 3.06 VBL = 6.1 k per pass**: the first track's raster list has 8 interrupts per VBL (flag/count list at `$3d0e`: 7 colour-15 steps + 1 palette-B switch), not 41-47; the old 41-47 per FRAME was 5-6 VBL. The mouse query was the unexpected one: 846 + 80 per VBL in the profile, **-8.3 k per pass measured** (the exception entries and the transmit wait are not in the profile).

### 4.2 `ta_ymw`
The player `$8c38` writes 12 registers every VBL (R0/R1 from the tone image + the word `$91f0`, R2-R6, R7 read-modify-write keeping bits 6-7, R8-R11; R12/R13 are never written). In the race only R0, R1, R8 change (measured over 300 calls on levels 0/5/12: 299/199-299/299 changes of 299 transitions; the other 9 never). The blob compares the groups with a shadow and writes only changed registers (first call writes everything). Stock loop 840 cycles/call; the YM total per VBL fell 3,341 -> 2,372 (+ blob 706): **-0.26 k/VBL by profile, -1.4 k per pass measured**. The channel interpreters (2.1 k per VBL) are untouched: rewriting them is the only way to a bigger YM gain and was not attempted.

### 4.3 `ta_rb`, `ta_rb0` (Timer B)
Stock: each VBL the builder `$d57c-$d5e4` writes the list; the ISR `$d616` takes one interrupt per entry: flag 0 writes the next colour of the table at `$3cbc` (table `$3cc4`, 8 sky-gradient colours) to `$825e`, flag 1 switches colours 1-14 to palette B (`$3cf2`), flag 2 both. On track 1 the table is `$256 $256 $256 $256 $356 $356 $357 $457`: three interrupts re-write the colour that is already there (a no-op), one more writes the same again at the start. `ta_rb` replays the displaced `bset` at `$d5e6` and replaces the list by a compact one: a flag-0 entry whose colour equals the colour on screen is dropped (its count is added to the distance of the next kept entry; the first kept distance goes to `$fa21`); the colours of the kept entries go to a private table and `$3cbc` is pointed there. The ISR is untouched, so every remaining write happens at exactly the instant it does in stock. The compact list is cached (key = `$12fe/$1300` long + the 9 colour words `$3cc4-$3cd5`, compared every VBL); `ta_rb0` (site `$d57c`) skips the stock builder entirely on a hit. Result on track 1: 8 -> 4 interrupts per VBL; ISR 1,986 -> 1,061 per VBL; `ta_rb` -3.0 k, `ta_rb0` another -1.5 k per pass.

Semantic test (`work/tightA/rb_test.py`: random ($12fe, $1300, 9 colours with 55 % repeats), builder run in the model, the list decoded by a Python model of the stock ISR semantics into colour-15-per-scanline and palette-switch lines, stock vs candidate; 20,000 cases each; inputs restricted to $1300 - $12fe >= 9, the game's range is 38-39; below 5 the stock builder itself wraps 16-bit counts and cannot work):
```
calls 2400 bad 0 chip writes stock 28800 patched 14688
cases 20000 bad 0 interrupts stock 151965 new 84655
cases 20000 bad 0 interrupts stock 151965 new 84655
```
Hatari raster trace (`--trace video_color`, 80 VBL each, `work/tightA/rb_trace.py`, `rb_cmp.py`): the effective colour-15 changes per frame (absolute scanline and value) and the palette-B switch lines. `ta_rb`: every frame equals the reference frame except frame 0 of the trace (the VBL that the live apply interrupted: its first palette copy lands 3 lines later); `ta_rb0`: all frames identical:
```
res/rb_ref.txt frames 145 distinct colour15-change signatures 4
res/rb_rb.txt frames 146 distinct 5
signature sets equal: False
  ref (((8, 598), (109, 854), (117, 855), (121, 1111)), (135,)) x 32 | cand x 32
  ref (((12, 598), (109, 854), (117, 855), (121, 1111)), (135,)) x 15 | cand x 15
  ref (((12, 598), (109, 854), (117, 855), (121, 1111)), (134,)) x 32 | cand x 32
  ref (((8, 598), (109, 854), (117, 855), (121, 1111)), (134,)) x 64 | cand x 64
  change line 8 col 256 line-cycle/16 ref [6, 7, 8, 9] cand [6, 7, 8]
  change line 12 col 256 line-cycle/16 ref [4, 5, 6] cand [4, 5, 6]
  change line 109 col 356 line-cycle/16 ref [2, 3, 4, 5, 6, 7, 8] cand [2, 3, 4, 5, 6, 7, 8]
  change line 117 col 357 line-cycle/16 ref [2, 3, 4, 5, 6, 7, 8] cand [2, 3, 4, 5, 6, 7, 8]
  change line 121 col 457 line-cycle/16 ref [2, 3, 4, 5, 6, 7] cand [2, 3, 4, 5, 6, 7, 8]
palette-B write lines/cycle buckets ref [(134, 3), (134, 4), (134, 5), (134, 6), (134, 7), (134, 8), (134, 9), (134, 10), (134, 11), (134, 12), (134, 13), (134, 14), (134, 15), (134, 16), (134, 17), (134, 18), (135, 3), (135, 4), (135, 5), (135, 6)] cand [(134, 3), (134, 4), (134, 5), (134, 6), (134, 7), (134, 8), (134, 9), (134, 10), (134, 11), (134, 12), (134, 13), (134, 14), (134, 15), (134, 16), (134, 17), (134, 18), (135, 3), (135, 4), (135, 5), (135, 6)]
```
```
res/rb_ref.txt frames 145 distinct colour15-change signatures 4
res/rb_rb0.txt frames 146 distinct 4
signature sets equal: True
  ref (((8, 598), (109, 854), (117, 855), (121, 1111)), (135,)) x 32 | cand x 32
  ref (((12, 598), (109, 854), (117, 855), (121, 1111)), (135,)) x 15 | cand x 16
  ref (((12, 598), (109, 854), (117, 855), (121, 1111)), (134,)) x 32 | cand x 32
  ref (((8, 598), (109, 854), (117, 855), (121, 1111)), (134,)) x 64 | cand x 64
  change line 8 col 256 line-cycle/16 ref [6, 7, 8, 9] cand [6, 7, 8, 9]
  change line 12 col 256 line-cycle/16 ref [4, 5, 6] cand [1, 4, 5, 6]
  change line 109 col 356 line-cycle/16 ref [2, 3, 4, 5, 6, 7, 8] cand [2, 3, 4, 5, 6, 7, 8]
  change line 117 col 357 line-cycle/16 ref [2, 3, 4, 5, 6, 7, 8] cand [2, 3, 4, 5, 6, 7, 8]
  change line 121 col 457 line-cycle/16 ref [2, 3, 4, 5, 6, 7] cand [2, 3, 4, 5, 6, 7, 8]
palette-B write lines/cycle buckets ref [(134, 3), (134, 4), (134, 5), (134, 6), (134, 7), (134, 8), (134, 9), (134, 10), (134, 11), (134, 12), (134, 13), (134, 14), (134, 15), (134, 16), (134, 17), (134, 18), (135, 3), (135, 4), (135, 5), (135, 6)] cand [(134, 3), (134, 4), (134, 5), (134, 6), (134, 7), (134, 8), (134, 9), (134, 10), (134, 11), (134, 12), (134, 13), (134, 14), (134, 15), (134, 16), (134, 17), (135, 3), (135, 4), (135, 5), (135, 6), (135, 7)]
```
Intra-line timing (line cycle / 16 of each effective write) sets agree to one bucket (the ISR entry latency depends on the instruction it interrupts).

### 4.4 `ta_nomouse` (default no, behaviour risk)
Site `$d486` = the VBL body's first instruction `jsr $d138` (IKBD command `$0D`, "interrogate absolute mouse position", reply = 6 bytes = 6 ACIA interrupts through `$cfb4` per VBL). Skipped while `$1021 == 2`. Evidence the race does not read the mouse: the only readers of `$6106/$6108/$610f-$6114` are menu code (`$169de $16b5c $16bca $17172`); a memory-read trace over 2,400 emulated race passes (levels 0/5/14, up and zig) shows 0 reads. Hatari, real IKBD joystick through host keys (`--joy1 keys`, `work/tightA/joy_test.py`; stock vs ta_nomouse): `$6105` = 00 / 01 (Up) / 05 (Up+Left) / 09 (Up+Right) / 00 identical, steering `$1318` and speed `$130c` the same:
```
hd_clouds,hd_nomap,hd_nomap2,h ('idle', '00', '0000', '0000', '0000')
hd_clouds,hd_nomap,hd_nomap2,h ('Up held 4s', '01', '0238', '000a', 'ffe4')
hd_clouds,hd_nomap,hd_nomap2,h ('Up held 7s', '01', '054e', '000a', 'ffe4')
hd_clouds,hd_nomap,hd_nomap2,h ('Up+Left', '05', '077b', '0008', '0071')
hd_clouds,hd_nomap,hd_nomap2,h ('Up+Right', '09', '094d', '0009', 'ff73')
hd_clouds,hd_nomap,hd_nomap2,h ('released', '00', '0a45', '0000', 'ff73')
hd_clouds,hd_nomap,hd_nomap2,h ('idle', '00', '0000', '0000', '0000')
hd_clouds,hd_nomap,hd_nomap2,h ('Up held 4s', '01', '0238', '000a', 'ffe4')
hd_clouds,hd_nomap,hd_nomap2,h ('Up held 7s', '01', '0576', '000a', 'ffe4')
hd_clouds,hd_nomap,hd_nomap2,h ('Up+Left', '05', '07b5', '0008', '0071')
hd_clouds,hd_nomap,hd_nomap2,h ('Up+Right', '09', '0991', '0009', 'ff7b')
hd_clouds,hd_nomap,hd_nomap2,h ('released', '00', '0a81', '0000', 'ff7f')
DONE3
```
Not proven: menus after the race, real IKBD hardware, a mouse used as fire button (the code reads `$6105` bit 7 only); the IKBD stays in absolute-mouse mode without being interrogated. Mouse variables `$6106-$6117` differ from stock in the state gate (masked, listed).

### 4.5 What was not done
The VBL handler's own 15-register save/restore (260 cycles), the palette-A copy, the channel interpreters of the YM player, the tick clock `mt_clock` (kept exact, not touched). A custom Timer B ISR was rejected: the stock ISR writes colour 15 about 100 cycles after entry, which may already be inside the visible line, so any prologue change moves visible pixels in the first columns of a band.

## 5. Gate results

### 5.1 Exact 68000 model, all frames, 3 extras per tick (reference = default set; candidate = ta_init erase face glyph ymw rb nomouse)
(patch-site rows removed from the list; the sites of ymw/rb/nomouse are not executed in the pass model)
```
level 0 up {'frames': 640, 'passes': 160, 'masked_bytes': 54978} bad RAM addrs 33
level 0 zig {'frames': 1278, 'passes': 320, 'masked_bytes': 109956} bad RAM addrs 33
level 5 up {'frames': 1918, 'passes': 480, 'masked_bytes': 164560} bad RAM addrs 33
level 5 zig {'frames': 2554, 'passes': 640, 'masked_bytes': 219164} bad RAM addrs 33
level 12 up {'frames': 3194, 'passes': 800, 'masked_bytes': 273020} bad RAM addrs 33
level 12 zig {'frames': 3711, 'passes': 960, 'masked_bytes': 326876} bad RAM addrs 33
level 14 up {'frames': 4156, 'passes': 1120, 'masked_bytes': 380732} bad RAM addrs 33
level 14 zig {'frames': 4616, 'passes': 1280, 'masked_bytes': 434588} bad RAM addrs 33
RESULT frames compared 4616, frames differing 0 (pixel bytes 0), other-buffer differing 0, RAM passes 1280, RAM differing addresses 33 (masked bytes 434588)
executions in candidate: {'0xbe114': 1331, '0xbe000': 153, '0xbe600': 4712}
  RAM $0100c differs in 637 passes
  RAM $0100d differs in 635 passes
```
RAM addresses that differ: `$100c/$100d` (the HUD kernel scratch that the skipped face draw no longer writes; masked in every earlier gate) and the bytes of the patch sites themselves; nothing else in `$0-$6ffff` over 1,280 passes.

Unit tests: glyph kernel
```
glyph kernel unit test: stock $14fd4 vs ta_glyph, all 256 colour bytes x 4 address parities, random font/screen: cases 1024 differing 0
```
Negative controls (poked blobs; must DIFFER) and positive controls (must be identical):
```
NEG glyph (movep write displaced by 2):
RESULT frames compared 160, frames differing 72 (pixel bytes 44186), other-buffer differing 72, RAM passes 160, RAM differing addresses 6 (masked bytes 0)
NEG erase (second movem at +64 instead of +48):
RESULT frames compared 160, frames differing 22 (pixel bytes 5016), other-buffer differing 21, RAM passes 160, RAM differing addresses 4 (masked bytes 54604)
NEG face (always same):
RESULT frames compared 160, frames differing 86 (pixel bytes 62838), other-buffer differing 86, RAM passes 160, RAM differing addresses 10 (masked bytes 54604)
POS controls (unpoked):
RESULT frames compared 160, frames differing 0 (pixel bytes 0), other-buffer differing 0, RAM passes 160, RAM differing addresses 6 (masked bytes 0)
RESULT frames compared 160, frames differing 0 (pixel bytes 0), other-buffer differing 0, RAM passes 160, RAM differing addresses 4 (masked bytes 54604)
```
(`ta_facestat` is a negative control by itself: 99 of 480 frames differ, section 3.3.)

### 5.2 Hatari per-pass state (R = default set, C = same with the ta set; `all_R_*` vs `all_C_*`; key = `$100e`; mask = the documented display scratch of `cmpstate_hd.py` + the mouse variables of ta_nomouse; the cloud-slot rows are the apply-instant artifact: they differ between ANY two runs including R tick-on vs R tick-off, 10,582 bytes)
```
=== R vs C start_on
res/state/all_R_start_on.json (202 passes) vs res/state/all_C_start_on.json (205): common 202 (keys 67..268); 1479044 bytes compared; mask=on (masked differing bytes 4840); differing addresses 0, differing bytes 0
   masked: 244 differing bytes in buffer parity/pointer $1004-$100d
   masked: 3 differing bytes in mouse variables $6106-$6117 (ta_nomouse only)
   masked: 67 differing bytes in raster scratch $12f0-$1307
   masked: 4526 differing bytes in road geometry output $4724-$4f77 (rewritten before use)
=== R vs C start_off
res/state/all_R_start_off.json (201 passes) vs res/state/all_C_start_off.json (201): common 199 (keys 70..268); 1457078 bytes compared; mask=on (masked differing bytes 743); differing addresses 0, differing bytes 0
   masked: 146 differing bytes in buffer parity/pointer $1004-$100d
   masked: 597 differing bytes in dial cache $10d4-$10d7
=== R vs C drive_on
res/state/all_R_drive_on.json (289 passes) vs res/state/all_C_drive_on.json (284): common 284 (keys 0..1706); 2079448 bytes compared; mask=on (masked differing bytes 16415); differing addresses 0, differing bytes 0
   masked: 600 differing bytes in buffer parity/pointer $1004-$100d
   masked: 1136 differing bytes in cloud counters $27de-$27ed (dd50 removed)
   masked: 10508 differing bytes in cloud slots $29c8-$2c67 (dd50 removed)
   masked: 170 differing bytes in dial cache $10d4-$10d7
   masked: 6 differing bytes in mouse variables $6106-$6117 (ta_nomouse only)
   masked: 4 differing bytes in object order list scratch $36e8-$36ff
   masked: 185 differing bytes in raster scratch $12f0-$1307
   masked: 3721 differing bytes in road geometry output $4724-$4f77 (rewritten before use)
   masked: 85 differing bytes in score cache/flag $11c4-$11c5 $11c7
=== R vs C drive_off
res/state/all_R_drive_off.json (294 passes) vs res/state/all_C_drive_off.json (287): common 287 (keys 0..1706); 2101414 bytes compared; mask=on (masked differing bytes 12264); differing addresses 0, differing bytes 0
   masked: 254 differing bytes in buffer parity/pointer $1004-$100d
   masked: 1148 differing bytes in cloud counters $27de-$27ed (dd50 removed)
   masked: 10619 differing bytes in cloud slots $29c8-$2c67 (dd50 removed)
   masked: 162 differing bytes in dial cache $10d4-$10d7
   masked: 81 differing bytes in score cache/flag $11c4-$11c5 $11c7
=== R vs C start_x16
res/state/all_R_start_x16.json (205 passes) vs res/state/all_C_start_x16.json (205): common 205 (keys 115..319); 1501010 bytes compared; mask=on (masked differing bytes 323); differing addresses 0, differing bytes 0
   masked: 244 differing bytes in buffer parity/pointer $1004-$100d
   masked: 79 differing bytes in mouse variables $6106-$6117 (ta_nomouse only)
=== R vs C start_x32
res/state/all_R_start_x32.json (204 passes) vs res/state/all_C_start_x32.json (205): common 204 (keys 117..320); 1493688 bytes compared; mask=on (masked differing bytes 190); differing addresses 0, differing bytes 0
   masked: 190 differing bytes in buffer parity/pointer $1004-$100d
```
`start_on/off` = race_start, tick patches ON/OFF; `drive_on/off` = race_drive (time-out and restart inside, keys 0..1706); `x16/x32` = extras at 16/32 MHz. **0 differing addresses outside the masks in all six comparisons.**

### 5.3 Hatari A/B pixels (full buffers, both, R vs C = all ta_* incl. rb0 and nomouse)
```
race_start flip  10 R hash 09c8b376/929fc524 C hash 09c8b376/929fc524  differing bytes (both buffers, 64,000 compared): 0
race_start flip  40 R hash 5826bbcb/39e01d6e C hash 5826bbcb/39e01d6e  differing bytes (both buffers, 64,000 compared): 0
race_start flip  90 R hash a41b4a3b/c5849665 C hash a41b4a3b/c5849665  differing bytes (both buffers, 64,000 compared): 0
race_start flip 150 R hash a1df720f/0a24f9d0 C hash a1df720f/0a24f9d0  differing bytes (both buffers, 64,000 compared): 0
race_grid flip  10 R hash 13d1cd99/8e758917 C hash 13d1cd99/8e758917  differing bytes (both buffers, 64,000 compared): 0
race_grid flip  40 R hash a48ac4d2/a48ac4d2 C hash a48ac4d2/a48ac4d2  differing bytes (both buffers, 64,000 compared): 0
race_grid flip  90 R hash 7d724d2b/7d724d2b C hash 7d724d2b/7d724d2b  differing bytes (both buffers, 64,000 compared): 0
race_grid flip 150 R hash c86a485f/d1f9228f C hash c86a485f/d1f9228f  differing bytes (both buffers, 64,000 compared): 0
race_up flip  10 R hash 00b9eaf0/1de22f9b C hash 00b9eaf0/1de22f9b  differing bytes (both buffers, 64,000 compared): 0
race_up flip  40 R hash 08c2ceca/1397c0ee C hash 08c2ceca/1397c0ee  differing bytes (both buffers, 64,000 compared): 0
race_up flip  90 R hash a525b4a2/5c02cdd9 C hash a525b4a2/5c02cdd9  differing bytes (both buffers, 64,000 compared): 0
race_up flip 150 R hash 36adc321/b2605904 C hash 36adc321/b2605904  differing bytes (both buffers, 64,000 compared): 0
race_drive flip  10 R hash 8cecd87b/89266370 C hash 8cecd87b/89266370  differing bytes (both buffers, 64,000 compared): 0
race_drive flip  40 R hash 48413685/48413685 C hash 48413685/48413685  differing bytes (both buffers, 64,000 compared): 0
race_drive flip  90 R hash 0ba3dbbf/f1c2ad18 C hash 0ba3dbbf/f1c2ad18  differing bytes (both buffers, 64,000 compared): 0
race_drive flip 150 R hash 90c7d49f/90c7d49f C hash 90c7d49f/90c7d49f  differing bytes (both buffers, 64,000 compared): 0
TOTAL differing bytes 0 
DONE8
```
Negative control (ta_face forced to "same"):
```
race_start flip  90 R hash a41b4a3b/c5849665 C hash a41b4a3b/c5849665  differing bytes (both buffers, 64,000 compared): 0
TOTAL differing bytes 0 (negative control)
```

### 5.3b Hatari A/B with sensitive controls on the SAME capture (gate of record; `work/tightA/pix_ctl.py`)
Why the first control printed 0 differing bytes (diagnosis, section 5.3 above): the control (`ta_face` forced to "same") only differs from the real patch where the face has to be drawn; the capture was race_start flip 90 and the ticker was idle there (`$11ab = 0`, see the first lines of the raw output below: face absent in both builds), so there was nothing to draw wrongly. The poke WAS applied (the same control fires at every capture with a message, below), the buffer and rectangle were right. Fix: every capture now prints what the game was doing (`$100e`, ticker state `$11ab`, erase pending `$11b0`) and runs R (the default set), C (all ta_*), `facestat` (the VISIBLE variant) and four controls = C with ONE poke each, all from the same snapshot and the same apply instant: `face_same` (ta_face always "same"), `face_wrong` (ta_face draws sprite + 1), `erase_short` (the box restore writes its second half at +64 instead of +48), `glyph_bad` (MOVEP write displaced by 2). Rule: C must be IDENTICAL to R; each control must DIFFER on at least one capture where its element is active, in the right rectangle (face box x 272-303 y 17-64, text box x 112-271 y 16-64). The pixels counted are all pixels of BOTH buffers.
```
== race_grid flip 40: $100e=3677 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   2460  (face box     0, text box  2460)  -> DIFFER
== race_grid flip 90: $100e=3727 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    342  (face box     0, text box   342)  -> DIFFER
   glyph_bad    vs R: differing pixels total   1314  (face box     0, text box  1314)  -> DIFFER
== race_start flip 40: $100e=155 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   1994  (face box     0, text box  1994)  -> DIFFER
== race_start flip 70: $100e=185 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   3954  (face box     0, text box  3954)  -> DIFFER
```
```
== race_start flip 10: $100e=125 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_start flip 55: $100e=170 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   3032  (face box     0, text box  3032)  -> DIFFER
== race_start flip 90: $100e=205 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    642  (face box     0, text box   642)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_start flip 100: $100e=215 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    642  (face box     0, text box   642)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_start flip 150: $100e=265 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total    139  (face box   139, text box     0)  -> DIFFER
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    484  (face box     0, text box   484)  -> DIFFER
   glyph_bad    vs R: differing pixels total   1322  (face box     0, text box  1322)  -> DIFFER
== race_grid flip 10: $100e=3647 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total    581  (face box     0, text box   581)  -> DIFFER
== race_grid flip 120: $100e=3757 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    566  (face box     0, text box   566)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_grid flip 150: $100e=3787 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    566  (face box     0, text box   566)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 10: $100e=432 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 40: $100e=462 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 90: $100e=512 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total    111  (face box   111, text box     0)  -> DIFFER
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   1184  (face box     0, text box  1184)  -> DIFFER
== race_up flip 150: $100e=572 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total    139  (face box   139, text box     0)  -> DIFFER
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    604  (face box     0, text box   604)  -> DIFFER
   glyph_bad    vs R: differing pixels total    119  (face box     0, text box   119)  -> DIFFER
== race_drive flip 10: $100e=1696 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_drive flip 40: $100e=19 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_drive flip 90: $100e=69 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   2826  (face box    64, text box  2762)  -> DIFFER
== race_drive flip 150: $100e=129 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   facestat     vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    370  (face box     0, text box   370)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
```
Summary over the 20 captures (R vs C and every control from the same snapshot and apply instant; the 16 requested A/B captures race_start/race_grid/race_up/race_drive at flips 10/40/90/150 are all inside, plus race_start 55/70/100 and race_grid 120): **C 20/20 identical to R. With a message active (`$11ab != 0`, 11 captures): face_same 11/11 DIFFER, face_wrong 11/11, glyph_bad 10/11, erase_short 3/11 (it differs where a message was erased shortly before: 8/20 captures overall); `ta_facestat` (the visible variant) 3/7.** Every control fires in its own rectangle (face box for the face controls, text box for glyph/erase).

`ta_ymw` (chip state, no pixels): control = the R0/R1 writes always skipped, same random sound triggers, real patch for comparison:
```
YM control (R0/R1 writes always skipped): expect bad>0
CHIP DIFF level 14 call 298 [66, 255, 170, 1, 194, 1, 26, 184, 10, 11, 8, 0, 170, 170, 170, 170] [170, 170, 170, 1, 194, 1, 26, 184, 10, 11, 8, 0, 170, 170, 170, 170]
CHIP DIFF level 14 call 299 [66, 255, 86, 1, 28, 1, 26, 184, 9, 10, 10, 0, 170, 170, 170, 170] [170, 170, 86, 1, 28, 1, 26, 184, 9, 10, 10, 0, 170, 170, 170, 170]
calls 1200 bad 1200 chip writes stock 14400 patched 5836
YM real patch:
calls 1200 bad 0 chip writes stock 14400 patched 7628
```
`ta_rb`/`ta_rb0` (raster, no buffer pixels): the trace comparator of section 4.3 must see a change when a colour-15 change is lost: control = `ta_rb` with the "colour differs" branch removed (`be7aa = nop`, every flag-0 entry dropped), same trace procedure (for the real `ta_rb` the "False" printed below is the single frame 0 of the trace, the VBL the live apply interrupted; all other 144 frames equal the reference; for the control NO reference signature is reproduced and the three colour changes at lines 109/117/121 are gone):
```
rb control (kept-colour branch removed) vs reference:
res/rb_ref.txt frames 145 distinct colour15-change signatures 4
res/rb_rbneg.txt frames 146 distinct 4
signature sets equal: False
  ref (((8, 598), (109, 854), (117, 855), (121, 1111)), (135,)) x 32 | cand x None
  ref (((12, 598), (109, 854), (117, 855), (121, 1111)), (135,)) x 15 | cand x None
  ref (((12, 598), (109, 854), (117, 855), (121, 1111)), (134,)) x 32 | cand x None
  ref (((8, 598), (109, 854), (117, 855), (121, 1111)), (134,)) x 64 | cand x None
  change line 8 col 256 line-cycle/16 ref [6, 7, 8, 9] cand [6, 7, 8, 9]
  change line 12 col 256 line-cycle/16 ref [4, 5, 6] cand [1, 4, 5, 6]
  change line 109 col 356 line-cycle/16 ref [2, 3, 4, 5, 6, 7, 8] cand []
  change line 117 col 357 line-cycle/16 ref [2, 3, 4, 5, 6, 7, 8] cand []
  change line 121 col 457 line-cycle/16 ref [2, 3, 4, 5, 6, 7] cand []

real ta_rb vs reference (from section 4.3):
res/rb_ref.txt frames 145 distinct colour15-change signatures 4
res/rb_rb.txt frames 146 distinct 5
signature sets equal: False
```

### 5.4 Cold boots, play
```
RESULT in_race = True vbl 5809
PEEK $b2700: > m $b2700 16
PEEK $bef00: > m $bef00 16
RESULT in_race = True vbl 5809
PEEK $b2700: > m $b2700 16
PEEK $bef00: > m $bef00 16
in_race True vbl 5808
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after SPACE: $100e 0
(366, 2, 101, 0, (2, 2, 14))
(816, 2, 191, 0, (12, 12, 44))
(1267, 2, 281, 0, (24, 24, 76))
(1717, 2, 371, 0, (25, 25, 81))
(2168, 2, 461, 0, (40, 40, 116))
(2619, 2, 552, 0, (53, 53, 151))
(3069, 2, 642, 0, (90, 90, 215))
(3520, 2, 732, 0, (99, 99, 235))
(3970, 2, 822, 0, (127, 127, 289))
(4421, 2, 912, 0, (164, 164, 352))
(4871, 2, 1002, 0, (167, 167, 361))
(5322, 2, 1092, 0, (171, 171, 371))
(5773, 2, 1183, 0, (200, 200, 430))
(6223, 2, 1272, 0, (231, 231, 491))
(6679, 2, 1364, 0, (252, 252, 544))
(7129, 2, 1454, 0, (271, 271, 594))
(7580, 2, 1544, 0, (289, 289, 644))
(8030, 2, 1634, 0, (314, 314, 699))
(8481, 2, 1705, 5, (321, 321, 711))
(8937, 2, 55, 0, (321, 321, 712))
(9738, 2, 215, 0, (343, 343, 773))
(10188, 2, 306, 0, (350, 350, 796))
(10639, 2, 396, 0, (352, 352, 801))
(11089, 2, 486, 0, (371, 371, 845))
(11540, 2, 576, 0, (387, 387, 883))
(11991, 2, 666, 0, (428, 428, 948))
(12441, 2, 756, 0, (432, 432, 960))
(12892, 2, 846, 0, (469, 469, 1021))
(13342, 2, 936, 0, (492, 492, 1070))
(13793, 2, 1027, 0, (492, 492, 1070))
(14243, 2, 1117, 0, (506, 506, 1101))
(14694, 2, 1207, 0, (536, 536, 1161))
(15144, 2, 1297, 0, (563, 563, 1218))
(15595, 2, 1387, 0, (579, 579, 1266))
(16046, 2, 1477, 0, (595, 595, 1310))
(16496, 2, 1567, 0, (614, 614, 1358))
(16947, 2, 1657, 5, (645, 645, 1415))
extra frames 645 in 17197 VBL; restarts seen 1 time-out seen True
alive, $100e: 1701 marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
DONE4
```
STE TOS 1.62 1 MB and 4 MB boot to the race; the 5-minute play (8 MHz, up held, with time-out `$1226=5` and one restart) of `build/tighta` (= default set with `ta_init ta_erase ta_face ta_glyph ta_ymw ta_rb ta_nomouse`, built with the private tool; `ta_rb0` was added after that play and is covered by the state/pixel/trace gates only).

## 6. Integration for the lead

### 6.1 Which patches are safe to default
| patch | class | why |
|---|---|---|
| `ta_erase` + `ta_init` | **safe** | identical pixels and state in the model, Hatari state gate (incl. restart) and pixel gate; the only behaviour change is where the restore's occupancy-map writes (dead) go |
| `ta_face` | **safe** | identical pixels/state; sensitive controls fire |
| `ta_glyph` | **safe** (68000-68030) | identical; exhaustive unit test; uses MOVEP (a 68060 would trap) |
| `ta_ymw` | **safe, low risk** | identical chip register file in 2,400 randomised calls; relies on the player being the only YM writer in the game (hwscan) |
| `ta_rb`, `ta_rb0` | **safe in the emulator, hardware timing unproven** | identical colour/palette-switch scanlines in the Hatari write trace; the ISR is untouched; the gain depends on the track's sky table (none lost if all 8 colours differ) |
| `ta_facestat` | **VISIBLE**, needs user approval | freezes the mouth (section 3.3) |
| `ta_nomouse` | **RISK: do not default without the user's approval** | see 6.2 |

### 6.2 `ta_nomouse`: exactly what it removes and what could break
It removes, once per VBL while the mode byte `$1021 == 2` (race), the IKBD command `$0D` (`jsr $d138` at `$d486`: "interrogate absolute mouse position") and with it the reply: 6 bytes through the ACIA receive interrupt (`$cfb4`) per VBL, whose handler stores the absolute x/y into `$6106/$6108` and the button/direction flags into `$610f-$6114`. Measured: -8.3 k cycles per driving pass, -7.1 k standing. What stays: the joystick and keyboard packets (independent of the query: checked with real host-key joystick input in Hatari, identical `$6105/$130c/$1318`), the IKBD mode (absolute mouse, never switched off). What could break: (a) any race-time code that reads the mouse variables (none found: readers are menu routines; 0 reads in 2,400 emulated passes on 3 levels; unproven for every possible path, e.g. end-of-race or pause screens inside mode 2); (b) a real mouse used as a fire/steer input in race (never read by the race code as far as traced); (c) on a real IKBD/ACIA the unusual condition "absolute mode but never interrogated" is untested; (d) code outside the race that expects the VBL to keep the position fresh right after leaving mode 2 (the query resumes at the first VBL with `$1021 != 2`, the report arrives one VBL later). Recommendation: keep `default: no`; ask the user ("-8 k per pass, 0.05 VBL, for dropping the mouse position while racing").

### 6.3 Sites, order, conflicts (from `msrpatch_priv.py list`, resynced with the current tool; `verify` ALL OK with every `ta_*`, `tb_*`, `tc_*` file present; the tool refuses any byte overlap)
| ta_ patch | site(s) | requires / conflicts | neighbours at nearby addresses (no byte overlap) |
|---|---|---|---|
| `ta_erase` | `$1209c` (6 B) | requires hd_stage; owns data `$BEF00-$BEF0F` | none |
| `ta_init` | `$edea` (6 B, the same bytes hd_init patches) | requires hd_stage ta_erase; **conflicts hd_init** (select ta_init INSTEAD) | tb_carph `$ed90`, tb_blit `$ed6c` (different bytes, same routine area) |
| `ta_face` | `$f994` (6 B) | requires hd_stage ta_erase ta_init; conflicts ta_facestat | hd_nomap `$f9dc` (4 B, same routine) |
| `ta_facestat` | `$f994` | same; conflicts ta_face | same |
| `ta_glyph` | `$14fd4` (6 B) | requires hd_stage | none |
| `ta_ymw` | `$8e2c` (10 B) | none; data `$BEF40-$BEF4F` | none |
| `ta_rb` | `$d5e6` (6 B) | none; data `$BEE00-$BEE7F` | mt_clock `$d128` (VBL ISR, different routine) |
| `ta_rb0` | `$d57c` (14 B) | requires ta_rb | none |
| `ta_nomouse` | `$d486` (6 B) | none | mt_clock `$d128` |
Order: nothing is order-dependent except `ta_init` replacing `hd_init`, `ta_rb0` after `ta_rb`, and `ta_face`/`facestat` after `ta_erase`+`ta_init`. Against `mx_*`: mx_sync calls `$f90c` (the face) and `$11ef0` (the ticker, with its erase) in the extra frames, so ta_face/ta_erase/ta_glyph run inside the extras (gated: 4,616 frames in the model, Hatari state at 16/32 MHz); mx_sync requires hd_stage only, not hd_init. Against `mt_*`: `mt_clock` replays the `addq` at `$d128`; `ta_nomouse` (`$d486`) and `ta_rb*` (`$d57c-$d5ec`) are in the VBL body, a different instruction range. Against `tb_*`/`tc_*`: their sites (`$ed6c $ed90 $39ac $17c24 $e2e8 $18bf4 $18c86 $e406 $e316`) are in the sprite/object/road path; none shares a byte with a `ta_*` site, and none of my patches reads or writes the sprite-slot memory. Blob areas: mine `$BE000-$BEF4F` only (tb `$BF000+`, tc `$B6800+`), no `; ram:`.
* No default flipped. Machines: CPU-only; no blitter, no STE register. Mega STE: not measured. TT/Falcon: not booted with the ta set. 50/60 Hz: nothing depends on the frame rate.

## 7. Unproven
* Horizon skip (item 1): upper bound only.
* `ta_nomouse` on real hardware and in menus.
* `ta_rb` raster identity is proven by the Hatari write trace and the decode model, not by a screenshot comparison; real-hardware raster timing not tested.
* Cycle numbers are Hatari-only; the per-item gains are measured on the first track (race_start/race_grid snapshots): `ta_rb`/`rb0` depend on the track's sky table (fewer repeated colours = fewer dropped interrupts).
* The extras were gated in the pass model (4,616 frames) and at 16/32 MHz in Hatari state, not with a Hatari pixel gate on extra frames.
* The cycle deltas have a phase effect of about +-1 k (a different cost of the interrupts that land in the stage).
