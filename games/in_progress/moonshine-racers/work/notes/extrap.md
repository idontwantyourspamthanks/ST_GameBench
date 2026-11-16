# Moonshine Racers: extra frames between logic ticks (`mx_sync` + `mx_pre`, prototype, `default: no`)

Goal: with the fixed tick (`mt_*`, T=36 = 8.333 passes/s) a fast machine idles most of each tick. The extra-frame scheme redraws the SAME logic step at a pose
extrapolated from the last step, in the idle time, so a 16 MHz / 32 MHz machine shows 2 / 3 frames per tick while 8 MHz is unchanged. No game logic runs in the
extra frames; every word the advance changed is restored before the next tick.
Files: `patches/mx_sync.s` (replaces `mt_sync`, site `$7b74`), `patches/mx_pre.s` (site `$7b46`). Use `mt_clock + mt_pre + mx_pre + mx_sync` (NOT `mt_sync`).
Tools/evidence: `work/extrap/` (private `msrpatch_priv.py`; `emu.py` = exact Unicorn 68000 model of the pass; `gate*.py`, `pix3.py`, `zerolong.py`, `msgcons.py`, `neg.py`;
`exp_mx.py`, `exp_state_mx.py`, `cmpstate_mx.py`, `jitter.py`, `capflips.py`, `coldmx.py`; raw outputs `res/`, pictures `ab/`).
Evidence tags: **[M]** measured (raw in `work/extrap/res/` or run in this session), **[I]** inference.

## 1. What the render reads (disassembly, `work/extrap/dis/`, `stages.py`)
Pass (`$7a88`..`$7b74`): logic `f9fa..11396 fe50 ff76 1003c`, then `17c24` (clear span buffer), `100b4` road geometry, `17c42` road draw, `10a5e 10a98 e218 e2e8 1182e 11a3c e316 dd50`,
`18318` horizon, `e406` objects, `ef7a` HUD+clouds, `18888 18c86 18f0e`, flip. Tail `$7b7a..$7bac`: raster-band copy, `$100e++`, `$5ff8 += $130c`, `$1338`, `$11c2`.
What carries the pose (every item consumes `$130c` = speed per pass, so calling it with `$130c = k` advances by k world units):
* three ring generators: `fe50` (rings `$13b0/$17b0`, head `$13ae`; `fe50: move.w $130c.w,d0`), `ff76` (curve ring `$1bbc`, head `$1bba`), `1003c` (hill ring `$23c8`, head `$23c6`; `01003e: move.w $130c.w,d7`),
* `100b4` itself integrates the stripe phase: `0101d8: move.w $130c.w,d0 / 0101dc: add.w $1308.w,d0` (`$1308/$130a`),
* `10a98` horizon scroll (`010ab0: muls.w $130c.w,d1`, `$12f8/$12fa/$12fc`), `dd50` clouds (from `$12fc`),
* object distance `$20(a0)` of the 32 slots `$2d80+` (`e2e8: sub.w $130c.w,d0`), projected by `e316/e338` through the geometry tables; the 4 AI cars `$2ca0` move by `($130c - $22(a0))` in `1182e` (`01184c..011856`),
* lateral position `$1318` (steering), per-tick change measured 4..8 units.
`$5ff8` is read only by the minimap (`f2de`), not by the road. Collisions/debris (`18c86`, `18f0e`, after the draw) are logic: not run in extras.
Camera pose of pass n is after the tick's ring consumption; the extra at fraction f shows pose n + f*v (v = this tick's `$130c`).

## 2. Mechanism (as built)
`newsync` (replaces `mt_sync`): `jsr $d1ca` flip, PEND=1, publish `$1302/$1304 -> $12fe/$1300` (raster bands, immediately so the VBL that latches the frame uses its own), flip log, `extras`, then mt_sync's sleep unchanged.
`mx_pre` (`$7b46`, before `e406`): copies the 48 object slots `$2c68..$36e7` (2688 B) to `PREBUF` unless `NOWANT` (no extra fitted last tick: an 8 MHz machine pays one test). Needed because `18888/18c86/18f0e` change the slots after the draw
(debris/collision) and `e406` itself rewrites slot x/y (measured: only bytes 0..3).
`extras` (deadline-aware, CLK in 1/300 s): per candidate frame: start clock, duration estimate DEXT (running average of measured VBL-quantised durations; first guess = main pass duration), skip if `start + DEXT + SAFE(0) > NEXT`;
display time = start + DEXT + 1 VBL; f = (display - main display)/36; k = round(f*v) (cap v); skip if k <= already advanced. Per frame: restore slots from PREBUF, `$130c`=delta: `fe50 ff76 1003c 17c24 100b4`, PEND latch guard (as `mt_pre`),
`17c42 10a5e 10a98`, slots `e2e8` with total k, AI-car step `$20 -= round((v - $22)*k/v)` (only visible cars, only inside 0..$3ff), `$130c`=v, `e316 dd50 18318 e406`, HUD (the `ef7a` list; message ticker `11ef0` run with its state
`$1198-$11b3 + $10f8` saved/restored around the call, so the extra's buffer gets the next ticker step early and the main frame does the real one), flip, PEND, publish bands, log.
Lateral: `$1318 = LAT0 + round(dLat*k/v)`, dLat = change since the previous tick (|dLat| <= 12), else 0.
Group end (`restoreundo`): static ranges (`$12f8 $1308 $1316-$1325 $13a2-$13b1 $1bb0-$1bbb $23bc-$23c7 $27c8-$27ed`, cloud x/y x12, HUD flags `$10bc $11c4-$11cf`, face state `$10ec-$10f9`), ring head windows (32/32/64/32 B at the live head),
the 48 slots, 100 sprite-kernel self-modified longs (`KTAB`, from a full-race write trace) and the HUD face RNG `$dafe`; `$130c`=v. Not restored (display history, consistent with what the buffers hold): cloud `$28/$2a`, HUD erase pointers `$10c2-$10c8`, geometry/raster scratch.
Extras are skipped when: no slot copy, kill switch `X_OFF`, `$130c`=0 or > 31, `$1024`!=0, `$1021`!=2. Test knob `X_TEST` n (n extras at f=j/(n+1), no clock, no guard), n+$80 = zero-advance extras. Counters `NFRAMES/NGROUPS/NTICKS`, skip reasons `RSN`, flip log `FLOG/KLOG`.
Size: payload 33,216 B (`$b2700-$ba8bf`); `msrpatch.py verify` ALL OK; `build --only pp_bigram_cache mt_clock mt_pre mx_pre mx_sync --out build/mx_only` built.

## 3. Measurements
**Gate A (emulator, `gate3.py`, bit-exact model: whole 1 MB RAM matched Hatari except IRQ-driven bytes `cmp_emu.py`):** stock vs mx, state `$1000-$7000` + code area `$7000-$19000`, every pass, 150 ticks x (start/zig, start/upleft, up/zig), 2-3 extras per tick:
differing bytes = only the 11-14 bytes of the patch sites themselves; masked: cloud `$28/$2a`, geometry/raster scratch, order list, sound. **Main frames pixel-identical to stock in every one of the 150 ticks (`pix3.py`: 0 frames differ).**
Negative controls (`neg.py`): kernel table off 30/100 frames differ; ring window shortened 186 logic bytes differ; undo range shortened (Hatari) 136 addresses.
**Gate B (Hatari 2.6.1, STE TOS 1.62, per-pass state at `$7b86`, `exp_state_mx.py`/`cmpstate_mx.py`, raw `res/state_gate_final.txt`):**
```
A_start vs X_start16: common passes 199 (keys 108..306), differing addresses 0   (201 extra frames drawn)
A_start vs X_start32: common 199, differing 0                                      (416 extra frames)
A_start vs X_start8 : common 189, differing 0                                      (0 extra frames)
A_drive vs X_drive16: common 257 (keys 0..1706: time-out and restart inside), differing 0 (8 extra frames; restart is standing)
```
Mask: `$1004-$100d` (buffer parity), `$12f0-$1307 $12fe-$1301` (raster scratch), `$3732-$374f $37c0-$37cb`, blob data. Window start 100..200 passes after the live apply.
**Rates (Hatari, `exp_mx.py`, 600 VBL, snapshot `mx_start_p200.sav` = driving, `$6105`=1; A/T rows 400 VBL, `res/rate_*`):**
| build | 8 MHz | 16 MHz | 32 MHz |
|---|---|---|---|
| stock | 8.25 fps, 82.5 pos/s | 16.4 fps, **150.6 pos/s** | 16.75 fps, 153.6 pos/s |
| mt (fixed tick) | 8.38 fps | 8.38 fps | 8.38 fps |
| mt + mx (this) | 8.33 fps (0 extras, 100 passes) | **16.50 fps** (98 extras/100 passes) | **25.25 fps** (203 extras/100 passes) |
World speed with mx: 83.25 / 81.9 / 82.1 pos/s = the stock STE rate. Frame spacing (`jitter.py`, flip log): 16 MHz every 18 units (3 VBL) exactly, main frames every 36; 32 MHz mostly every 12 units, main interval 36 in 93/95 samples (30 and 42 once each).
Frame period is limited by the VBL latch (one buffer flip per VBL at best) and by the VBL-quantised clock; 32 MHz could reach about 4-5 frames/tick with a finer clock [I]. 8 MHz: no extra fits (work 4.7 VBL of 6), behaves as `mt` (`NOWANT` removes even the slot copy).
**Zero-advance test (`zerolong.py`, 700 ticks x 3 runs, extras at k=0 must equal the main frame):** identical except talking-face mouth (random per render), minimap box (the stock minimap draws one step further on the frame after a step commit), top-right sky cloud residue,
message text area (extras show the NEXT ticker step: `msgcons.py` 700 ticks, 232 changing ticks: every extra frame equals main n or main n+1, never non-monotone, patterns AA/NN only), HUD puff animation rows 163-171 (frame +1); about 5 % of extra frames have >12 differing bytes outside these.
Screenshots: `work/extrap/ab/emu_start_p20_sheet.png` (main n, 3 extras, main n+1, 3 extras; emulator, not Hatari), `emu_start_p20_strip.png` (road corner crops). **Hatari screenshots of extra frames were not taken** (`capflips.py` written, not run).

## 4. Visible / different from stock (needs the user's approval, hence default: no)
New pictures between ticks (2 / 3 frames per tick on 16 / 32 MHz); object/AI-car/road/scroll/cloud/stripe poses between ticks; main frames identical to stock. Extras differ from main frames in the categories of the zero-advance test.
The radio-message typing runs one character early in extra frames; the bottom-left puff animation is held; talking-face mouth changes per frame.
Alarm sound flag `$11ce` is cleared during extras so the HUD item does not beep twice (the main frame plays it).

## 5. Risks and what remains
* **Not done:** cold-boot gates (STE 1/4 MB, Mega STE, TT) with `build/mx_only` (`coldmx.py` written, not run); 60 Hz (VBLU handling added: 5 or 6 units per VBL from `$ff820a`, untested); Hatari screenshots; long play session; real hardware.
* Overrun: a frame can end up to 1 VBL after the tick is due (SAFE=0, clock is VBL-granular); the tick grid does not drift (mt_sync resync), the main frame is then late by <= 1 VBL (observed 2 of 95).
* AI cars/objects are extrapolated linearly (cars by relative speed); steering `$1318` by the previous tick's change (measured at f=1: mean differing bytes vs the true next frame 276/438 with prediction vs 911/1066 without, 254/297 with the exact value, `latq.py`).
  A direction change inside a tick overshoots up to one tick's step. Collisions are logic-only: an extra can show a sprite overlap one tick before the collision is processed. HUD stopwatch/score are per tick (not extrapolated).
* The kernel patch table (`KTAB`, 100 longs) comes from one race of one track; other scenery could patch other longs: then a main frame may differ from stock by a few bytes (stock stale-immediate quirk), never state.
* `mx_sync` depends on `mx_pre`, `mt_clock`, `mt_pre` (no dependency check in the tool); `$B9000-$BA880` blobs/data. Speeds > 31 skip extras.
* Observation about `mt_sync` (not changed): it publishes `$12fe/$1300` after the sleep (up to a tick after the flip), so the raster bands of a frame lag; `mx_sync` publishes right after the flip.

## 6. Integration wave: kernel-table caveat restated (MSRIntegrate)
`KTAB` (the 100 self-modified sprite-kernel longs `mx_sync` restores) comes from ONE race on ONE track (the first level). Not checked on a second track here (mx stays `default: no`; see `integration.md` for which other tracks could be reached at all). Anything beyond the first track is **[INFERENCE]**: another level's scenery could patch other kernel longs, then a main frame might differ from stock by a few bytes. Not required for shipping `mt_*`/`rd_*`.
