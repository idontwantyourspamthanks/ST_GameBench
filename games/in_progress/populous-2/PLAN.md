# Populous 2: plan

Study (second pass, 2026-11-11): `work/notes/baseline.md`, `hotpaths.md`, `algorithms.md`, `ui.md`, and `../populous/work/notes/bullfrog_family.md`. The first draft never reached the game; its plan (stride copy at `$2f4fe`, intro keyboard patch, tooltip rows 0-7 full width) is withdrawn. No patches exist. Harness: `tools/populous2.py`. Snapshots: `game_start`, `busy1` (2 MB STE).

Facts the plan rests on: frame-coupled (6.0 turns/s busy, 8.9 at the start, 8 MHz; 2.05x at 16 MHz); a busy frame is 8.1 VBLs: 47% drawing, 32.5% world logic, 8.4% interrupts.

## Ranked work

Gains are shares of the busy frame at 8 MHz and [INFERENCE] unless a measurement is named; days are [INFERENCE].

| # | Item | Ports from | Gain | Risk | Days |
|---|---|---|---|---|---|
| 1 | **Delivery** at 2 MB and 4 MB: payload, trampoline, HAGA file patches, free-RAM pattern test (`$7b37f`-`$f7fff`, `$167cfa`-`$1d89f7` are zero in the busy dump), credit line. Decide whether to skip the manual question. | Midwinter 2 tool; shared with Populous | none | the game sits at `$2300`-`$48000`, far from Midwinter's layout; 1 MB is out | 3 (1.5 after Populous) |
| 2 | **Sprites**: pre-shifted cache / STE blitter. | `p4_spr`, portable (site bytes identical at `$213b0`) | most of 10.0% | low-medium; blitter chunks and `p4_clamp` per `buserr.md` | 2 |
| 3 | **Pointer** only when something changed. | `p4_ptr`, adapted | 6.9% measured cost | low | 1 |
| 4 | **Land score**: remove the `divu #$34` (1.2%), then study `$252d8` (7.3%). | new | 1-5% | low for the divide; unknown for the scan | 2 |
| 5 | **Fixed tick** (VBL counters `$392d8` / `$392d4`). Rate is the user's choice (stock 8.9 -> 6.0 turns/s); proposal 6.25 per second (8 VBLs at 50 Hz). | `tick_*` design | constant speed | medium: link games, the click-age test at `$22f84` counts turns | 4 |
| 6 | **Tooltips** in the black sky at the top, (120,0)-(255,7), built from category and slot, showing the game's existing keys. No new keys until command `$72` is understood. | `pm_tooltip`, adapted | none | low; other landscapes and zoomed views unchecked | 2.5 |
| 7 | **Cached terrain**. | new, shared design with Populous | up to 20% in a static view | medium | 5 |
| 8 | IKBD clamp, triple buffering, DMA sound. | `p4_clamp` portable; `p7_triple`, `snd_*` adapted | small | low / low / medium | 0.3 / 1.5 / 3 |
| 9 | Other machines (TT, Falcon, Mega STE). | | | untested | 2+ |

Still to study before items 4-7 are firm (one read-only slice, about 2 days): landscape generation, walker pathing, effects, the computer player, command numbers `$0e`-`$78`, the zoomed views, a scene with effects running.

## Delegation slices

- A. Delivery (after or together with Populous slice A; same HAGA patches).
- B. "P2 world code" study, then item 4.
- C. Display: items 2, 3, then 7.
- D. Timing: item 5.
- E. UI: item 6.
