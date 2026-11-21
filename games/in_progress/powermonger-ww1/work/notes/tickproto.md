# Powermonger WW1: the fixed-rate tick — live prototype

The 1990 tick design (`../../done/powermonger/patches/tick_*.s`, `REPORT.md` section 3)
transposed to the WW1 engine. This is a **live prototype** (assembled and applied to the
running game through the debugger), not yet a delivered patch. Source:
`work/tickproto/tick.s`, build: `vasmm68k_mot -Fbin -o tick.bin tick.s`.

Evidence tags as usual; the emulator state is the map-view snapshot
(`work/snapshots/mapview.sav`, 1 MB STE, TOS 1.62, 8 MHz unless stated).

## 1. The pass kinds

The main loop is `$13d58..$145fe` (back edge `bra.w $13d58`), see `frameloop.md` section 1.

| kind | when | runs |
|---|---|---|
| **T** | a world tick is due | the original pass |
| **S** | another tick is owed | the tick logic + the men; the render skipped (the speed countdown parked at 2) |
| **R** | ahead of real time | render only: the head jumps to `$13dcc`; the weather (`$13e24`) and the men (`$13e36`) wrappers skip themselves; the terrain (`$13e42`) runs |

Real time: the VBL counter `$71b7c` (low word `$71b7e`) delta × (6 at 50 Hz / 5 at 60 Hz,
the shifter sync bit `$ff820a` bit 1) in 1/300 s units; **TICK = 75 = 0.25 s = 4.00 steps/s**
(the 1990 rate). A backwards counter or a gap > 60 VBL re-syncs; **a backlog beyond 3 ticks
is dropped** (keep one owed tick) so a slow machine cannot starve the render.

## 2. The sites (live original bytes, for the future patch headers)

| site | original bytes | becomes | what |
|---|---|---|---|
| `$13da0` | `4a79 0005a856` (`tst.w $5a856`) | `jmp $72000` | the pass head -> the tick decision |
| `$13e24` | `4eb9 0001b90a` (`jsr $1b90a`) | `jmp $720e0` | the weather wrapper (skip on R) |
| `$13e36` | `4eb9 000158b2` (`jsr $158b2`) | `jmp $72110` | the men/entity wrapper (skip on R) |
| `$13e42` | `4eb9 000074e0` (`jsr $74e0`) | `jmp $72140` | the terrain wrapper (skip on S) |
| `$7e6` | `0002ed90` | `00072180` | the right-latch copy source: the world counter -> PASS |
| `$842` | `0002ed90` | `00072180` | the left-latch copy source |
| `$144b4` | `0002ed90` | `00072180` | the tail's latch-expiry read |

`PASS` is bumped every pass (T, S and R) at `$72180`, so a click lives one pass, not one
tick (the 1990 `tick_click` rule). Variables: `PASS $72180`, `ACC $72184`,
`LASTVBL $72188`, `KIND $7218a`; code at `$72000` (the free span `$72000-$c1cff`).

## 3. Measured results [obs]

| run | world rate |
|---|---:|
| unpatched, 8 MHz (standing) | **3.67 ticks/s** (the frame-coupled rate; 3.55-4.27 over runs) |
| patched, 8 MHz (standing) | **4.00 ticks/s** |
| patched, 16 MHz (standing) | **4.00 ticks/s** (unpatched 6.97: the 1.9x defect gone) |
| patched with TICK = 30 (10/s target), 8 MHz | 8.32 ticks/s — the S path runs the logic as fast as the machine allows, render skipped; no crash, the screen stays drawn |
| unpatched, 8 / 16 MHz (battle) | 3.67 / 7.13 |
| patched, 8 MHz (battle) | **3.89** (one tick short over a 9.3 s window; the battle ended during the run) |
| patched, 16 MHz (battle) | **4.00** |

The map-view screen remained live (mean 62.5, 165k bright px, no bus errors in the Hatari
log) after patching at both clocks; on the battle the scene kept rendering (activity 596 at
8 MHz, 96 at 16) with the world at 4/s.

## 4. Open gates before this can be a patch

- [ ] **60 Hz**: the delta math reads `$ff820a` bit 1; run a Mega STE / TOS 2.06 (60 Hz)
      cold boot with the patch and expect 4.00 (the 1990 game's `timing.md` section 11 gate).
- [ ] **State equality**: per-tick low-RAM equality against the unpatched game (the 1990
      tick gate: match by the tick counter, compare the whole low RAM, negative control).
      The map view is nearly static; use a scene with moving men (the command-cell RE is
      still pending) and a forced season change.
- [ ] **Click lifetime**: a `poke_click` must still be consumed in one pass (the PASS
      redirect) on both T and R passes.
- [ ] **Pause and the speed slider** (`$5a856`, `$5a852/$5a854`): pause must freeze the
      world without a burst at resume; the speed >1 setting (`$5a852`) interacts with the
      S-pass countdown park (the prototype assumes period 1, the map-view default).
- [ ] **The wrappers' R-pass skips in a live scene**: the men frozen between ticks (the
      point of the patch) and resuming exactly on the next tick.
- [ ] **Delivery**: the real patch in `WWIEDITN.PRG` (the carrier, `frameloop.md` section 4)
      with the verify-then-apply hook and the site table.

## 5. Gotchas found on the way (worth remembering)

- `vasmm68k_mot`: an `equ` label does NOT move the assembler's position; use `org` before
  each block or the code silently lays out sequentially (the first build crashed the game by
  jumping into mid-instruction).
- Hatari's debugger `w` takes **decimal** values; hex needs `$` (`w $addr $4e $b9 ...`).
  A bare `4e` is a parse error.
- Hatari's `m` output includes an ASCII column; strip it before parsing the bytes.
- The pass head is `$13d58`, not `$13dA0`: the scroll clamp runs first (the head hook must
  be at `$13da0`, after the clamp, or the camera stalls).
