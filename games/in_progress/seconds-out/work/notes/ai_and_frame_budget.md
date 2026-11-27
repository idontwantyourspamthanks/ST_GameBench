# Seconds Out (1988, Tynesoft) — Frame Budget & Fighter AI Analysis

## 1. Baseline Frame Budget (8 MHz STE, 1 MB, Fight 1)

Measured over 250 VBLs (5.0 s, 63 frames) on stock `AUTO/EMPTY.PRG` (text base `$f176`):
- **Baseline FPS:** `12.6 fps` (`3.97 VBLs/frame`, hard-capped at 4 VBLs in `$0912: cmpi.w #$3, $716.l`).
- **Active work per frame (excluding VBL wait):** `415,540 cycles` (`2.59 VBLs/frame`).

| Routine | Share of total | Cycles / frame | VBLs / frame | What it does |
|---|---:|---:|---:|---|
| `Blit mode 0/2` (`$bc4-$ca6`) | 36.7% | 205,657 | 1.28 | Software-shifted 4-plane masked sprite (Opponent) — reads `$ca8/$ae0/$adc/$cb4` from RAM every 16 px |
| `VBL wait` (`$8fc-$91e`) | 25.8% | 144,800 | 0.90 | Idle wait for 4-VBL cap (`cmpi.w #$3, $716.l`) |
| `Blit mode 4` (`$1bfa-$1cb9`) | 23.0% | 128,711 | 0.80 | Software-shifted 2-plane wireframe masked sprite (Marco) |
| `BG copy partial` (`$10b6-$10ea`) | 11.8% | 66,239 | 0.41 | Copies 15,936 B (`$53ec0..$57cff`) from `RING.PI1` via `movem.l` |
| All game logic, AI, HUD, VBL, IKBD | 2.7% | ~15,000 | 0.09 | Everything else combined |

**Optimisation:**
- Precomputed 1-plane inverted mask cache (`$90000..$a5fff`, 88 KB) for all 8 sprite sheets (`$20000..$67fff` + 2-plane masks for `BOX1.PI1` & `PUNCHES.PI1`).
- STE Blitter HOG acceleration for BG partial/full copy (with dirty horizontal strip tracking per double buffer), Mode 0/2 (4 AND + 4 OR passes), and Mode 4 (4 AND + 2 OR passes), with a fast register-only CPU fallback for Blitter-less ST/TT.
- Uncoupled render loop (1-VBL flip) from fixed 12.5 Hz (4-VBL) real-time logic tick with 50 Hz positional tweening for both fighters.

## 2. Fighter AI & Balance Analysis (`EMPTY.TOS`)

`EMPTY.TOS` (`$534e`, 1,870 B) stores 5 fighter descriptors (`$86` bytes each, copied to `$2bf8` by `$2d24`) and 5 bytecode behaviour scripts (opcodes `0..13` dispatched via `$1530`):

| # | Fighter | Speed (`+$1e`) | Reactive Timer (`+$20`) | HP Regen (`+$3a`) | Anim Delay (`+$7e..$82`) | `REACT_BLK` (op 13) | Attacks in Script | Special Dmg (`+$34`) |
|---|---|---:|---:|---:|---|---:|---:|---:|
| 0 | Joe Weed | 1 | 20 (1.60s) | 50 | (2, 2, 2) | 0 / 135 | 6 | 7 |
| 1 | B. Jones | 2 | 10 (0.80s) | 18 | (2, 2, 2) | 0 / 133 | 11 | 10 |
| 2 | M. Hagman | 1 | 9 (0.72s) | **5** | **(1, 2, 1)** | 18 / 114 | 5 | 12 |
| 3 | J. Ronco | 1 | **4 (0.32s)** | **6** | **(1, 2, 1)** | **65 / 104** | **26** | 10 |
| 4 | M. Malone | **3** | **3 (0.24s)** | **8** | (2, 2, 2) | 18 / 104 | **22** | **16** |

### Root cause of "unblockable attack spam" on later fighters
In `$360c` (reactive AI), every `+$20` ticks when in range:
1. If the player is punching, the CPU immediately ducks (`$3600 = $ffff`) or low-blocks (`$168a`).
2. Otherwise, the CPU reads `$373e` (**the player's exact current guard height**): if the player guards High (`0`), the CPU picks a Low attack; if the player guards Low (`1`), the CPU picks a High attack — and whenever CPU HP > Player HP + 10, it immediately launches a **Special** (`$159c`, 16 dmg on Malone)!
3. On J. Ronco (`+$20 = 4`, `anim_delay = 1`) and M. Malone (`+$20 = 3`, `speed = 3`, `p_dmg_taken = 2`), this triggers every **0.24–0.32 seconds**, faster than human reaction time, while Ronco's script is 62% instant `REACT_BLK` and Hagman/Ronco regenerate HP 8–10× faster than Joe Weed.

### Rebalance applied (in `hook_load_opp`, `hook_cpu_react`, `hook_react_blk`)
- Escalating reactive timers: Weed `20`, Jones `14`, Hagman `12`, Ronco `10`, Malone `8`.
- Fair HP regen curve: Weed `50`, Jones `20`, Hagman `16`, Ronco `14`, Malone `12`.
- Human-reactable punch telegraphs `(2, 2, 2)` for Hagman & Ronco; Malone speed `3 -> 2`, Special dmg `16 -> 12`, damage taken `(2,2,4,3,4) -> (3,3,4,4,6)`.
- 50% fair-read gate in `$360c`, 2.0 s (`25`-tick) Special cooldown, and full stamina awareness (CPU cannot spam attacks/specials or auto-block when exhausted).
