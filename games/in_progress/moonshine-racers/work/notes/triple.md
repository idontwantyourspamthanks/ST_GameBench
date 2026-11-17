# Moonshine Racers: triple buffering as the lever for extra frames on the STE (study, MSRTripleStudy)

Verdict: **NO-GO for the 8 MHz STE** (the user's target); **a conditional candidate for 16 MHz machines** (Mega STE), where it measures as +5.8 displayed fps at best.
8 MHz STE: removing every latch wait (the whole benefit a third screen can give) moves racing ticks with an extra picture from 28.8 % to 29.5 % (12.88 -> 12.95 displayed fps, measured with pokes that remove the waits), the third screen costs 32,000 B that on the plain STE are the player-car code cache (about -21 k cycles per frame if taken from there; the model says 17 % of ticks with an extra instead of 29 %), and the ticker/face/erase machinery would have to be rewritten for a ring of three.
16 MHz (same build, same scene): latch wait 0.305 VBL per extra frame, extras per tick 1.744 -> 2.324, displayed 27.4 -> 33.2 fps (section 6); on a Mega STE the pool the screen would take is idle (`tb_car` is off there).
What limits the 8 MHz extras is elsewhere (section 7): the `mx_sync` undo save/restore costs 0.48 VBL per tick with an extra, the extra frame itself 2.45 VBL, and late-ending extras starve the next tick.

Machine for every measurement: Hatari 2.6.1, STE TOS 1.62, 1 MB, 8.02 MHz, 50 Hz, snapshot `race_drive`, zig-zag joystick steering as a pure function of `$100e` (same scene as `integration.md` 11.6: 1,300 passes, time-out + restart inside, 94 standing passes, then racing),
build = the real default set (`work/triple/live/X`, made with the private tool copy `work/triple/msrpatch_priv.py`; its `live` output is byte-identical to `tools/msrpatch.py live`: `cmp work/triple/live/X.img work/triple/live/Xref.img` printed `same`).
"Racing ticks" = ticks after the restart with `$100e >= 130` (1,110 ticks).
Scripts: `work/triple/meas.py` / `meas2.py` (Hatari trace breakpoints, each prints `e $tag`, `e VBL`, `e FrameCycles`; time = VBL * 160256 + FrameCycles), `parse.py`, `analyze.py`/`analyze2.py`, `stats.py`/`stats2.py`, `run_lat.sh`, `run_lat16.sh`, `erase_check.py`; raw logs and parsed ticks in `work/triple/res/`.
Evidence tags: **[M]** measured (raw file named), **[D]** read in a disassembly / patch source (file named), **[I]** inference.
Nothing under `patches/`, `tools/`, `originals/` was touched; nothing enabled by default; no patch was written (the best case of the lever was measured by two byte pokes instead, section 2.3).

## 1. The protocol today [D]

* Flip `$d1ca` (`m68dis work/dumps/ram_race_start.bin d1a8`): `move.l $1008.w,d0 / move.l $1004.w,d1 / move.l d0,$1004.w / move.l d1,$1008.w / move.l d0,d2 / ror.w #8,d2 / move.l d2,$8200.w`: swaps the pair, writes the video base ($ff8201/$ff8203; $ff820d stays 0, so 256-byte alignment is required on the ST). The shifter latches the new base at the next VBL.
* `mx_sync` (patches/mx_sync.s) `newsync`: `jsr $d1ca` (flip), `PEND=1` ($B8F08), publish raster-band words, `logf`, `extras`, then the sleep until NEXT. Each extra frame ends with its own `jsr $d1ca` + `PEND=1` (disassembly `$b867c`).
* `mt_clock` (patches/mt_clock.s): the VBL ISR hook `$d128` -> `$B8000` clears `PEND` and adds 6 units (50 Hz) to the 1/300 s clock.
* The latch guards: `mt_pre` (`$B8200`, main frame: `tst.b PEND / beq / .w: tst.b PEND / bne .w / jmp $17c42`) and the `.g` loop in `extras` (`$b862e: tst.b $b8f08.l / $b8634: bne.s $b862e`): the first write into the new back buffer (`$17c42`) waits for the VBL that latches the flip. Everything before it (logic, `fe50 ff76 1003c`, `17c24`, `100b4`) runs inside the wait window.
* `$1004`/`$1008` users outside the race loop (grep of `work/hud/dis/all_7000_19000.txt`): `$7370 $7404.. $7554.. $7620.. $76b2.. $7734.. $8438.. $8484.. $8618.. $da62..`, the high-score/name screen `$7bf4 $7c60 $7cba $7d00`; flip callers: `$7b74` (`jsr $d1e4`, replaced by mx_sync), `$7496` (`bsr $d1e4`), `$7382 $7464` (`jsr $d1fe`). Fixed-address users: `$718c` (`move.l #$70000,$1004 / #$78000,$1008`), `$d8e4 $da32 $da4a` (clear/copy `$70000`/`$78000`).

## 2. Where the time goes (question 2), measured

### 2.1 Method
`work/triple/meas2.py`: 22 persistent trace breakpoints (loop top `$796a`, render start `$7a88`, newsync entry `$b8100` = end of the main pass, `$d1ca`, extras entry `$b8400`, `saveundo` `$b8a46`/`$b85f0`, `fe50` `$b8604`, `17c24` `$b861a`, `100b4` `$b8620`, the latch loop `$b862e` (every iteration is logged), first road write `$17c42`, stage returns `$b863c $b8648 $b866c $b8672 $b8678`, extra flip `$b867c`, `restoreundo` `$b8ab6`/`$b8710`, tick end `$b816a` with `m $b8f32 $100e $b8f24 $11ab`). 1,300 passes, 6,500 emulated VBL. The first run (`lat_X8.json.log`, fewer tags) and the second (`lat2_X8.json.log`) give the same histogram: 327/1134 and 320/1110 racing ticks with one extra, i.e. 28.8 % in both, and `integration.md` 11.6 printed 322/1115 = 28.9 % (same scene, same build).
Raw outputs: `work/triple/res/stats_X8.txt` (the listing below is abridged: min/median/max columns dropped), `stats_NW8.txt`, `stats_X16.txt`, `stats_NW16.txt`. Files: `lat_X8.json.log.gz` = first run (tick end tagged 17), `lat2_*.json.log.gz` = 8 MHz baseline and no-wait runs, `lat3_NW16.json.log.gz`; `*_ticks.json` = parsed per-tick records (the scripts read the uncompressed log: `gunzip` first). `lat3_X16.json.log` (3.7 GB, the latch loop is logged per iteration at 16 MHz) was deleted after parsing; its `lat3_X16_ticks.json` and `stats_X16.txt` are kept. The first two attempts of `lat2` produced no steering (the chain start link was armed too late: `K0 = $100e + 6` after 22 breakpoint registrations) and were discarded; the final runs arm the breakpoints first and the steering start at `$100e + 25`.

### 2.2 The 8 MHz STE, default build, per racing tick [M] (`stats_X8.txt`; VBL = 160,256 cycles)
```
===== X8 baseline (default build) ticks 1300 racing 1110
 extras/tick histogram {0: 790, 1: 320}  share with >=1 extra 28.8%  mean extras 0.288
 displayed fps ~ (passes+extras)/time = 12.88 (10 passes/s x (1+mean extras))
 tick len mean 4.999; >5.05: 247; <4.95: 203; main_end mean 2.937
  main flip entry(tag3) -> extras entry (tag32)  n 320 mean 0.003
  extras entry -> saveundo entry                 n 320 mean 0.009
  saveundo (tag20 -> tag21)                      n 320 mean 0.240 min 0.224 med 0.239 max 0.272
  rings fe50 ff76 1003c (6->22)                  n 320 mean 0.016
  17c24 clear (22->23)                           n 320 mean 0.014
  100b4 geometry (23->wait start)                n 320 mean 0.409 min 0.369 med 0.410 max 0.456
  latch wait loop (wait start -> 17c42)          n 320 mean 0.033 min 0.000 med 0.000 max 0.329
  road 17c42 (8->24)                             n 320 mean 0.658
  10a5e+10a98 (24->25)                           n 320 mean 0.003
  prerestore+e2e8+carstep+e316 (25->26)          n 320 mean 0.185
  horizon 18318 (26->27)                         n 320 mean 0.222
  objects e406 (27->28)                          n 320 mean 0.854 min 0.390 med 0.826 max 1.624
  hud (28->flip call 5)                          n 320 mean 0.054
  extra frame, tag6 -> flip                      n 320 mean 2.447 min 1.886 med 2.384 max 3.307
  restoreundo (tag30 -> tag31)                   n 320 mean 0.238 min 0.224 med 0.229 max 0.272
  last flip -> tick end (sleep + restoreundo)    n 320 mean 0.275
  latch-wait histogram (0.1 VBL): {0.0: 263, 0.1: 24, 0.2: 24, 0.3: 9}  >0.02: 64 of 320
  no-extra ticks: n 790, main_end mean 3.091, idle (len - main_end) mean 1.691
   main_end [0.00,2.50): 216 ticks, with extra  65%
   main_end [2.50,2.75): 280 ticks, with extra  40%
   main_end [2.75,3.00): 170 ticks, with extra  29%
   main_end [3.00,3.25): 175 ticks, with extra   9%
   main_end [3.25,3.50): 113 ticks, with extra   3%
   main_end [3.50,9.00): 156 ticks, with extra   1%
  main latch wait (tag8 - tag9): mean 0.0099 max 0.478; >0.02: 68 of 1110
```
(`main_end` = loop top to the newsync entry, interrupts included; the "latch wait" of an extra = first `$b862e` hit to `$17c42`; main = `$B8200` to `$17c42`.)

Reading:
* **Latch wait: 0.033 VBL per extra frame on average (5.3 k cycles), 0 in 256 of 320 extras, at most 0.33 VBL; the main frame's own wait is 0.0099 VBL per tick.** The reason is visible in the same table: the extra spends 0.240 (saveundo) + 0.016 + 0.014 + 0.409 (`100b4`) = 0.68 VBL before its first road write; the main flip comes at a random phase of a VBL, so the next VBL latches it (u in 0..1 VBL after the flip) before that work is done in 80 % of the extras. The idle per tick caused by latch waits is `0.288 * 0.033 + 0.0099 = 0.019 VBL` (one fiftieth of a VBL).
* The undo costs more than the wait: saveundo 0.240 + restoreundo 0.238 = **0.478 VBL (76.6 k cycles) per tick that gets an extra**.
* Extra frame 2.447 VBL = geometry 0.409 + road 0.658 + horizon 0.222 + objects 0.854 + slot restore / distance / projection 0.185 + hud 0.054 + the rest 0.065.
* A tick with an extra: main 2.560 (mean over those ticks) + saveundo 0.240 + extra 2.447 + restoreundo 0.238 -> the tick runs 5.535 VBL long on average (the next tick is shortened by the same amount).
* Where the rest of the tick goes (racing ticks): mean main 2.937, mean idle after the last flip 1.283 VBL: **ticks without an extra idle 1.691 VBL** (they cannot hold the 2.45 + 0.24 + 0.24 VBL an extra needs), ticks with an extra 0.275 VBL.

### 2.3 Upper bound of the triple-buffer gain, measured by removing every wait [M]
`meas2.py ... poke=b8206=6008 poke=b8634=4e71`: `$B8206` `beq.s` -> `bra.s` (the `mt_pre` guard never waits) and `$B8634` `bne.s` -> `nop` (the extras' `.g` loop falls through). That is the timing a ring of three has if its flip never has to wait (every frame lasts > 1 VBL on this machine, so the flip-side wait of section 5 is zero): the pictures are wrong (a back buffer written while on screen), the CPU work is identical. Same scene, same steering. Raw `work/triple/res/stats_NW8.txt`:
```
===== NW8: both latch waits removed (upper bound of triple buffering) ticks 1299 racing 1109
 extras/tick histogram {0: 782, 1: 327}  share with >=1 extra 29.5%  mean extras 0.295
 displayed fps ~ (passes+extras)/time = 12.95 (10 passes/s x (1+mean extras))
  latch wait loop (wait start -> 17c42)          n 327 mean 0.000
  extra frame, tag6 -> flip                      n 327 mean 2.412 min 1.870 med 2.384 max 3.198
  latch-wait histogram (0.1 VBL): {0.0: 327}  >0.02: 0 of 327
  main latch wait (tag8 - tag9): mean 0.0002 max 0.000; >0.02: 0 of 1109
```
**28.8 % -> 29.5 % of ticks with an extra, 12.88 -> 12.95 displayed fps (+0.07 fps).** A logistic fit of "tick has an extra" against `main_end` on the baseline run (`P = 1/(1+exp(1.388 + 3.756*(main_end-2.9)))`, reproduces the 28.8 %) predicts 30.7 % for a shift of -0.033 VBL: the measured +0.7 point and the model's +1.9 points bracket the gain (run-to-run noise about one point). **[INFERENCE]** about the model; the two runs are measured.

### 2.4 How much of a tick is lost at the end [M] (`lat2_X8_ticks.json`, racing ticks with an extra: 320)
* 166 of 320 extra frames flip after 5.17 VBL (the 5.0-VBL grid plus the clock's 1/6 VBL), flip-time histogram in 0.5-VBL bins `{4.0: 3, 4.5: 61, 5.0: 119, 5.5: 80, 6.0: 38, 6.5: 17, 7.0: 2}`; the tick then ends late: lateness against the grid (cumulated overrun, `max(0, previous + len - 5 VBL)`, 0.5-VBL bins) `{0.0: 89, 0.5: 122, 1.0: 76, 1.5: 19, 2.0: 13}`, 177 of 320 >= 0.5 VBL, 61 >= 1.0 VBL, 19 >= 1.5 VBL. (`integration.md` 11.6 counted "79 of 349 extra-drawing ticks ended one or two VBL late" over the whole 137-s window, this count is over the 1,110 racing ticks only.)
* The late tick is paid by the next one (`mt_sync` resync keeps the grid): the 178 ticks that follow a tick ending >= 0.5 VBL late are 4.09 VBL long on average and **3 % of them get an extra, against 34 % for all other ticks.** Each overrun costs the next tick its extra; the overrun itself comes from the VBL-granular clock (`readclk` only changes at a VBL: the start of an extra is read up to 1 VBL early, so the rule `start + DEXT <= NEXT` is optimistic by about 0.5 VBL on average) [I] for the cause, [M] for the effect.
* Total time borrowed from following ticks: sum of the lateness increments 174.7 VBL over 1,110 racing ticks = 0.157 VBL per tick.

## 3. Does the undo / restore design survive a ring of three (question 3)?

### 3.1 `mx_sync` restores game STATE (RAM words), never screen content [D]
`patches/mx_sync.s`: `saveundo`/`restoreundo` copy `UTAB` (`$10ec,14 $12f8,6 $1308,4 $1316,16 $13a2,16 $1bb0,12 $23bc,12 $27c8,38`), `RTAB` ring windows (bases `$13b0 $17b0 $1bbc $23c8`, 32/32/64/32 bytes at the live head), the object slots `$2c68-$36e7` (2,688 B) and `KTAB` (the 100 self-modified immediates of the sprite kernels `$12a66 .. $15f22` plus `$dafe`, the HUD face RNG), into `UNDO` `$B9000..`. No address in these tables is a screen address, `$1004` or `$1008`; `restoreundo` ends with `move.w V.l,$130c.w`. `extrap.md` section 2 says it in words: "Not restored (display history, consistent with what the buffers hold): cloud `$28/$2a`, HUD erase pointers `$10c2-$10c8`, geometry/raster scratch." The state gates (per-pass RAM compare, `integration.md` 11.2) and the main-frame pixel gates therefore do not depend on how many buffers there are. **The undo/restore design survives a ring of three unchanged** (no change to `UTAB`, `RTAB`, `KTAB`, `U_SLOT`, `PREBUF`, `mx_pre`).
What the extras do assume about the screen is the other half, items 3.2-3.8.

### 3.2 Rows 65-199 are rewritten by every frame; the third buffer needs no background copy [D]/[M]
Per frame the game repaints rows 120-199 completely (road/grass/bands, 12,800 B, which also erases the previous cars and signs), recopies the horizon strip rows 65-119 (`$18318`, from the four pre-shifted sources `$60800 $62600 $64400 $66200`, fixed RAM, not part of any screen) and draws the sprites over it (`rendering.md` section 4.2; the stage films `film_bbox.txt`). Sky, clouds and mountain strip are NOT persistent per buffer in this build: the clouds are gone (`hd_clouds`/`hd_nomap`), the mountains are the recopied strip. The only persistent per-buffer content is rows 0-64: the black bar bitmap (rows 0-15, `BAR` `$BB800`, 2,560 B) and the flat sky (colour 15 = all planes set, rows 16-64), written by `hd_stage`'s `paint` the first time a buffer is used after the race init (`painted` byte = 0). So the third buffer needs no one-time copy of its own: it paints itself on its first back-buffer pass once its shadow has a `painted` byte (3.3). One-off cost [I from `hud_design.md` 3.5: 4.28 cycles/B bar copy 2,560 B = 11.0 k, sky 7,840 B = 17-21 k]: about 30 k cycles once per race start per buffer.
The same fact is what lets today's two buffers start with arbitrary contents (cold boot: intro/map pictures) and pass the pixel gates.

### 3.3 HUD per-buffer shadows [D] (`patches/hd_stage.s`, generated by `tools/msrhudgen.py`)
`topbar`: `move.l a5,d0 / btst #15,d0 / beq .sel / lea 64(a4),a4` with `a4 = S0 = $BCF00`: **the buffer is told apart by bit 15 of its address** ($70000: 0, $78000: 1). Two shadows of 64 B (S0 `$BCF00`, S1 `$BCF40`), `$BCF80` scratch. A third buffer has bit 15 equal to one of the two (any 256-aligned address): it would alias that shadow. Change: three-way select (`cmpa.l #$78000,a5 / cmpa.l #T3,a5`), S2 in free data space (`$BEF80-$BEFBF` is unused in the map: `ta_erase` data is `$BEF00+16`, `ta_ymw` `$BEF40+16`), `paint` and `hdinit`/`ta_init` clear its `painted` byte. The shadows are display history: `restoreundo` does not touch them (hud_design.md section 6 point 2), so extras need no change.

### 3.4 `ta_face` / `ta_erase` / `ta_init` per-buffer state [D]
`FV0/FV1` (`$BEF00/$BEF02`, the face sprite index last drawn in `$70000/$78000`, `$ffff` = nothing): `ta_face` chooses with `cmpa.l #$78000,a5`, `ta_erase` with `btst #15` (and writes `$ffff` for the buffer it erases), `ta_init` writes `$ffff` to both and clears `S0/S1` `painted`. `ta_facestat` (not default) likewise. Add `FV2 = $BEF08` and the third compare in the three patches (about 10 lines).

### 3.5 THE real work: the message ticker draws and erases for exactly two buffers [D] (`work/hud/dis/all_7000_19000.txt` `$11ef0`..`$120a4`; `hud.md` 5.2)
* **Typing**: pass N types character c into the back buffer (`$12022 bsr $120a4`, then `$12026 st.b $11ae`); pass N+1 finds `$11ae` set (`$11fd4`..`$11fe2`), draws the same character again into ITS back buffer (the other one) and only then advances the cursor `$11a6` (`$11fe6..$11fec`). So each character is drawn once in each of two consecutive back buffers: the "redraw twice" idiom for two buffers. In a ring of three the third buffer never receives the character.
* **Erase**: `$12078 subq.b #1,$11ac / bne / clr.b $11ab / st.b $11b0` falls straight into `$12086` (the erase of x 112-303, y 16-64 via `$1209c jsr $1242c`, `ta_erase`'s site): the end-of-hold pass erases the back buffer, `$11b0` stays set, and the next pass (`$11fc2 tst.b $11b0 / bsr $12086`) erases the other buffer and clears `$11b0 $11b1 $11a8`. Two erases (hence "two ~35 k passes per message"); the third buffer would keep the text.
* The face lives inside that box (x 272-303, y 17-64) and is cleared by the same erase.
* With extras today: the extra's `$11ef0` call runs with the ticker state saved and restored (`mx_sync` `hud:`), so every extra draws the pending repeat character / erase into its (other) buffer and the main frame repeats it into its own; consistent for two buffers.
* **Measured on the stock game** (`work/triple/erase_check.py race_grid`, breakpoints on `$12086`, `$120a4`, `$7a88` with `m $100e / $1004`, raw `work/triple/res/erase_stock.log`, 40 s of the time-out scene): box erases at `(pass, back buffer)` = `(3619, $70000) (3620, $78000) (3695, $70000) (3696, $78000) (3736, $78000) (3737, $70000) (3845, $70000) (3846, $78000) (3935, $70000) (3936, $78000)`: always two consecutive passes, alternating buffers; glyph draws: two `$120a4` calls per typing pass in that pass's buffer `(3565,$70000)x2 (3566,$78000)x2 (3567,$70000)x2 ...` (the new character and the repeat of the previous one).
**Design for three (the cost of a GO)**: hook the glyph entry `$120a4` (caller `$12026` = typing: append `(char, $11a6)` to a per-message log; return without drawing) and add a per-buffer catch-up routine called after `$11ef0` in `newhud` and in `mx_sync`'s `hud:`: `DRN[b]` = log entries already drawn in buffer b, `EG[b]` = erase generation drawn, `MG[b]` = message generation; per frame: if `EG[b] != EG` erase the box in this buffer (and `FV[b] = $ffff`, `DRN[b] = 0`), then draw log entries `DRN[b]..LOGN` with the existing glyph kernel (`ta_glyph`/`$14fd4`) and set `DRN[b] = LOGN`; the stock erase calls (`$12086` x2) become "bump `EG`" only. Cost [I]: one more glyph per typing pass (+1.8 k with `ta_glyph`) and one more box erase per message (+11.6 k with `ta_erase`); code about 250 B; the risk is pixel equality of the text with the two-buffer game while messages interrupt each other (higher priority message while one is typed: stock overtypes, leaves the old text) and the time-out/finish message flows that wait on `$11ab/$11b1` (`hud.md` 5.2: skipping the ticker soft-locks the game). Needs a message-heavy pixel gate (the `msgcons.py`-style monotonicity check plus stock-vs-ring comparison per main frame).

### 3.6 Road repaint 'erase through repaint', `tb_car` [D]
Nothing per buffer: `rd_draw` reads `$1008` and writes downwards from `$7d00(a0)` (`rd_draw.s` lines 56-58), the horizon copy and the sprite kernels address relative to `a5`/`a3`; `tb_car`'s generated code uses `d(a3)` offsets (`tb_car.s` notes) and its pool is code, not screen. Any 256-aligned buffer works.

### 3.7 Flip / latch protocol with three buffers (what `$d1ca`/`$d1de` must become)
Ring `A = $70000`, `B = $78000`, `C = T3`; state `F` = `$1004` (last flipped), `K` = `$1008` (next back buffer), `Z` = blob word (the buffer displayed before the last flip). New flip `t3flip` (replaces both `jsr $d1ca` in `mx_sync`):
```
t3flip: tst.b  PEND ; bne.s *-6          ; the previous flip must have been latched: the buffer shown before it is then free
        move.l $1008.w,d0                ; the frame just rendered = new front
        move.l $1004.w,d1                ; old front: still on screen until the next VBL
        move.l d0,$1004.w
        move.l Z,$1008.w                 ; next back buffer = the buffer shown before the old front (free)
        move.l d1,Z                      ; the old front becomes the spare
        move.l d0,d2 ; ror.w #8,d2 ; move.l d2,$8200.w ; then PEND=1 as today (mx_sync does that)
```
Why the wait before the write is necessary and sufficient: after flip i the display shows F(i-1) until the next VBL; the next render targets the buffer shown before F(i-1). If flip i-1 had not yet latched when flip i is written, that target is still on screen until the VBL (tearing); one pending flip at most guarantees it is free. The wait costs time only if a frame takes less than the time to the next VBL after the previous flip (any frame > 1 VBL: never; on this machine frames last 2.4-3 VBL). `mt_pre`'s guard and the `.g` loop disappear. At 16 and 32 MHz where frames are 1 VBL or less the same wait moves to the end of the frame (no gain there either except that the pre-latch work is no longer forced to start after the flip).
Two further requirements: (a) `$1004/$1008/Z` initialised at the race init (`$edea`, `ta_init`'s site): front = what the shifter shows (`$ff8201/$ff8203`), back = the other classic buffer, Z = T3; (b) the non-race code (`$7370..`, `$da62..`, name entry `$7bf4..`) keeps using `$1004/$1008` as a pair of valid screens, but several routines address `$70000/$78000` literally (`$d8e4 $da32 $da4a`, `$718c`): when the race loop is left with the front buffer = T3 they would clear/copy the wrong one. There is no hook at the loop exit today [I: the race loop `$796a..$7bac` is left only through its state machine; not traced]; a GO needs one (collapse to `$70000/$78000` + show `$70000`), or the ring must be collapsed at every flip when `$1021 != 2`.

### 3.8 Table: what a ring of three changes
| item | change |
|---|---|
| `mx_sync` undo/restore (`UTAB RTAB KTAB U_SLOT`), `mx_pre`, `PREBUF` | none (game state) |
| `mx_sync` flips, `.g` loop, `mt_pre` guard | `t3flip`, guards removed (3.7) |
| `hd_stage` `topbar`/`paint`/`hdinit`, `ta_init` | third shadow S2, three-way select, clear `painted` |
| `ta_face`, `ta_erase`, `ta_facestat` | FV2, three-way select |
| ticker `$11ef0` (`$120a4`, `$12086`) | log + per-buffer catch-up/erase (3.5) |
| `rd_*`, `tc_*`, `tb_car`, `ta_glyph`, `ta_ymw`, `mr_edge` | none |
| race init / race exit | ring init at `$edea`; exit hook needed (3.7) |

## 4. RAM for a third 32,000-byte screen (question 1) [D]/[M]
Map (`python3 tools/msrpatch.py list`, "valid layouts for this set: 1MB, 4MB; free run(s) $b2800-$e2bff"; free at 1 MB: `$B2700-$E2BFF` = 197,376 B; TOS 1.62 STE is zero to `$E83FF`, Mega STE TOS 2.06 only to `$E2BFF` (`integration.md` 10.3): zero runs of all `work/dumps/ram_*.bin`: `b2700-e83ff` (STE) / `b2700-e2bff` (Mega STE), plus small runs `4e700-4ffff` 6 K, `54000-55fff` 8 K, `5fe00-61fff` 8 K, `66f00-67fff` 4 K, `80000-80fff` 4 K, `ea800-eb7ff` 4 K (Mega STE only), `fb700-fffff` 18 K: **nothing but the top region can hold 32,000 contiguous bytes**; `$81000-$B1D40` is PP's HAGA chunk cache (the data the loader re-reads; [INFERENCE: not tested] unusable).
Used: payload image `$B2700-$BFC27` (54,568 B span, 16,022 non-zero bytes in 17 runs, the rest are run-time data areas and holes: no 32 KB hole), `rd_geom` `$C0000-$CAFFF` (45,056 B, fully used: product table `PT $C1000` 80 x 256 words), `rd_draw` `$CB000-$D7FFF` (53,248 B; tables end at `$D7040`, 3,968 B slack), `tb_car` pool `$D8000-$E2BFF` (44,032 B; filled up to `$E1D9C` in the 500-pass run, `pool_p44.json`: POOLP `00 0e 1d 9c`).
Candidates, 256-byte aligned (the shifter requires it on the ST; all of these are):
| option | third screen | what gives | cost [M from `work/tint/res/pool_log.txt`, mean cycles per pass over ~540 passes, same scene and set] | machines |
|---|---|---|---|---|
| A | `$DAF00-$E2BFF` | pool shrinks 44,032 -> 12,032 B (limit `POOLEND` `$DAF00`) | pool 44 KB 458,486; 16 KB 477,695; 8 KB 482,133 -> 12 KB about 480,000: **+21.5 k cycles = +0.134 VBL per frame that draws the player car (main AND every extra)** | both layouts at 1 MB; on a Mega STE `tb_car` is off by its run-time probe (`tb_car.s`: generated code is never run where a CPU cache exists) so the pool is idle there: free |
| B | `$E0000-$E7CFF` | pool 44,032 -> 32,768 B (`$D8000-$DFFFF`) | 32 KB 461,014 vs 44 KB 458,486 = +2.5 k = +0.016 VBL | STE TOS 1.62 only (`$E2C50+` is TOS 2.06 data on the Mega STE) |
| C | repack the payload | `$B2700-$BAFFF` | needs `org` changes in ~25 patch files; `rd_geom`/`rd_draw` tables are 98 KB fixed | a free 32 KB would appear below `$C0000` only by moving `rd_geom` up and shrinking the pool by 4-5 KB; not attempted |
| D | 4 MB machines | above `$100000` [INFERENCE: PP's whole-image cache layout is `integration.md` 10, not checked for a screen] | none | STE/Mega STE 4 MB |
**A unified answer for the plain STE (the machine the user cares about): A costs 0.134 VBL on the main frame and again on each extra, i.e. about 0.17 VBL per tick at the current 0.29 extras per tick, against a latch-wait gain of 0.019 VBL per tick. B costs 0.016 VBL but needs a per-machine screen address (probe TOS/Mega STE at the race init).**

## 5. End-to-end gain on the STE (question 4)
Arithmetic from section 2: the whole possible gain is the latch wait, 0.033 VBL x 0.288 extras + 0.0099 = 0.019 VBL per tick. In the extras histogram {0: 790, 1: 320} (28.8 %) removing every wait gave {0: 782, 1: 327} (29.5 %): **+7 ticks of 1,109 = +0.7 point, 12.88 -> 12.95 fps** [M]; the logistic model gives 30.7 % (+1.9 points, 13.1 fps) [I]. Option A's pool loss (+0.134 VBL on main and on extra, +0.27 VBL for a tick with an extra) predicts, with the same model, 17.1 % of ticks with an extra (about 11.7 fps) [I]: a net loss; option B (+0.016 x 2) would be neutral (+/-1 point).
Slope of the same model near the operating point (every 0.1 VBL taken off main + extra): shift -0.3 -> 46.6 %, -0.5 -> 58.2 %; so the cut needed for "most ticks" is not in the latch.
(16 MHz and above: the wait is a much larger share of the frame, section 6; 32 MHz is already at one frame per VBL with 3.9 extras per tick, `integration.md` 11.6.)

## 6. 16 MHz (for completeness, where frames are short)
Same scene (race_drive zig steering, 1,300 passes), same default build, `set_cpuclock(16)` after the live patch, `CYC=320512` (Hatari's `FrameCycles` run to 320,512 per VBL at 16 MHz; with 160,256 the durations came out negative and are discarded). Raw `work/triple/res/stats_X16.txt`, `stats_NW16.txt` (logs `lat3_*.json.log`):
```
X16 baseline: extras/tick {0: 8, 1: 419, 2: 653, 3: 87, 4: 22}  mean 1.744   displayed fps 27.44   main_end mean 1.578
  saveundo 0.116   restoreundo 0.115   100b4 0.198   road 0.325   horizon 0.105   objects 0.536   extra frame (tag6 -> flip) mean 1.601
  latch wait loop (wait start -> 17c42)  n 2074  mean 0.305  min 0.000  med 0.331  max 0.794     >0.02: 1477 of 2074
  main latch wait mean 0.1516, > 0.02: 418 of 1189
NW16 (both waits removed): extras/tick {0: 1, 1: 107, 2: 629, 3: 307, 4: 82, 5: 1}  mean 2.324   displayed fps 33.24   main_end mean 1.432
  extra frame mean 1.293   latch wait 0.000
```
The previous 16 MHz histogram of `integration.md` 11.6 was `{0: 8, 1: 386, 2: 618, 3: 87, 4: 22}` (mean 1.758): the baseline reproduces. **At 16 MHz the latch wait is 19 % of an extra frame (0.305 of 1.601 VBL): removing it gives +0.58 extras per tick (+33 %), 27.4 -> 33.2 displayed fps.** Check that the poke does not flatter a real ring: a real flip waits for the previous latch, which matters only for frames shorter than the time to the next VBL; the flip-to-flip intervals of the NW16 run (`lat3_NW16_ticks.json`, 4,120 intervals) are < 1.0 VBL in 77 cases, none < 0.8, mean 1.596, so the possible wait at the flip is at most 0.003 VBL per tick (sum of `max(0, 1 - interval)` per tick). 32 MHz (49 fps = one frame per VBL) cannot gain.
Where this applies [I]: STE accelerated to 16 MHz and the Mega STE (HAGA runs it at 16 MHz + cache, `integration.md` 10); the cache makes the CPU work shorter and the latch share larger, not measured (Hatari STE 16 MHz only). RAM there: the third screen at `$DAF00` is free on the Mega STE (pool idle) [D `tb_car.s`], on an accelerated plain STE the pool is live (options A/B of section 4).
The 8 MHz verdict does not change: the frames there are 2.4 VBL, the pre-write work (0.68 VBL) already hides the wait.

## 7. What actually limits the extras on the 8 MHz STE (measured levers; none is triple buffering)
Per tick with an extra (VBL, 8 MHz, mean): main 2.56 (all ticks 2.94) + saveundo 0.240 + extra 2.447 + restoreundo 0.238. Free time per racing tick on average: 5 - 2.937 - 0.288 x (0.240 + 2.447 + 0.238) = 1.22 VBL, but it is fragmented: a tick without an extra idles 1.69 VBL, short of the 2.4-2.9 an extra needs.
1. **undo save + restore = 0.478 VBL (76.6 k cycles) per tick with an extra** (`saveundo` 0.240, `restoreundo` 0.238 [M]: UTAB words, 4 ring windows byte-wise with `and.w/move.b/dbra` (about 36 cycles per byte), 672 longs of slots with `move.l (a0)+,(a1)+ / dbra`, 100 KTAB longs through an index loop). Hand estimate of the copy loops [I] 25-26 k each, measured 38 k: faster kernels (`movem.l` slots, word copies for the rings, only the KTAB entries that were actually patched) could save a large part of it; this alone is worth more than every latch wait: by the model, -0.24 VBL on the rule's side (saveundo is inside the measured frame) predicts about 43 % of ticks with an extra [I], and the restore removes the lateness that starves the next tick.
2. The deadline rule runs on a VBL-granular clock: 166 of 320 extras flip after the 5.0-VBL grid, and the 178 ticks after a late tick get an extra in 3 % of the cases (34 % otherwise). A finer clock (STE video counter `$ff8205-$ff8209`, or Timer C) in `readclk`/`wantnext` would stop the overruns and give those ticks their extra back [I]; the packing bound is `(5 - 2.94)/(2.45+0.24+0.24) = 0.70` extras per tick [I arithmetic], against 0.288 measured.
3. The extra frame itself: objects 0.854, road 0.658, geometry 0.409, horizon 0.222, restores/projection 0.185. The `100b4` geometry (0.409 VBL = 65 k cycles) is recomputed for each extra although the extra's pose differs from the main frame's only by `k` world units [I: needs the road model to move; not examined here].

## 8. GO / NO-GO
**NO-GO for the 8 MHz STE.** Measured best case +0.7 point of ticks with an extra (+0.07 fps) against a cost of 32,000 B that (on the plain STE) are the player-car code cache (-12 points by the model if taken from there), a ticker/face/erase rewrite with a message-heavy pixel gate, a race-exit hook, three-way shadows in four patches, and risk on every non-race screen. The latch wait the lever removes is 0.019 VBL per tick at 8 MHz.
**Conditional GO for 16 MHz machines (Mega STE)** only if the user wants more than the 27 fps those get today: measured upper bound 33.2 fps (+5.8), the RAM is free there, the work is the same patch list. Not recommended before the 8 MHz levers of section 7 are exhausted, because they help every machine.
The exact design if built: ring `$70000 -> $78000 -> T3 -> $70000` (the render order; `K = $1008` is always the buffer shown before the one just flipped), `T3 = $DAF00` (screen `$DAF00-$E2BFF`, 256-aligned, one layout for STE TOS 1.62 and Mega STE TOS 2.06 at 1 MB; `tb_car`'s `POOLEND` becomes `$DAF00`, pool 12,032 B on a plain STE) or `$E0000` on TOS 1.62 only (pool `$D8000-$DFFFF`, `POOLEND = $E0000`); patches that change: new `t3_flip` (flip with the wait on PEND before the write, ring state `Z`, init at `$edea`, exit collapse), `mx_sync` (two `jsr $d1ca` -> `t3flip`, delete the `.g` loop `$b862e-$b8635`), `mt_pre` (guard removed: `jmp $17c42`), `hd_stage` via `msrhudgen.py` (S2 at `$BEF80`, three-way select, `paint`), `ta_erase`/`ta_face`/`ta_facestat`/`ta_init` (FV2 `$BEF08`, painted), a new ticker patch (3.5), `msrpatch` `; ram:` for T3 and the `POOLEND` immediate. Unchanged: `UTAB RTAB KTAB`, `mx_pre`, `rd_*`, `tc_*`, `tb_car` code, `ta_glyph`, `ta_ymw`.

## 9. Not done / unproven
* No ring was built: the best case was measured by pokes (pictures wrong, timing exact for a ring whose flip never waits). The flip-side wait of section 3.7 is zero only because frames last > 1 VBL (8 MHz: 2.4 VBL; 16 MHz: flip-to-flip < 1.0 VBL in 77 of 4,120 intervals, section 6).
* Option A/B costs are the pool sweep of `integration.md` 11.5 (pool limit poked, same scene), interpolated to 12 KB [I]; not re-measured at 12 KB.
* The logistic model (sections 2.3, 5, 7) is a fit to the baseline 8 MHz run only; its one validation point (NW8, 29.5 % measured) is 1.2 points from the model's 30.7 %. Run-to-run: the two baseline runs give 28.8 % and 28.8 %.
* The ticker redesign, the exit hook, Mega STE/4 MB screen addresses, 60 Hz were not built or tested. The HAGA chunk cache being unusable is not tested. The `$1004/$1008` hazards on leaving the race loop (3.7) are [I].
* 16 MHz was measured on Hatari's STE at 16 MHz (no cache); the Mega STE's cache is not modelled by this setup.
* Real hardware: nothing measured. The video base latch timing (the base is taken at the next VBL) is the Hatari model and the assumption the existing `mt_pre`/`PEND` protocol already makes.
