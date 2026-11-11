# Midwinter 2 — in-game main loop & frame flip

Agent: FrameLoop. Read-only analysis; no game files patched. Snapshot used for all
dynamic work: `work/snapshots/ingame_foot_walking.sav` (on foot, walking, mouse mode).
Profile: `work/prof/walking.txt` (total_cycles = 35,321,256 ≈ 4.415 s @ 8 MHz ≈ 19.4 frames).

## 1. Scope

| Item | Address |
|---|---|
| Frame-loop function (setup prologue + infinite loop) | `$31440` entry; loop body `$31486`–`$315de` (`bra.w $31486`) |
| Flip routine (writes `$ff8201`) | `$26e98` (reached via jump-table stub `$4f36`) |
| Master 3D renderer (one call) | `$1dbbe` (stub `$5056`), scene renderer `$1dc12` |
| VBL handler (context) | `$26298`, increments `$7020` & `$770c` (`$262d0`/`$262d4`) |

Coverage: the loop body's ~40 direct calls account for **100 %** of profiled in-play
cycles; every one of the top-30 self-cycle functions (75.5 % of all cycles) is inside
the single renderer call `$1dbbe` (proved by runtime stack backtrace, §7).

## 2. Role

`$31440` is entered once when the "on foot / in vehicle" in-play state starts (caller
chain seen on the stack at flip time: `$2c6c8`→`$2c6ce`, `$2c616`→`$27406`). It runs a
setup prologue (`$31440`–`$31484`: clears `$40b6/$40b8/$7708`, copies game-clock
`$eb8c`→`$e218`, arms exit vector `$f92c = $323b2`), then falls into the frame loop
`$31486` which **never returns** during play. Each iteration = one presented frame:
read state → simulate → set up view → render the whole 3D scene + HUD → flip → housekeeping.

Exit conditions inside the loop: `$314c0 bne $315e2` (when `$2d4be` signals) and
`$314cc jmp $323b2` (when `$df80 ≠ 0`).

Inputs: game-state words (`$6220` mode, `$66e6/$66ea` camera, `$eb8c` clock, `$eb9x`
screen mgmt), IKBD state (written by the **interrupt** `$26882`, not polled here).
Outputs: the back screen buffer (`$67a6` = `$60000`/`$70000`), the video base register
`$ff8201/$ff8203`, and updated world/HUD state.

## 3. Call graph

```
$27406 / $2c6ce (in-play state dispatcher)
   └─ $31440  frame-loop function (setup once, then:)
        loop $31486 … $315de  (bra.w $31486)
          ├─ ~28 pre-render calls  ($3148a … $315a0)   logic / sim / view-setup
          ├─ $315a4 jsr $5056 → $1dbbe  MASTER RENDERER (scene renderer $1dc12 →
          │            $1d768,$1b996,$1d434,$1d8d4,$20088,$30f2c, … $38cd0,$3c5e2,$1fdf0)
          ├─ $315a8…$315c0  post-render/HUD ($320b4,$3264a,$326de,$32910,$3166c)
          ├─ $315c6 jsr $4f36 → $26e98  FLIP (movep → $ff8201)
          └─ $315ca…$315d8  post-flip housekeeping ($32db6,$26e6c,$1aaa4,$30f72)
```
Flip `$26e98` has exactly one code xref (`jmp $26e98.l` at `$4f36`, the jump-table stub);
the stub `jsr $4f36.w` has 106 call sites but only `$315c6` is the in-play per-frame flip
(confirmed dynamically, §7). `--xref ff8201` returns only `026ea2: lea.l $ff8201.l,a0`.

## 4. Ordered per-frame call list

Role from disassembly; **self %** = profile cycles bucketed at that exact entry (dispatchers
have low self %, real cost is in subtrees). Block-level **inclusive** cost is measured by HBL
timing (§6): pre-render block ≈ **17 %**, renderer `$1dbbe` ≈ **83 %**, post-render+flip+
housekeeping ≈ **0.1 %**.

| # | site | →target | role | self % |
|--:|---|---|---|--:|
|1|`$3148a`|`$32574`|video shift/scroll reg setup (`$17fc4`,`$181fa` from `$67ba<<$67be`)|0.00|
|2|`$31498`|`$2e36e`|screen/overlay mgmt (reads clock `$eb8c`-`$e218`, `$eb9a`)|0.03|
|3|`$3149e`|`$2ea04`|screen/page setup (clr `$df80`, a6=`$770e`)|0.18|
|4|`$314ba`|`$2d4be`|cond. state check; non-zero → exit loop (`$314c0`)|0.02|
|5|`$314d2`|`$2dad2`|state/flag update (gated by `$5362`)|0.01|
|6|`$31504`|`$2e756`|cond. (`$66da==30`) screen reload, sets `$eb90/$eb94`|0.00|
|7|`$31512`|`$2f4b8`|**sim** (reads mode `$6220`, table `$753a`)|0.03|
|8|`$31518`|`$2fa0a`|**sim** (camera `$66e6` vs `$4bfa8`, thresh `$200`)|0.02|
|9|`$3151e`|`$2f968`|**sim** (world slots `$efb0/$efb2`, a0=`$6f9c`)|0.00|
|10|`$31524`|`$2f726`|**sim** (`$efb4` cap `$3e8`, `$6750`)|0.01|
|11|`$3152a`|`$30130`|object-table clear (`$efc0`/`$b3aa` list, clr `8(a0)`)|0.29|
|12|`$31530`|`$3232c`|logic update|0.00|
|13|`$31536`|`$33b7c`|logic update|0.00|
|14|`$3153c`|`$350c4`|logic update|0.10|
|15|`$31542`|`$1aedc`|logic (stub `$50da`)|0.00|
|16|`$31546`|`$36ad8`|logic/sound|0.15|
|17|`$3154c`|`$32f06`|logic|0.00|
|18|`$31552`|`$34adc`|logic (largest pre-render self)|0.68|
|19|`$31558`|`$34bbe`|logic|0.02|
|20|`$3155e`|`$335ce`|logic|0.02|
|21|`$31564`|`$18e44`|logic (stub `$512e`)|0.00|
|22|`$31568`|`$1b43a`|logic (stub `$50d4`)|0.00|
|23|`$3156c`|`$32574`|video shift/scroll setup again|0.00|
|24|`$31570`|`$33bca`|**PLAYER SIM step** (→`$33bde`→integrator `$344ac`: `add.l d0,$66e6` / `add.l d1,$66ea`) — *SimTiming-confirmed 1×/frame*|0.00|
|25|`$31576`|`$359c2`|logic|0.20|
|26|`$3157c`|`$351a8`|logic|0.10|
|27|`$31582`|`$1a706`|**HUD/clock** (stub `$50b6`; writes `$180f6`–`$1813a`, `$770e` HUD record; `addq.l #1,$eb8c.l` on frame-countdown `$6290` expiry) — *SimTiming*|0.00|
|28|`$31586`|`$32ee0`|logic|0.01|
|29|`$3158c`|`$19f54`|logic (stub `$50b0`)|0.00|
|—|`$31590`|`tst $6298`|**render gate**: if ≠0 → `$1b6be` and SKIP render; else ↓|—|
|30|`$3159c`|`clr $7020`|reset UI VBL counter (not a wait)|—|
|31|`$315a0`|`$20272`|view/projection setup (camera `$66e6/$66ea`-`$6400`→`$18784/$18788`; consts `$a90/$900/$790`)|0.00|
|32|**`$315a4`**|**`$1dbbe`**|**MASTER RENDERER** (stub `$5056`). ≈**83 %** of frame (measured). Calls scene renderer `$1dc12`→`$1d768`(record init),`$1b996`(sky/screen bulk fill),`$1d434`,`$1d8d4`,`$20088`,`$1dcfa`,`$1d596`, and `$30f2c`; deep leaves `$38cd0`(12.5%),`$3c5e2`(10.6% span fill),`$1fdf0`(4.7% projection),`$3c58c`,`$3c02a`,`$3c080`,`$38b8c`|0.05 self|
|33|`$315a8`|`$320b4`|post-render HUD/status bar (mode `$6220==5` → `$770e`+`$20`)|0.00|
|34|`$315ae`|`$3264a`|post-render (reads `$7590`)|0.00|
|35|`$315b4`|`$326de`|post-render|0.00|
|36|`$315ba`|`$32910`|post-render|0.00|
|37|`$315c0`|`$3166c`|post-render|0.04|
|38|**`$315c6`**|**`$26e98`**|**FLIP** (stub `$4f36`) — see §5|0.02|
|39|`$315ca`|`$32db6`|post-flip|0.00|
|40|`$315d0`|`$26e6c`|post-flip event/index (reads `$7684`, indexes `$662e`→`$66d8/$66da`)|0.01|
|41|`$315d4`|`$1aaa4`|post-flip (stub `$50ce`)|0.00|
|42|`$315d8`|`$30f72`|post-flip|0.00|

*Scene-dependent leaves present in the profile but not executed in the steady walking
snapshot (0 hits in 12 s): `$30e30` (3.35 %, masked 4-plane sprite/cockpit blit, from
`$28cee`), `$28f4a` (1.82 %, from `$28f34`), `$2b01a` (1.71 %, from `$2ddf4`). `[INFERENCE]`
object/sprite draw pass under the renderer; fires only with sprites/vehicles on screen.*

## 5. Flip mechanism (`$26e98`)

```
26e98: movem.l d0-d2/a0/a6,-(a7)
26e9c: lea.l   $770e.w, a6          ; a6 -> {front=$770e, back=$7712}
26ea0: move.l  (a6), d0             ; d0 = front ptr ($770e)
26ea2: lea.l   $ff8201.l, a0        ; VIDEO_BASE_HI
26ea8: lsr.l   #8, d0               ; d0 = ptr>>8  (e.g. $000700)
26eaa: movep.w d0, 0(a0)            ; $ff8201=hi byte, $ff8203=lo byte  <-- THE FLIP
26eae: move.l  (a6), d0
26eb0: move.l  4(a6), (a6)          ; $770e <- $7712   (swap front/back)
26eb4: move.l  d0, 4(a6)            ; $7712 <- old $770e
26eb8: move.l  (a6), $67a6.w        ; $67a6 = new front = next DRAW target
26ebc: move.l  4(a6), $67aa.w       ; $67aa = new back  = DISPLAYED
26ec2: movem.l (a7)+,d0-d2/a0/a6 ; rts
```

It sets the video base to the buffer just drawn, then swaps `$770e`↔`$7712` and mirrors
them into `$67a6`(draw target used by the renderer at `$1dc06 move.l $67a6,$71c0`) and
`$67aa`(displayed). Only `$ff8201/$ff8203` are written — `$ff820d` (low byte) is never
touched, so buffers must stay 64 KB-aligned (`$60000`/`$70000`). `movep.w` is used because
`$ff8201`/`$ff8203` are odd-strided byte registers. Runs in **supervisor mode** (ISP `$8016`,
S=1 at the breakpoint) — required to write `$ff82xx`.

## 6. VBL-wait analysis (measured) — **there is none**

Five `:trace` probes (`e VBL`+`e HBL`) over 10 consecutive frames. ST frame = 313 scanlines;
abs = VBL·313 + HBL. Averages (scanlines → VBL → % of the 4013-scanline ≈ 12.8-VBL
instrumented frame):

| stage | probe pair | avg scanlines | VBL | % frame |
|---|---|--:|--:|--:|
| pre-render logic (28 calls) | loop_top`$31486` → rend_entry`$315a4` | 678 | 2.17 | **16.9 %** |
| **renderer** `$1dbbe` | rend_entry`$315a4` → rend_ret`$315a8` | 3330 | 10.64 | **83.0 %** |
| post-render + flip | rend_ret`$315a8` → flip`$26eaa` | 3 | 0.01 | 0.07 % |
| flip → loop end | flip`$26eaa` → loop_end`$315de` | 2 | 0.006 | 0.05 % |
| loop end → next loop top | `$315de` → `$31486` | 0 | 0 | 0 % |

Frame period = sum of stages with **no gap** ⇒ 100 % CPU-bound, free-running.

- **VBLs lost waiting per frame = 0.** The flip happens **3 scanlines** after the renderer
  returns, at whatever HBL that lands on (observed flips at HBL = 12, 41, 90, 187, 217, 240,
  278 … i.e. mid-screen, **not** in vertical blank). Next frame's loop-top is 2 scanlines
  after the flip, same VBL. Example (raw, §7): flip at VBL 417741/HBL 90 → next loop-top at
  VBL 417741/HBL 92 → next rend_entry at VBL 417743/HBL 27.
- Consequence: the game already does **not** pay the "wait-a-VBL-after-flip" cost that P4
  lists as a pacing candidate — there is nothing to remove. But because the base register is
  changed mid-scanline, tearing/roll is possible; if a tear-free flip is ever wanted it must
  be *added* (sync `$26e98` to VBL), costing up to 1 VBL/frame (≈8 %).
- Since the loop free-runs, world speed ∝ fps (baseline: 8 MHz→4.4 fps→16 u/s, 16 MHz→
  8.8 fps→44 u/s). This is the direct cause of the "runs too fast" symptom.

## 7. Verification (raw Hatari output)

**(a) Flip caller = `$315c6`** — break at the `movep` (`$26eaa`), dump ISP stack; the long
at `a7+20` is the return into the loop:
```
> b pc = $26eaa :trace :once :file /tmp/frameloop/hit.txt
  A0 00FF8201  A6 0000770E  A7 00008016  SR=2300 S=1
00026eaa 0188 0000   movep.w d0,($0000,a0) == $00ff8201
> m a7 96
00008016: 00 00 00 09 00 00 00 0c 00 0c 00 3a 00 04 4f 20   (saved d0,d1,d2,a0)
00008026: 00 07 d2 3c | 00 03 15 ca | 00 02 c6 cc | 00 02 c6 1a
                      ^ret $315ca (flip site $315c6)  ^loop fn caller  ^outer caller
> e VBL = #417714
```

**(b) Flip before/after** — break at entry `$26e98` and after the swap `$26ec2`, same frame:
```
BEFORE (@$26e98, VBL=417714):            AFTER (@$26ec2):
 $770e: 00 07 00 00 00 06 00 00           $770e: 00 06 00 00 00 07 00 00   (swapped)
 $ff8201: 06 00 00 00  (displaying $60000) $ff8201: 07 00 00 00  (displaying $70000)
 $67a6: 00 07 00 00 00 06 00 00           $67a6: 00 06 00 00 00 07 00 00   (draw target now $60000)
```
Proves: video base is set to the just-drawn buffer, then `$770e/$7712` and `$67a6/$67aa` swap.

**(c) Renderer owns every heavy leaf** — break at each top-self function's entry, dump the
stack, scan for a loop return address (`$3148e`..`$315de`). 17/17 captured leaves resolved to
`$315a8` = the return of `jsr $5056`→`$1dbbe` at `$315a4`:
```
038cd0,01fdf0,01b996,03c5e2,01fa54,01da92,01d434,01e668,01ecba,0200b4,
03c58c,03c02a,03c080,03bfa2,0385b4,038b8c  <- jsr@0315a4 -> 01dbbe  (all 17)
```
(`$1dbbe` header confirms: `jsr $505c`→`$1dc12` which `bsr $1d768`,`$1d434`,`$1d8d4`,`jsr
$20088`,`$1dcfa`,`$1d596`; plus `jsr $1b996`, `jsr $5002`→`$30f2c`.)

**(d) Timing** — see §6 table; raw probe sequence (excerpt):
```
loop_top  VBL=417728 HBL=14 | rend_entry VBL=417729 HBL=255 | rend_ret VBL=417741 HBL=87
flip VBL=417741 HBL=90 | loop_end VBL=417741 HBL=92 | loop_top VBL=417741 HBL=92
```

## 8. Data structures / variables touched by the loop

| addr | size | meaning |
|---|---|---|
| `$770e` / `$7712` | long ×2 | front / back screen-buffer pointers (swapped by flip) |
| `$67a6` / `$67aa` | long ×2 | mirror of the above: `$67a6`=draw target (renderer), `$67aa`=displayed |
| `$ff8201/$ff8203` | byte ×2 | video base hi/mid (written by flip via `movep`) |
| `$7020`/`$770c` | word | VBL counters (handler `addq #1`); `$7020` cleared at `$3159c`/frame, `$770c`=mod-6, neither read in the in-play loop |
| `$6220` | word | game/vehicle mode (sim `$2f4b8/$2f726`, HUD `$320b4`, render `$1dc06`) |
| `$66e6`/`$66ea` | long ×2 | camera/player position (integrator `$34504/$34508`; view setup `$20272`) |
| `$eb8c` | long | game clock (minutes); `addq.l #1` in HUD `$1a706` on `$6290` countdown expiry; `$753a[]`=reload table |
| `$6298` | word | render gate (≠0 ⇒ skip `$1dbbe` this frame) |
| `$759e/$75a0/$75a2` | word ×3 | IKBD packet state — written by the **interrupt** `$26882` only, not polled in the loop |
| `$18784/$18788`,`$18772-$18776` | word | view origin / projection constants (set by `$20272`) |

## 9. Logic vs rendering — separability verdict

**Separable: YES, cleanly.** The loop is a flat sequence of ~42 independent `jsr`s:

- **Logic/simulation** = the pre-render block `$3148a`–`$315a0` (calls #1–#31), ≈17 % of the
  frame. Contains the player integrator `$33bca`(#24, →`$344ac`:`add.l d0,$66e6`), the world/
  object sim cluster `$2f4b8/$2fa0a/$2f968/$2f726`(#7–#10), the game clock + HUD writer
  `$1a706`(#27, `addq.l #1,$eb8c`), and view setup `$20272`(#31). Input is **not** here — it
  arrives via the IKBD interrupt `$26882`, so logic reads already-latched state.
- **Rendering** = the single call `$1dbbe`(#32), ≈83 % of the frame, self-contained: it reads
  world/camera state and writes only the back buffer `$67a6`. It does not feed logic.
- **Flip + HUD + housekeeping** = #33–#42, ≈0.1 %.

Dependency is one-directional (logic writes state → render reads it), and there is **no VBL
wait** coupling them. Therefore **P3 option B is directly implementable**: run the pre-render
block `k` times (k = elapsed VBLs / VBLs-per-logic-step) and call `$1dbbe` + flip once. Logic
is cheap (17 %), so even k = 2–3 on a 16 MHz machine adds little. Caveats (SimTiming):
replicating the block also re-runs the idempotent HUD writes (`$1a706`→`$180f6..$1813a`,
harmless) and advances the game clock `$eb8c` k× per rendered frame — which is the *desired*
real-time behaviour, provided the `$753a`/`$6290` reload table is left untouched. The
render-gate `$6298` and exit checks (`$2d4be`/`$df80`) must be evaluated once per rendered
frame, not per logic step, to avoid k× exit latency.

## 10. Optimisation opportunities (STE / blitter)

| target | idea | est. saving (% frame) | risk |
|---|---|--:|---|
| renderer `$1dbbe` subtree | **all** P4 render work lives here (83 % of frame). A 10 % cut in renderer cost = ~8.3 % of frame, ~1:1 fps gain | up to ~40 % (blitter fills + span table) | med/high |
| span filler `$3c5e2` (10.6 % self) | replace `mulu #320` + `jmp (a1)` with a table entry; wider stores | 3–6 % | med (pixel-exact) |
| bulk fills `$1b996`(sky/screen,4.4 %),`$1d768`(record init,4.5 %) | STE **blitter** fill/copy. No VBL idle exists, so blitter must beat CPU in HOG mode (CPU halts during blit) — benchmark per-op | 4–8 % | high (HOG overlap) |
| projection `$1fdf0`/`$3c02a`/`$3c080` (muls/divs, ~9 %) | reciprocal tables / shift scaling | 3–5 % | med (precision) |
| cockpit/sprite blit `$30e30` (3.35 %, conditional) | draw once into both buffers; clip 3D view to the window instead of re-masking per frame | 2–3 % (vehicle scenes) | med |
| flip `$26e98` | leave async (0 cost today). Only if tearing matters: add VBL sync (**costs** ≤1 VBL ≈ 8 %) or triple-buffer (needs a 3rd 64 KB-aligned buffer; RAM allows at 2 MB) | −8 % (sync) / 0 (triple) | low |
| pre-render logic (17 %) | not worth optimising for speed, but it is the block P3 replicates; keep it side-effect-clean & idempotent | — | low |

**Visual-tradeoff removable:** the per-frame `clr $7020` + HUD status-bar setup (`$320b4`,
mode-gated) and the conditional cockpit re-mask (`$30e30`) could be drawn once / only on
change if a small visual difference is accepted.
