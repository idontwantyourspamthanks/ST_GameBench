# Player Manager — New Game Setup Analysis (`PLAYERME`, 8 MHz STE 1 MB)

## Summary

Starting a **New Game** runs the routine at `$010cc0..$010d42` ("Please wait whilst the player manager game environment is being created..."). On an emulated 8 MHz Atari STE (1 MB, TOS 1.62), this takes **~7.7 minutes (~23,000 VBLs / ~460 s)** before advancing immediately to the Player-Manager edit screen (`$0108ae`).

It generates a starting universe of **1,065 players** (minimum quota **861** across 16 buckets = 4 Divisions × 4 Positions, capped at `quota + 15` per bucket for a max of 1,101) by **simulating every candidate player's entire career year-by-year from age 16** (youth training, match-by-match seasons, skill progression, division placement, aging, and retirement).

The ~8–10 minute wait is caused by a combination of **severe micro-level inefficiencies** (a 1-bit LFSR RNG + `divu.w` modulo consuming **~66–68% of all CPU cycles**) and **macro-level algorithmic waste** (brute-force rejection sampling of ~3,400 full careers, simulating match-by-match seasons whose outputs are overwritten every year, and redundant calculations).

---

## 1. What the Setup Routine Actually Does

### Outer loop (`$010cc0..$010d42`)
- Clears the 16-byte bucket count array at `a4-$38bc` (`$025dde`, where `a4 = $02969a`).
- Target minimum quotas at `a4-$7d22` (`$021978`):
  - **Div 1:** Keeper 23, Defender 76, Midfield 73, Forward 51 (223)
  - **Div 2:** Keeper 21, Defender 65, Midfield 67, Forward 47 (200)
  - **Div 3:** Keeper 24, Defender 78, Midfield 66, Forward 54 (222)
  - **Div 4:** Keeper 24, Defender 73, Midfield 65, Forward 54 (216)
  - **Total minimum:** 861 players.
- Maintains a 16-bit bitmask `d6` of **full** buckets (each bucket is marked full once `count >= quota + 15`) and a counter `d7` starting at `16` (decremented each time a bucket first reaches its minimum `quota`).
- Loops calling `$014c92` (generate one accepted player) until `d7 == 0`, redrawing the bucket count and `d7` on screen after every accepted player (`$017b9c`).

### Candidate player generation & rejection (`$014c92..$014d00`)
1. Calls `create_player` (`$01515a`):
   - Linearly scans the 1,500-slot (`$5dc`) × 42-byte (`$2a`) player pool (`$014c5e`) for a free slot (`age == 0`).
   - Rolls **height** (`$8(a2)`, 150–250 cm) as the sum of **350** random bits (`sum_rng_mod(350, 2)`), retrying if out of range.
   - Rolls **weight** (`$9(a2)`, 40–100 kg) from **140** random bits (`sum_rng_mod(140, 2)`) adjusted by height, retrying from height if out of range.
   - Sets age = 16 (`$4(a2) = $10`) and rolls 5 base attributes (`$a..$e`) using `sum_rng_mod(4, 6) * 10`.
   - Runs 8 rounds of generic youth training (`$015830`), then 8 rounds of position-picked training (`$0156f2` + `$015830`), then 2 full seasons (`$01526c`), then zeroes season stats (`$0150a8`).
2. Picks a random target age `18..37` (`18 + rnd % 20`).
3. Simulates seasons (`$01526c`) one by one until `age == target_age` and `division != 0`:
   - `pick_best_pos` (`$0156f2`) → `calc_pos_ratings` (`$0155f2`)
   - `assign_division` (`$0154ee`, also rolls international caps if rating ≥ 1000)
   - `sim_season_matches` (`$01539a`, simulates 20–48 individual matches for appearances/bookings/goals/injuries)
   - `train_skills` (`$015830`)
   - `age_and_train` (`$0157a0`, ages +1 and mutates physical/mental attributes using the age curve at `a4-$7a79`)
   - `check_retire` (`$0152d4`, age ≥ 30 retirement roll)
   - If the player retires early, `clr.b $4(a5)` frees the slot and **restarts from scratch** (`$014c96`).
4. Checks whether the `(division, position)` bit is set in `d6` (bucket already at `quota + 15`). If full, frees the slot and **restarts from scratch**.

---

## 2. Measured Runtime & CPU Profile (8 MHz STE, 1 MB)

### Full setup progression (fast-forward Hatari run from `newgame_0.sav`)
| Emulated ST time | Accepted players | Buckets ≥ quota | Buckets full (`+15`) | Rate |
|---:|---:|---:|---:|---:|
| 0 → 127 s | 533 | 0 / 16 | 0 / 16 | 4.2 players/s |
| 127 → 194 s | 745 (+212) | 1 / 16 | 0 / 16 | 3.1 players/s |
| 194 → 268 s | 940 (+195) | 12 / 16 | 3 / 16 | 2.6 players/s |
| 268 → 383 s | 1,059 (+119) | 15 / 16 | 12 / 16 | 1.0 players/s |
| 383 → 465 s | 1,065 (+6) | 16 / 16 | 12 / 16 | **0.07 players/s** |

- **Total time:** ~460 s (~7.7 min) for `$010cc0..$010d42` (followed immediately by `$014d3c` picking the Player-Manager from the pool).
- **Final counts:** `[23, 91, 88, 66, 32, 80, 82, 62, 32, 93, 81, 69, 29, 88, 80, 69]` (all 12 outfield buckets hit `quota + 15`; **Div 1 Keeper** was last to finish at 23/23).

### 250-VBL (5.0 s ST) CPU Profile Breakdown
| Component | Address range | Early setup | Late setup |
|---|---|---:|---:|
| 1-bit LFSR RNG (+ jmp table) | `$021656..$021678`, `$021792` | **35.79%** | **34.8%** |
| `sum_rng_mod` (mostly `divu.w #2`) | `$01863e..$01865c` | **30.48%** | **30.9%** |
| `calc_pos_ratings` (13× `divu.w`) | `$0155f2..$0156f2` | 7.89% | ~8% |
| VDI/UI number redraws | `$0d0000+` | 6.77–7.52% | 4.61% |
| `sim_season_matches` | `$01539a..$0154e6` | 4.51% | ~4.5% |
| `train_one_skill` | `$015758..$0157a0` | 3.51% | ~3.5% |
| `rating_lookup` | `$01530e..$015382` | 2.72% | ~2.7% |
| `pick_best_pos` | `$0156f2..$015738` | 1.95% | ~2.0% |
| `age_and_train` + everything else | various | ~6.4% | ~8.0% |

In 5.0 s of ST time, the CPU executes **~68,000 LFSR RNG calls** (~13,500/s), **~57,000 `sum_rng_mod` iterations** (`divu.w`), **~400 simulated seasons**, and **~37 candidate player attempts** — roughly **~3,400 candidates, ~36,000 seasons, and ~6.2 million RNG calls** over the full 7.7-minute run.

---

## 3. Inefficiencies Identified (Ranked by Impact)

1. **`sum_rng_mod` (`$01863e`) + 1-bit LFSR RNG (`$021656`) — ~66–68% of total CPU time**
   - The 48-bit LFSR at `$021656` is called through a jump table (`$021792`), pushes/pops `d0-d1/a0` (`movem.l`), shifts 3 memory words by 1 bit (`roxl.w (a0)+`), and returns — **~200+ cycles per call** for 1 fresh bit.
   - `sum_rng_mod` (`$01863e`) loops `d0` times calling the LFSR and executing a **~140-cycle `divu.w d1, d3`** to take the remainder.
   - **~91% of all `sum_rng_mod` iterations pass `d1 = 2`** (binomial coin-flip sums: `d0 = 350` for height, `d0 = 140` for weight, `d0 = 20` × 4 per season, `d0 = 8` per season). It executes `divu.w #2, d3` ~1,370 times per candidate (~4.7 million times total) just to sum random bits!
   - A fast `d1 == 2` path (or 16-bit-at-a-time PRNG + byte popcount lookup table, or even `andi.w #1` + inlined LFSR) would eliminate nearly the entire 66% RNG/divu bottleneck (~2.5–3× speedup on its own).

2. **Brute-force rejection sampling for rare buckets — ~3× wasted work (and ~18% of total time on the last 2 keepers)**
   - Out of ~3,400 fully simulated candidate careers, only **1,065 are kept** (~68% discarded).
   - Once the 12 outfield buckets reach `quota + 15`, **~93% of generated players are thrown away** while waiting for the last few **Division 1 Keepers**. The final 6 players (2 Div 1 Keepers) alone took **~83 seconds** (~18% of total runtime).
   - Players are simulated all the way to their random target age *before* checking if their bucket is full — even though position (`$5(a2)`) is largely locked in early, and a player's early attributes/position could be steered or filtered before simulating 10+ seasons.

3. **Wasted match-by-match season simulation (`$01539a..$0154e6`)**
   - Every season of a candidate's career simulates 20–48 individual matches (3–5 RNG calls + `divu.w` per match) to populate `$1d` (injuries), `$1f` (bookings), `$21` (goals), and `$23` (appearances).
   - At the start of the *next* season (`$0153e2..$0153ee`), all four fields are **immediately cleared (`clr.b`)** and nothing reads them between seasons.
   - Simulating matches for any season other than the player's final accepted season has zero effect on the resulting player data (only advancing the RNG state).

4. **Redundant recalculations inside the season loop**
   - `calc_pos_ratings` (`$0155f2`, 7.89% of cycles, containing **13 `divu.w` instructions**) is called **twice per season** (`$015282 -> $0156f2 -> $0155f2` and `$01528e -> $01539a -> $015340 -> $0155f2`) even though no player stats change between the two calls.
   - `rating_lookup` (`$01530e`, 2.72% of cycles) is called inside the per-match loop (`$015460`) up to 48 times per season with constant inputs (`d0 = 3`, unchanged Forward rating and division).

5. **UI/VDI redraw overhead (`$0d0000+`, ~5–7.5% of cycles)**
   - Every accepted player triggers two VDI text redraws (`$017b9c`), including redrawing the remaining-buckets counter (`d7`) even when it has not changed.

6. **Bonus bug found in original game: Division 4 training table out-of-bounds read (`$01583e..$015848`)**
   - `train_skills` (`$015830`) indexes the training probability table at `a4-$7a1a` (`$021c80`) using `division * 32` without subtracting 1 (divisions are `1..4`, while the table only has 4 entries `0..3` at `$021c80..$021cff`).
   - For **Division 4** (`$6(a2) == 4`), it reads past the end of the table at `$021d00..$021d1f` — right into the **Rating Thresholds** table (`$021d08`: `2000, 1110, 915, 845...`)! As a result, Div 4 Keepers get `[0, 0, 25, 33]` (0% chance to train keeping/tackling) while Div 4 outfielders get thresholds > 150 (100% training success every season).

---

## 4. Micro-Optimisation Patch Results (`patches/micro_opt.s`, `tools/pmpatch.py`)

Applied via a 1,028-byte payload staged to `$b3000` from `FILES/PMLA`'s unused zero data segment (`PMOK` marker at `$b2ff8`, cold-booted on 1 MB 8 MHz STE, TOS 1.62):
1. `sum_rng_mod` (`$01863e`): 100% bit-exact 16-bit LFSR step + 256-byte popcount table for `d1 == 2`; register-inlined LFSR for `d1 != 2`.
2. `fast_lfsr` (`$021792`): 100% bit-exact faster 1-bit LFSR (saves only `d0.w/d1.w`, `roxl.w d(a4)`).
3. `sim_season_matches` (`$0153ee`/`$01545e`): 100% bit-exact hoist of `rating_lookup` (`$01530e`) + `mulu.w` outside the per-match loop.
4. Dead intermediate-season match skip (`$010cc0`/`$01528e`/`$014ce2`): skips `$01539a` during intermediate setup seasons and runs it once on accepted players.
5. Setup UI (`$010d1a`): redraws `d7` only when it decrements (16× instead of 1,037×).

### Before vs After (1 MB 8 MHz STE, TOS 1.62)
- **Unpatched:** ~460 s (**7 min 40 s**, ~23,000 VBLs, 4.2 players/s early)
- **Patched v1 (initial micro-opts):** **121 s** (**2 min 01 s**, 6,053 VBLs, 10.5 players/s early) — **3.8× faster**
- **Patched v2 (+ extra micro-opts & Option A early position rejection):** **~109 s** (**1 min 49 s**, 5,433 VBLs, **13.8 players/s** early) — **4.2× faster**
  - Added: 4-bit & 8-bit LFSR steps in `fast_sum_rng_mod` (`d1 == 2`, zero 1-bit loops for `N=20`/`N=8`), 100% exact `fast_calc_pos_ratings` (reciprocal `mulu.w`/shifts + `tbl_1333`/`tbl_1750` LUTs), register-inlined LFSR in `fast_pick_best_pos` & `fast_train_one_skill`, batched VDI bucket-counter redraws (every 8th + quota/full + final pass; VDI dropped from 9.4% → 3.4%), and Option A early position rejection at `$014c96`/`$014cbe` (only rejects once all 4 divisions for a position are full and no open position is within 40 rating points).
  - Remaining hotspots in v2 250-VBL profile: 77.2% inside `$b3000+` payload (dominated by the last bit-exact `divu.w` instructions: general `sum_rng_mod` `d1 != 2`, `divu.w #150` / `#1333` in `train_one_skill`, and `divu.w #40` in `pick_best_pos`), 4.8% `age_and_train`, 3.4% VDI redraws, 3.2% `clamp_stat`.

