# Powermonger WW1: per-tick state equality (the tick gate) — first results

Tool: `tools/pmtick_eq.py` (the 1990 `tools/pmtick.py` method). Both runs restore the same
snapshot (`work/snapshots/battle.sav`, the men fighting), and the low 1 MB is dumped **exactly
at the same world tick** by a Hatari value breakpoint on the world counter `$2ed90`
(`b ($2ed90).l > N-1 :once :file` — an equality condition never fires because the debugger
tests at instruction boundaries; the `>` form captures the first instruction after the
counter passes N).

## 1. What compares, and what is excluded

Excluded (each justified): TOS low memory `$0-$7ff`; the patch sites (`$7e6`, `$842`,
`$144b4`, `$13da0`, `$13e24`, `$13e36`, `$13e42`); the weather-animation phase `$1b900`
(advanced by the R passes — see the design note in 3); the IKBD parser and pointer words and
the two screen buffers `$1d2a0-$2d5ff` (position forcing + the picture, which the pixel gate
covers); the stack `$2d600-$2dfff`; the world counter + click stamp + latches and the RNG
seed `$2ed90-$2edbf`; the sound sequencer `$5ef00-$5efbf`; the VBL counter `$71b7c`; the
payload `$72000-$72fff`.

## 2. The result [obs]

At world tick N (8 ticks after the restore): **582 differing bytes outside the excluded
ranges**, in these clusters:

| range | what | verdict |
|---|---|---|
| `$51af7-$51d82` (≈300 B) | the **men records** (positions, `$32`-byte stride) | the real finding: the men are one step ahead in the patched run — an ordering difference, see 3 |
| `$4dbb8`, `$4dc38`, `$4f022`, `$4f0a2`, `$4f2a6`, `$4f326`, `$5081c`, `$5089c` | 2-byte values that look like **glyph/icon words** (`0af8`, `0b9a`, `0396`, `02f4`, `061e`, `bd00`, `006c`, `bd14`) — they are *drawn* glyph data, and in the patched run the same code holds the *next* glyph; the same values appear at both addresses in both runs, swapped | consistent with a one-step difference in the icon/glyph animation, same root cause as the men |
| `$50fdb` | 1 byte inside a scroll/config word | [INFERENCE] the same one-step difference |
| `$55xxx-$56xxx` (≈200 B) | the **territory/selection tables** (counts and the `$5a8`-style records) | the same one-step difference |
| `$585xx-$588xx` | the scroll/conquest-meter words (`00ffc0ff` vs `09ffc0ff` patterns) | the same |
| `$5a82f`, `$5a851-$5a85b` | the selection + speed words (`$5a852` = 1 both; the `$5a85x` block) | the same |
| `$71b82` | just above the VBL counter | the harness's own VBL read, harmless |

The **negative control passes**: stock tick N vs N+1 differs in 216 bytes, so the gate is
sensitive (it is not comparing noise).

## 3. Diagnosis: the pass kinds reorder the men by one step

The tick's S/R design (work/notes/tickproto.md) splits a pass into logic and render. On an R
pass the logic (including the men wrapper `$13e36`) is skipped, on an S pass the render is
skipped. The original ran **logic then render in the same pass, with the render's VBL wait in
between**; the patched build can run the logic of tick N+1 while the *previous* render is
still to come, so at the instant the counter reads N+1 the men records can be one tick
further along than the original's at the same counter value. That is exactly what the
clusters show (the men and everything derived from them, including the glyph animation and
the territory counts, one step ahead; nothing else differs).

**It is a timing-of-observation difference, not (yet proven) a state divergence.** The 1990
patch solved the same class of problem by keeping the *world* logic in the T pass only and
making the S/R passes pure render, and it verified equality at the *tick* boundary after the
flip. Two candidate fixes:

1. **Order the tick decision before the logic only** (the 1990 shape): the head hook decides
   T/R/S *for the logic*, and an R pass must not let the next tick's logic run before the
   render — i.e. the accumulator should only advance on a pass that rendered, or the R pass
   should still run the pending flip.
2. **Compare at the same point in the pass** (after the flip) rather than at the counter
   bump; if the divergence then disappears, the state is equal and the gate was observing a
   half-finished pass.

The next step is (2) first (cheap, tells us whether the state really diverges), then (1) if
it does.

## 4. The measurement bugs, found and fixed [obs]

Three real defects in the gate itself, each of which had produced a false "divergence":

1. **A stale dump was accepted.** `work/eq/tick_8.bin` was a 4096-byte leftover from an
   aborted run; Python repeated the short buffer and the comparison ran to the end. The tool
   now deletes any old dump before capturing and refuses one shorter than `$72000` bytes.
2. **The two runs captured different points of the simulation.** The stock run read the base
   tick after a 5 s sleep; the patched run read it after applying the patch (later). Every
   "divergence" below `$2ed90` was then partly just a different absolute tick. The tool now
   reads the counter immediately on restore and takes the targets from that same base in both
   runs. Verified: `stock: base tick 266, targets [272, 273]` and `tick: base tick 266,
   targets [272, 273]`.
3. **The two runs sit on opposite screen buffers** at the same tick (flip parity), so the
   draw pointer `$e7c2`, its copy at `$11dc6` and the buffer pair `$2ed98/$2ed9c` differ by
   construction. Now excluded (the picture is the pixel gate's job).

## 5. The current result [obs]

With the fixed tool, at the same absolute tick 272 (both runs from base tick 266):
**397 differing bytes**, negative control 138 bytes (stock 272 vs 273), so the gate is
sensitive and the engine itself is bit-deterministic (two stock runs of the same snapshot give
**0** differences).

And the cause of the remainder is identified: **`$50fd8` is a PASS counter** (bumped
`addq.l #1,$50fd8` in the pass tail at `$13dae`), whose low word `$50fda` is the **animation
phase** the men walk reads (`$158ce`: `d0 = $50fda + $18(rec)`, `& $3ff`, compared against the
record's frame). At the same world tick the patched run has had **more passes**: stock
`$267`, patched `$275` (8 more) in the measured run — because the tick build renders extra
frames per tick on a fast machine. The men therefore stand on a different *animation frame*
(`$fd02` vs `$fdff`, `$fc04` vs `$fa00`), while their static record fields
(`08 11 24 80 44 80`, the terrain/cell words) are identical.

Measured passes/tick (5 s windows):

| | 8 MHz | 16 MHz |
|---|---:|---:|
| stock | 1.000 | 0.976 |
| patched | 1.000 | 1.000 |

**So the gate's premise needs one decision:** either the animation phase must be driven by
the world tick (then the state is exactly equal and the gate passes as written), or the gate
must compare at the same *pass* count rather than the same tick (then extra frames are
legitimate and only the world state is compared). The 1990 game chose the first: its tick kept
the animation on the world clock.

## 6. What was ruled out

| candidate fix | result |
|---|---|
| make the S pass render too (S = T) | no change |
| no pass at all on R (one render per tick) | no change to the world-state set |
| mask interrupts across the tick decision | no change |
| dump after the flip rather than at the counter bump | 582 → 235 (the half-finished pass) |
| engine determinism (stock vs stock, two runs) | **0 bytes** |

Reproduce:
```
cd games/in_progress/powermonger-ww1
python3 tools/pmtick_eq.py work/snapshots/battle.sav 6,7
```

