# Moonshine Racers: frame pacing, per-pass state and a fixed-rate tick (prototype)

Scope: the flip/pacing mechanism (rendering.md §6 item 1), the inventory of state that advances per *frame* rather than
per *time* (item 2), and a prototype fixed-rate logic tick that decouples game speed from frame rate (item 3).
Everything here was measured on snapshots with **live patches** (`loadbin`/`w` at a one-shot breakpoint) — no file was
touched, `originals/` is untouched, and `tools/msrpatch.py` (another agent's work) was not used. Machine: Hatari 2.6.1,
STE, TOS 1.62, 1 MB, 50 Hz unless a row says otherwise. Unproven statements are marked `[INFERENCE]`.

Snapshots: `work/snapshots/ste1m_race_start.sav` (driving, `$6105=$01` held up, speed `$130c`=10 at the plateau,
`$10d2`=10136 = the race-clock step), `ste1m_race_grid.sav` (standing on the grid), `ste1m_race_drive.sav` (mid-race,
the time-out 4 passes ahead).

Scratch tools (this study, `work/timing/`): `tlib.py` (harness + breakpoint-chain helpers), `live.py` (vasm +
`loadbin`/`w`), `tick.s` + `tickpatch.py` (the prototype blob and its sites), `exp_tick.py` (rate: two one-shot `VBL >`
breakpoints whose files read `$5ff8/$100e/$10ce/$130c`/`$ff820a`, so window length and deltas are taken with the CPU
halted at the same instant), `exp_state.py` + `cmpstate.py` (per-pass state equality), `who*.py`/`dbg*.py` (the
`$d1e4` investigation), `sync.s`/`sync2.s`/`sync3.s` (the failed in-place `$d1e4` variants, kept as evidence).

## 1. The frame pacing mechanism: what `$d1e4` does

### 1.1 Code (from `work/dumps/ram_race_start.bin`)

```
00d1e4:  0c390002 0000611a   cmpi.b #$2, $611a.l      ; floor: 2 VBLs since the last clear
00d1ec:  65f6               bcs.b  $d1e4
00d1ee:  6100ffda           bsr.w  $d1ca             ; flip
00d1f2:  61000012           bsr.w  $d206             ; wait for the NEXT VBL
00d1f6:  4239 0000611a      clr.b  $611a.l
00d1fc:  4e75               rts
00d1ca:  20381008           move.l $1008.w,d0        ; d0 = back buffer
00d1ce:  22381004           move.l $1004.w,d1        ; d1 = displayed
00d1d2:  21c01004           move.l d0,$1004.w
00d1d6:  21c11008           move.l d1,$1008.w
00d1da:  2400 / e05a        move.l d0,d2 / ror.w #8,d2
00d1de:  21c28200           move.l d2,$8200.w        ; $ff8200=$00, $ff8201=hi, $ff8203=mid; $ff820d untouched
00d206:  3f00               move.w d0,-(a7)
00d208:  1038 611a         move.b $611a.w,d0
00d20c:  b038 611a / 67fa   cmp.b $611a.w,d0 / beq.b $d20c      ; spin until the VBL handler bumps $611a
00d122:  5239 0000611a      addq.b #$1,$611a.l                  ; VBL ISR ($d11e)
007b74:  4eb9 0000d1e4      jsr $d1e4.l              ; the race loop's only call (last call of the pass)
```
`$d1e4` is called from exactly two places: `$7b74` (the race loop) and `$7496` (PP's position-table screen). A patch
must therefore splice **the call site**, not the routine (see §1.5).

### 1.2 Measured phase of a pass (8 MHz, driving)

`pace1.py` + `pace_an.py` (`work/timing/pace_ste1m_race_start.sav_8.raw`): breakpoints on `$7a88` (render start),
`$7b0a` (before the road draw), `$d1ca` (flip entry), `$d1f6` (after the post-flip wait), each logging `e VBL`,
`e FrameCycles`, `m $611a 2`, `m $1004 8`, `m $ff8200 4`; time = VBL·160256 + FrameCycles (frame-wrap offset fitted as
in `tools/msrstages.py`):

```
07a88 t= 0.000 VBL  611a=0 $1004=78000 $1008=70000 ff8201/03=78000
07b0a t= 0.777 VBL  611a=0
0d1ca t= 5.349 VBL  611a=5                 <- flip entered (nothing written yet)
0d1f6 t= 5.997 VBL  611a=6 $1004=70000 ff8201/03=70000   <- after the wait: new base programmed
07a88 t= 6.000 VBL  611a=0                 <- next pass starts exactly on the VBL edge
```
Per pass at 8 MHz driving: 0.78 VBL of logic, 4.57 VBL of drawing, flip, then 0.65 VBL of idle wait for the VBL edge.
The pass period is `ceil(work)`: work 5.35 → period 6.00.

### 1.3 The buffer scheme (exactly)

* Two screens, `$70000` and `$78000` (32,000 B each, 768 B gap). `$1004` = the buffer the shifter shows, `$1008` = the
  back buffer. `$d1ca` swaps the two longs and programs `$ff8201/$ff8203` from the new `$1004`.
* One owner per pass: the loop loads `a5 = $1008` once (`007a88: 2a78 1008 movea.l $1008.w,a5`), and every HUD routine
  re-reads `$1008` itself (`00f53c: 2a78 1008`), so all writes of a pass land in the same buffer.
* The shifter latches the video base **at the next VBL**, not at the write (ST hardware behaviour; the trace in §1.2
  shows the write at 5.349 and the game's own wait ending at 5.997 — the wait exists only because the latch is later
  `[INFERENCE: hardware documentation + the stock code's structure; Hatari does not expose "what is displayed"]`).
  Until that latch the **old** front buffer, which is now the back buffer, is still on screen.
* Therefore the post-flip wait is *load-bearing*: it must hold the CPU until the latch, before the first write into the
  new back buffer. The first such write is at `$17c42` (`007b0a: 4eb9 00017c42 jsr $17c42.l`), 0.78 VBL after the flip.
* The 2-VBL floor is **dead weight at 8 MHz**: the only readers of `$611a` are `$d122` (increment), `$d1e4/$d1ec`
  (floor), `$d1f6` (clear), `$d208/$d20c` (wait) and `00df20: c038 611a and.b $611a.w,d0` in `$df1e` (the car-sprite
  wheel animation), which `--xref df1e` shows is called only from `0075b4` (the intro/pit sequence), never from the
  race loop. In the race the floor does nothing but set a minimum period (2 VBL + the wait = 3 VBL) — which is exactly
  the 16.67 fps ceiling measured at 16 and 32 MHz.
* The raster-table double buffer is tied to the flip: `007b7a: 31f8 1304 1300 move.w $1304.w,$1300.w` and
  `007b80: 31f8 1302 12fe` publish the horizon band's new top/bottom line (`$12fe/$1300`, read by the VBL handler at
  `00d57c: 303812fe` / `00d580: 32381300`) immediately after the flip. This position must be kept (§4.4).

### 1.4 Corrected estimate for item 1 (the "+4 % standing / +10 % driving" claim)

The claim's rationale — "overlap road geometry `$100b4` with the wait" — is **wrong**: `$100b4` already runs *before*
the wait (after the wait only the two raster-table moves at `$7b7a` and the 0.05 VBL tail `$7b86`..`$7bac` run), so
nothing can be overlapped. What actually happens when the wait is
replaced by a latch guard before `$17c42` is that **the pass period stops being rounded up to a whole VBL**: the guard
only has to cover the gap from the flip to the latch (0.64 VBL at 8 MHz driving), and the 0.78 VBL of logic before
`$17c42` already covers it, so the guard never waits and the period becomes the work time. Variant B (wait removed
entirely — which tears) measures that work time: 5.357 VBL/pass.

Measured with the **call-site** build (`$7b74` → `newsync`, `$7b0a` → guard; the same blob with `TICK=0`, so no pacer):

| build | clock | pass/s | VBL/pass | `$5ff8`/s | `$10ce`/s | vs stock |
|---|---:|---:|---:|---:|---:|---:|
| stock | 8 | 8.333 | 6.000 | 83.33 | 1.333 | |
| sync fix | 8 | **9.333** | **5.357** | 93.33 | 1.500 | **+12.0 %** |
| stock | 16 | 16.667 | 3.000 | 166.67 | 2.583 | |
| sync fix | 16 | 16.667 | 3.000 | 166.50 | 2.583 | 0 % |
| stock | 32 | 16.667 | 3.000 | 166.67 | 2.583 | |
| sync fix | 32 | **25.833** | **1.935** | 229.67 | 4.000 | **+55 %** |
| stock, grid | 8 | 9.833 | 5.085 | 0 | 0 | |
| sync fix, grid | 8 | **10.000** | **5.000** | 0 | 0 | **+1.7 %** |

So the correct numbers are **+12 % driving** (not +10 %) and **+1.7 % standing** (not +4 %) at 8 MHz, with the basis
above; and the floor removal matters only on faster machines (+55 % at 32 MHz; nothing at 16 MHz because the pass is
2.68 VBL of work rounded to 3). All of those gains are *game speed* unless the tick (§3) holds the rate.

### 1.5 Trap found: never patch `$d1e4` in place

Overwriting `$d1e4`'s first 6 bytes with `jmp <blob>` (the obvious patch) makes the **old tail run as well**: the hit
sequence is `7b74 d1e4 d1ca d1ec d1ee d1ca 7b86` per pass (96 flips for 49 passes over 300 VBL; `who4.py`), i.e. after
the blob's flip the CPU resumes at `$d1ec` (the orphaned `bcs.b $d1e4` / `bsr.w $d1ca` / `bsr.w $d206` / `clr` / `rts`;
the hit set shows a `$d1ec` return frame, but how it gets there was not isolated), so the flip runs twice and the old
VBL wait still happens. Three variants
built that way (`sync.s`, `sync2.s`, `sync3.s`) all measured 6.977 VBL/pass at 8 MHz and 4.0 at 16 MHz — *slower* than
stock, and they first looked like a refutation of item 1. Nothing in the image references
`$d1ec`/`$d1ee` (`--xref` empty); **the safe recipe is to splice the call site `$7b74`** (and
`$7b0a`), leaving `$d1e4` byte-identical. That build gives +12 % and is byte-exact (§4.4).

## 2. What advances per pass rather than per time

The race pass is `$796a`..`$7bac`: head (`$796a`..`$7a88`), 18 logic calls (`$f9fa`..`$1003c`), `$17c24`, `$100b4`,
`$17c42`, `$10a5e/$10a98`, `$e218`..`$dd50`, `$18318`, `$e406`, `$ef7a`, `$18888/$18c86/$18f0e`, `$d1e4`.

| variable | addr | writer (disassembly) | cadence | scaling need |
|---|---|---|---|---|
| world position | `$5ff8` | `007b90: d1785ff8 add.w d0,$5ff8.w` (d0 = `$130c`) | per pass | the game speed |
| distance / score | `$11c2` | `007ba8: d17811c2 add.w d0,$11c2.w` (`d0 = $130c>>3`, `007ba6 e648`) | per pass | same |
| stripe phase | `$1338` | `007b94..007ba2` (`$1338 + $130c`, wrap at `$b`) | per pass | same |
| pass counter | `$100e` | `007b86: 5278100e addq.w #$1,$100e.w` | per pass | gates the pass (§ start lights etc.) |
| speed word | `$130c` | `010d98: 31c1130c move.w d1,$130c.w` | per pass | from the accumulator |
| speed accumulator | `$10d8` | `010d86: d282 add.l d2,d1` / `010d8c: 21c110d8`; tables `$10ae6..$10b06`, `$1018` | per pass | integral: the tick |
| race clock | `$10ce` | `0117aa: d082 add.l d2,d0` / `0117ac: 21c010ce` (`d2 = $10d2`) | per pass | real seconds only with a fixed pass rate |
| race-clock step | `$10d2` | `00ee8e: 31c010d2` (table `$edcc`, `mulu $57890`, `divu #$c8`); cleared `00fb3c` | at race start | = clock per pass |
| time-up flag | `$1226` | `0117be: 11fc0005 1226` when the clock's high word ≥ `$ff` | per pass | follows `$10ce` |
| steering | `$1318` | `010f0e/010f14/010fcc/011026/0110fe/0111ac/0111b4` (input `$6105`, curve `$1bbc`), `$1312`,`$1314`,`$1324`,`$1224`,`$121e`,`$121c` | per pass | the tick |
| track/hill stream | `$23c8` ring, `$27da`, `$12a4` | `01003c` consumes **one sample per speed unit** (`01003e: 3e38130c move.w $130c.w,d7`, `dbeq d7,$10062`) | per pass | keep on the tick (integer units) |
| opponents/AI (36 slots) | `$29c8`, `$2c68`, stride `$38` | `00e406` sort, `00e598` dispatch, `01182e` (overtaking), `011a3c`, `011230`, `0112c4` | per pass | keep on the tick |
| race position | `$10ca` | `011890: 31c510ca` (1..`$63`) | per pass | keep |
| voice/radio timers | `$1214`..`$1217` | `00fba8`, `00fc9c`, `00fcf4`, reloads `00fc24`/`00fcca`/`00fd4e` | per pass | keep |
| fuel/counter | `$10c0` | `010e58: 537810c0` gated by `010e50: c078100e and.w $100e,d0` | every 8th pass | keep |
| start lights | `$102e`,`$1030` | `007a0a..007a5c` (`$100e` == `$102e` → light; == `$102e+$16` → go) | pass-counted | keep |
| race state machine | `$1024`,`$1027` | `00f9fa`, `00fa2c`, `011792` (`0117e4`), `00fb36` | pass-counted | keep |
| HUD "redraw twice" flags | `$11c4`..`$11cd` | `00f3b6`, `00f430`, `00f53c` (once per buffer) | per pass | keep |
| VBL counter since clear | `$611a` | `00d122` (ISR), cleared by `$d1f6` | **per VBL** | already real time |
| free-running VBL counter | `$611b` | `00d128` (ISR) | per VBL | read nowhere else |
| YM sound player | — | `$d486` → `008bf2` → `008c38`, from the VBL ISR | per VBL | already real time |
| raster palette | — | Timer B ISR `$d616` (41-47/frame, 12-14 k cycles/frame) | per VBL | already real time |

There is no other time source in the race: `--xref 4ba` (TOS `_hz_200`) is empty, `--xref 466` has no race hit, and
the MFP timer C is disabled (`006f72..006f8e`; only Timer B + ACIA are enabled).

Consequences:

* Game speed = pass rate × step, so it doubles with the frame rate today (`$5ff8` 83.33 → 166.67 units/s at 16 MHz,
  and the race clock 1.333 → 2.583 s-of-race per second — the HUD stopwatch is **frame-driven**, answering rendering.md
  Q3).
* A race ends on a pass count: `$10d2`=10136 → the clock's high word reaches `$ff` after 1649 passes (198 s at 8.33
  pass/s, 99 s at 16.7), then `$1226`=5 unwinds the state machine; the next race starts at pass 0 (`$78aa`) with its
  lights at passes 10..55 (§4.4 covers this sequence).

## 3. Design: a fixed-rate logic tick

### 3.1 Fixed number of passes per second, zero change to the pass body

The step cannot be scaled by elapsed time: the speed accumulator is an integer long fed by table lookups and `asr.l`
(`010d3e`, `010d48`), the steering clamp chain compares absolute units (`0110f4..0111aa`), the hill stream consumes
exactly `$130c` samples per pass (`01003e`), and the AI/collision code works in integer world units. Scaling those by
"VBLs elapsed" changes the integers and cannot be bit-exact. Running the **unchanged pass body once per tick** is exact
by construction — the same code sees the same inputs in the same order, just later in wall-clock time. This is the MW2
`tick_vbl`/`tick_head` shape (one tick = one game step, the clock decides when), not the Bresenham-scaled-step option.

### 3.2 Clock, rate, and what T means

* Clock `CLK` (long, `$b8f00`) in **1/300 s units**, advanced by the VBL handler: +5 for a 60 Hz frame, +6 for 50 Hz,
  from `$ffff820a` bit 1 (MW2's `tick_vbl` method). The tick rate is then independent of the refresh rate — which the
  stock game is not (measured: 60 Hz stock 8.5 pass/s vs 8.33 at 50 Hz).
* Target **T = 36 units = 6 VBL = 8.333 pass/s** = the stock 8 MHz STE driving rate (`$5ff8` +83.3 units/s). "Keep
  today's gameplay speed." T should be a multiple of 6 (50 Hz) and 5 (60 Hz) to land on VBL edges every pass; 30 and 60
  qualify at both, 36 is exact at 50 Hz and alternates 7/8 VBL at 60 Hz (measured 7.14/7.23 VBL → 8.3-8.4 pass/s, i.e.
  0.8 %, self-correcting through the accumulator).
* The presented frame rate equals the pass rate (one flip per pass), so **T is the frame-rate ceiling**: performance
  work buys the option to *lower* T (10 Hz at T=30, 12.5 Hz at T=24), not extra frames at a fixed T. Today's
  unoptimised 8 MHz pass is 5.357 VBL, so T=30 cannot be held (measured 9.333 pass/s instead of 10, §4.2) — ship T=36
  now and drop to T=30 once the pixel-identical render work (rendering.md §6 items 3-9, estimated 3.9-4.3 VBL) lands.

### 3.3 Hook sites (original bytes verified against `work/dumps/ram_race_start.bin`)

Blob at `$b8000` (free RAM `$b2700-$e8400` at 1 MB; the patch tool must pick a place that also fits at 4 MB). Three
splices, all in the `$7000-$19000` image, all verified byte-for-byte before applying:

| # | site | original bytes | new | why |
|---|---|---|---|---|
| 1 | `$d128` (VBL ISR) | `52 39 00 00 61 1b` `addq.b #1,$611b.l` | `4eb9 <vblclk>` | the clock; the displaced `addq.b` is the first instruction of the hook |
| 2 | `$7b74` (end of the pass) | `4e b9 00 00 d1 e4` `jsr $d1e4.l` | `4eb9 <newsync>` | flip + tick pacer (replaces the floor *and* the post-flip wait) |
| 3 | `$7b0a` (first back-buffer write) | `4e b9 00 01 7c 42` `jsr $17c42.l` | `4eb9 <pre17c42>` | the latch guard |

`$d1e4` itself, `$7b7a`/`$7b80` (the raster-table copy) and everything else stay byte-identical.

```
CLK   equ $b8f00     ; long, 1/300 s
NEXT  equ $b8f04     ; long, scheduled start of the next pass
PEND  equ $b8f08     ; byte, 1 = a flip awaits its VBL latch

vblclk: addq.b  #1,$611b.l          ; displaced instruction
        clr.b   PEND                ; the flip (if any) is latched by this VBL
        addq.l  #5,CLK.l            ; 60 Hz frame = 5 units
        btst    #1,$ffff820a.w      ; bit 1 set = 50 Hz
        beq.s   .done
        addq.l  #1,CLK.l            ; 50 Hz = 6 units
.done:  rts

newsync: jsr     $d1ca.l            ; the flip itself is untouched
        move.b  #1,PEND.l
        clr.b   $611a.l             ; keep the stock meaning of $611a for any other user
.rd:    move.l  CLK.l,d0            ; torn-read safe (re-read until stable)
        cmp.l   CLK.l,d0
        bne.s   .rd
        sub.l   NEXT.l,d0           ; lag behind the schedule
        bmi.s   .rd                 ; not due: sleep until the tick
        cmp.l   #MAXLAG,d0
        bls.s   .ok
        move.l  CLK.l,d0            ; > MAXLAG behind (pause key, disk, stall): resync, no burst
        cmp.l   CLK.l,d0
        bne.s   .rd
        move.l  d0,NEXT.l
.ok:    add.l   #TICK,NEXT.l
        rts

pre17c42:
        tst.b   PEND.l
        beq.s   .go                 ; the flipped buffer is already on screen
.w:     tst.b   PEND.l              ; else wait for the VBL that latches it
        bne.s   .w
.go:    jmp     $17c42.l
```
(`MAXLAG = 2·T` = 72 units with T=36; the blob code is 138 bytes at \$b8000-\$b8089, data at \$b8f00-\$b8f0b, `vasmm68k_mot -Fbin -m68000`.)

Design notes:
* The pacer sleeps at the end of the pass (inside `newsync`, after the flip), so passes start on the tick; the flip then
  sits at a constant offset from the tick edge and every frame is displayed for exactly T VBLs at 50 Hz.
* `MAXLAG` = MW2's `4*GRP` resync: after a stall longer than two ticks the schedule is reset instead of running a burst
  of passes (the F1 "wait for a key" loop `$79b4`, disk, PP's state-save). A stall shorter than 2 ticks is paid back at
  once (≤ 2 passes).
* When the machine is too slow the pacer simply does not sleep — the game runs slower than real time (as stock does)
  instead of skipping logic steps (which would break collision and the race clock).
* The 2-VBL floor disappears only for the race loop: `$d1e4` keeps its bytes, so `$7496` (PP's position-table screen) and
  the intro/title loops (`$735a`, `$73e6`, `$751c`) keep their own pacing.

### 3.4 What must stay exact, and the risks

Exact and verified (§4.4): every byte of `$1000-$13ff` + the 36 object slots `$2c68-$34ff` + the RNG long `$dae6`,
pass keyed by `$100e`, for 154 passes from the race start and 198 passes of `race_drive` — the latter spans the race
time-out (`$1226`=5 at pass 1649) and the restart with its lights (`$1030` 0→1 at pass 55). That covers results,
positions, the stopwatch, AI and collisions, because they are all functions of that state.

Risks:
* **A scene that cannot make T runs slow** (measured: T=30 at 8 MHz → 9.33 pass/s). Mitigation: margin (T=36 today);
  measure the worst scene (standing start with 4 cars + signs).
* **Feel on fast machines**: a 16 MHz machine today runs 16.67 pass/s (game speed 2× stock); with T=36 it runs 8.33.
  That is the intended decoupling but it *feels* 2× slower there; T is the knob and the performance work is what pays
  for raising it.
* **The 3-VBL floor removal is bundled in**: for the race loop the floor is gone (the pacer replaces it). If the pacer
  were ever disabled (T=0), the game runs at the work rate (§1.4) and game speed rises with it.
* **`$611a`**: the race loop no longer reads it, and `newsync` clears it so any other user keeps the stock meaning.
* **60 Hz**: exact by construction; measured 8.4 and 8.3 pass/s (T=36) at 8 and 16 MHz.
* **PP screensaver / state-save (`/`), `*` exit**: outside the race loop, untouched. `[INFERENCE]` no interference.
* **TT/Falcon**: the blob is plain 68000 and only reads `$ff820a` (present on both); no probe needed. Not tested.
* **Blob placement** at 4 MB is the patch tool's problem (`$B2700-$E8400` is free only at 1 MB).

## 4. Prototype results (raw)

All rows: `ste1m_race_start.sav` unless marked grid; 600-VBL windows with the CPU halted at both ends; `pass/s` = `$100e`
per second, `VBL/pass` = window / passes, `pos/s` = `$5ff8` units per second, `sw/s` = the race clock's high word per
second (1.333 = one "unit" per pass at 8.33 pass/s).

### 4.1 Tick build, T=36 (`python3 work/timing/exp_tick.py T ... 600 36`)

(`tools/msrbench.py` cannot apply a live patch, and its `pos_per_s` divides a position delta taken over the peek window by
a VBL span taken around the flip-count window — the two differ: 546 vs 300 VBL in the stock rows of
`work/notes/bench_ste_race_start.jsonl`. The rate here is measured by `exp_tick.py` with the CPU halted at both ends of
the same 600-VBL window; its stock rows reproduce the bench's pass rates and per-pass step exactly, 8.333/16.667/16.667
pass/s and 83.33/166.67/166.67 units/s, so the two methods agree on the stock game.)

```
ste1m_race_start 8 MHz : pass/s 8.333  VBL/pass 6.000  pos/s 83.33  sw/s 1.333
ste1m_race_start 16 MHz: pass/s 8.333  VBL/pass 6.000  pos/s 83.33  sw/s 1.333
ste1m_race_start 32 MHz: pass/s 8.333  VBL/pass 6.000  pos/s 83.33  sw/s 1.333
ste1m_race_grid   8 MHz: pass/s 8.333  VBL/pass 6.000  pos/s 0      sw/s 0
```
Stock, same windows (`work/notes/bench_ste_race_start.jsonl` + this study's runs): 8 MHz 8.333 pass/s / 83.33 units/s;
16 MHz 16.667 / 166.67; 32 MHz 16.667 / 166.67; grid 8 MHz 9.833 (the grid rows at 16/32 MHz were only measured with the
earlier blob revision; the pacer is identical, `[INFERENCE]` 8.333 there too). So the tick makes the world rate **identical at 8, 16 and 32 MHz** (83.33 `$5ff8` units per second, 10 units per pass,
one race-clock unit per pass, 6.000 VBL per pass) where the stock game doubles its speed with the clock. Repeated runs
of the 8 MHz row give the same 100 passes / 1000 units per 600 VBL (`+/- 0`: the tick is a schedule, not a race).

60 Hz (`w $ff820a $fc` after applying; T=36):
```
tick  8 MHz 60 Hz: pass/s 8.400 VBL/pass 7.143 pos/s 84.00 sw/s 1.300   (sync $fc)
tick 16 MHz 60 Hz: pass/s 8.300 VBL/pass 7.229 pos/s 83.00 sw/s 1.300
stock 8 MHz 60 Hz: pass/s 8.500 VBL/pass 7.059 pos/s 85.00 sw/s 1.300
```

### 4.2 Overload behaviour (T too short for the machine)

```
tick 8 MHz T=30: pass/s 9.333 VBL/pass 5.357 pos/s 93.33 sw/s 1.500
```
The 8 MHz STE cannot hold 5 VBL/pass with today's render (5.357 VBL of work), so the pacer never sleeps and the game
runs at the work rate — 12 % faster than stock rather than the intended 20 %, and *no* burst/skip. At 16 MHz the same
T=30 build would be tick-limited; not measured.

### 4.3 The sync fix on its own (`TICK=0`, i.e. the same blob with no pacer)

See the table in §1.4: 8 MHz driving **+12.0 %** (6.000 → 5.357 VBL/pass), 8 MHz grid **+1.7 %** (5.085 → 5.000),
16 MHz **0 %** (3.000 → 3.000), 32 MHz **+55 %** (3.000 → 1.935). At 32 MHz the world ran 229.67 units/s and the car
left the road (speed 10 → 6 within the window) — a direct demonstration of why the tick is needed with the floor gone.

### 4.4 Per-pass state equality, stock 8 MHz vs tick 8 MHz (T=36)

`python3 work/timing/exp_state.py {A,T} <snap> 8 <passes> <out>`: at every execution of `$7b86` (first instruction of
the tail, once per pass) a debugger file dumps `$1000` 1024 bytes, `$2c68` 2200 bytes and `$dae6` 4 bytes; captures are
keyed by the frame counter `$100e` and compared byte by byte (`cmpstate.py`).

```
A ste1m_race_start.sav 8 hits 160   T ste1m_race_start.sav 8 hits 168
common passes 154; differing addresses: 0

A ste1m_race_drive.sav 8 hits 204   T ste1m_race_drive.sav 8 hits 204
common passes 198; differing addresses: 0
```
Coverage inside those windows (dump of the same captures): the race restart resets `$100e` to 0 in both builds, the
start lights come up at pass 55 (`$1030` 0→1, `$102e`=33), and `race_drive` crosses the time-out at pass 1649
(`$1226`=5) in both. No skip, no double step, no reordering.

(The earlier version of the blob also copied the raster-table values `$1302/$1304` → `$12fe/$1300` from the guard, one
VBL later than stock; that changed `$12ff`/`$1301` by 1-2 in 6 of 154 / 11 of 154 passes. Keeping the two moves at
`$7b7a`, as above, removes that difference — hence the "0 differing addresses" with no exclusions.)

## 5. Consequences for the plan, and open points

1. **Item 1 (frame sync) is worth +12 % driving / +1.7 % standing at 8 MHz, not +4 %/+10 %,** and its rationale changes:
   nothing is overlapped; the pass period stops being rounded up to a whole VBL. It also removes the 3-VBL floor, which
   is what gives fast machines their frame rate — and, without the tick, an unplayable game speed (+55 % at 32 MHz).
2. **Item 2 (timing) is one blob with item 1** for the race loop: the pacer replaces the floor and the post-flip wait.
   With T=36 nothing of item 1's gain is visible at 8 MHz (the tick sets 6.00 VBL/pass); the gain is realised by
   lowering T to 30 once the render work lands. Recommend: build the patch with `TICK` as one `equ`, default 36, and a
   one-line change to 30 after P4/P5.
3. **T is a gameplay decision** (user): T=36 = stock 8 MHz driving speed but the grid runs 8.33 fps instead of 9.83 (the
   car is standing, so "game speed" is unaffected; only the frame rate), and a 16 MHz/Mega STE machine becomes 2× slower
   in wall-clock terms than today. T=30 = 20 % faster than stock at 8 MHz, exact at 50 and 60 Hz, sustainable only after
   the render work (5.357 VBL of work today).
4. **Gate for the patch tool**: the §4.4 capture (three `m` commands at `$7b86`, keyed by `$100e`) is a ready
   pixel-independent regression test; require 0 differing addresses over ≥150 passes from both snapshots, plus the rate
   check (`pass/s` equal at 8/16/32 MHz).
5. Not tested: real hardware, TT/Falcon/ST 1.04, 4 MB blob placement, a long multi-race session, `$1027`>1 ("race 2"),
   PP's state-save inside the race. The `$d1ec` entry mechanism of §1.5 is unexplained (only observed); the call-site
   recipe avoids it.

(Raw outputs kept next to the scripts: `res_tick0.txt.gz` = the §1.4 sync-only matrix, `res_v2.txt.gz` = grid sync-only
+ the T=36 matrix at 8/16/32 MHz, `res_v3.txt` = the final T=36 8 MHz rate and the state captures' summary,
`res_sync*.txt` = the failed in-place `$d1e4` variants. The 3-9 MB per-pass JSON captures were deleted after their
comparison; `exp_state.py <A|T> <snap> 8 <passes> <out.json>` regenerates them in ~30 s each.)
